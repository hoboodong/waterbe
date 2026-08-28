#!/usr/bin/env python3
"""
Google Drive 남선매출 폴더 전체를 SQLite DB와 동기화한다.

기본 동작:
  - 남선매출 루트와 월별 하위 폴더의 스프레드시트 파일을 찾는다.
  - 파일명에서 매출일을 추정한다.
  - 같은 날짜 파일이 여러 개면 Google Sheets 파일을 우선하고, 그 안에서 수정 시간이 최신인 하나만 남긴다.
  - 선택되지 않은 중복 파일은 --trash-duplicates 지정 시 휴지통으로 보낸다.
  - 선택된 파일은 CSV로 export해서 scripts/namseon_sales.py로 import한다.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SALES_SCRIPT = ROOT / "scripts" / "namseon_sales.py"
SUPABASE_SCRIPT = ROOT / "scripts" / "namseon_supabase_sync.py"
DEFAULT_FOLDER_ID = "1MQkVkt795mKLqCi8zFbJS3mqJ3k9FO2i"
DEFAULT_DB_DRIVE_FILE_ID = "10lBIcYzcqktWEdF9xYfnM82S-mFGzG-m"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_ROOT_NAME = "Google Drive root"


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: str
    parent_id: str
    parent_name: str
    sale_date: str
    from_drive_root: bool = False


def run_json(args: list[str]) -> dict:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def drive_ls(parent_id: str | None = None) -> list[dict]:
    files: list[dict] = []
    page = ""
    while True:
        args = [
            "gog",
            "drive",
            "ls",
            "--max",
            "100",
            "--json",
            "--no-input",
        ]
        if parent_id:
            args.extend(["--parent", parent_id])
        if page:
            args.extend(["--page", page])
        data = run_json(args)
        files.extend(data.get("files", []))
        page = data.get("nextPageToken") or ""
        if not page:
            return files


def folder_year_month(name: str) -> tuple[int, int] | None:
    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월", name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def infer_sale_date(
    file_name: str, parent_name: str, modified_time: str = ""
) -> str | None:
    name = unicodedata.normalize("NFKC", file_name).replace("\u00a0", " ")
    parent_ym = folder_year_month(parent_name)

    month = None
    day = None

    match = re.search(
        r"(\d{1,2})\s*월\s*일?\s*(\d{1,2})\s*[.]?\s*일?", name
    )
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
    else:
        match = re.search(r"(?<!\d)(\d{1,2})\s*[.,]\s*(\d{1,2})(?!\d)", name)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))

    if day is None:
        return None

    if parent_ym:
        year = parent_ym[0]
        if month is None:
            month = parent_ym[1]
    else:
        year_match = re.search(r"(20\d{2})", name)
        if year_match:
            year = int(year_match.group(1))
        elif re.match(r"20\d{2}-", modified_time):
            year = int(modified_time[:4])
        else:
            return None

    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def discover(
    root_folder_id: str, include_drive_root: bool = False
) -> tuple[list[DriveFile], list[str], dict[tuple[int, int], str]]:
    root_files = drive_ls(root_folder_id)
    folders = [
        f for f in root_files if f.get("mimeType") == FOLDER_MIME
    ]
    month_folders = {
        ym: f["id"]
        for f in folders
        if (ym := folder_year_month(f.get("name", ""))) is not None
    }
    containers = [(root_folder_id, "남선매출")]
    containers.extend((f["id"], f["name"]) for f in folders)
    if include_drive_root:
        containers.append(("", DRIVE_ROOT_NAME))

    discovered: list[DriveFile] = []
    skipped: list[str] = []
    for folder_id, folder_name in containers:
        if folder_id == root_folder_id:
            entries = root_files
        elif folder_id:
            entries = drive_ls(folder_id)
        else:
            entries = drive_ls()
        for item in entries:
            mime_type = item.get("mimeType", "")
            if mime_type == FOLDER_MIME:
                continue
            if not (
                mime_type == GOOGLE_SHEET_MIME
                or item.get("name", "").lower().endswith((".xlsx", ".xls", ".csv"))
            ):
                continue
            sale_date = infer_sale_date(
                item.get("name", ""), folder_name, item.get("modifiedTime", "")
            )
            if not sale_date:
                skipped.append(f"{folder_name}/{item.get('name', '')}")
                continue
            discovered.append(
                DriveFile(
                    id=item["id"],
                    name=item.get("name", ""),
                    mime_type=mime_type,
                    modified_time=item.get("modifiedTime", ""),
                    parent_id=folder_id,
                    parent_name=folder_name,
                    sale_date=sale_date,
                    from_drive_root=folder_name == DRIVE_ROOT_NAME,
                )
            )
    return discovered, skipped, month_folders


def choose_latest(files: list[DriveFile]) -> tuple[list[DriveFile], list[DriveFile]]:
    by_date: dict[str, list[DriveFile]] = {}
    for file in files:
        by_date.setdefault(file.sale_date, []).append(file)

    chosen: list[DriveFile] = []
    duplicates: list[DriveFile] = []
    for sale_date in sorted(by_date):
        candidates = by_date[sale_date]
        candidates.sort(
            key=lambda f: (
                1 if f.mime_type == GOOGLE_SHEET_MIME else 0,
                f.modified_time,
                f.id,
            ),
            reverse=True,
        )
        chosen.append(candidates[0])
        duplicates.extend(candidates[1:])
    return chosen, duplicates


def export_csv(file: DriveFile, out_dir: Path) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{file.sale_date}_{file.id}.csv")
    out_path = out_dir / safe_name
    run(
        [
            "gog",
            "sheets",
            "export",
            file.id,
            "--format",
            "csv",
            "--out",
            str(out_path),
            "--no-input",
        ]
    )
    return out_path


def import_file(db: Path, file: DriveFile, csv_path: Path) -> None:
    run(
        [
            sys.executable,
            str(SALES_SCRIPT),
            "--db",
            str(db),
            "import-csv",
            str(csv_path),
            "--date",
            file.sale_date,
            "--source-file-id",
            file.id,
            "--source-file-name",
            file.name,
            "--modified-time",
            file.modified_time,
        ]
    )


def trash_file(file: DriveFile) -> None:
    run(["gog", "drive", "delete", file.id, "--force", "--no-input"])


def imported_sources(db: Path) -> dict[str, tuple[str, str]]:
    if not db.exists():
        return {}
    with sqlite3.connect(db) as conn:
        try:
            rows = conn.execute(
                "SELECT sale_date, file_id, coalesce(modified_time, '') FROM source_files"
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
    return {sale_date: (file_id, modified_time) for sale_date, file_id, modified_time in rows}


def incremental_files(db: Path, files: list[DriveFile]) -> list[DriveFile]:
    imported = imported_sources(db)
    return [
        file
        for file in files
        if imported.get(file.sale_date) != (file.id, file.modified_time)
    ]


def upload_db(db: Path, drive_file_id: str) -> None:
    run(
        [
            "gog",
            "drive",
            "upload",
            str(db),
            "--replace",
            drive_file_id,
            "--json",
            "--no-input",
        ]
    )


def sync_supabase(db: Path, sale_dates: list[str]) -> None:
    args = [sys.executable, str(SUPABASE_SCRIPT), "--db", str(db)]
    if sale_dates:
        for sale_date in sorted(set(sale_dates)):
            args.extend(["--date", sale_date])
    else:
        print("supabase-sync reconcile-all; no new or modified Drive files")
    run(args)


def ensure_month_folder(
    sale_date: str, root_folder_id: str, month_folders: dict[tuple[int, int], str]
) -> str:
    parsed = date.fromisoformat(sale_date)
    key = (parsed.year, parsed.month)
    if key in month_folders:
        return month_folders[key]

    folder_name = f"{parsed.year:04d}년 {parsed.month:02d}월"
    data = run_json(
        [
            "gog",
            "drive",
            "mkdir",
            folder_name,
            "--parent",
            root_folder_id,
            "--json",
            "--no-input",
        ]
    )
    folder = data.get("file") or data.get("folder") or data
    folder_id = folder.get("id")
    if not folder_id:
        raise RuntimeError(f"created folder id not found for {folder_name}")
    month_folders[key] = folder_id
    return folder_id


def move_to_month_folder(
    file: DriveFile, root_folder_id: str, month_folders: dict[tuple[int, int], str]
) -> None:
    folder_id = ensure_month_folder(file.sale_date, root_folder_id, month_folders)
    run(["gog", "drive", "move", file.id, "--parent", folder_id, "--no-input"])


def main() -> None:
    parser = argparse.ArgumentParser(description="남선매출 Drive 전체 동기화")
    parser.add_argument("--folder-id", default=DEFAULT_FOLDER_ID)
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT / "instances" / "sales" / "namseon" / "namseon_sales.db",
    )
    parser.add_argument("--trash-duplicates", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from-date", help="Only import selected files on or after YYYY-MM-DD")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Start from the day after the latest sale_date already in the DB",
    )
    parser.add_argument(
        "--upload-db",
        action="store_true",
        help="Replace the Drive DB file after sync",
    )
    parser.add_argument(
        "--db-drive-file-id",
        default=DEFAULT_DB_DRIVE_FILE_ID,
        help="Drive file ID to replace when --upload-db is used",
    )
    parser.add_argument(
        "--include-drive-root",
        action="store_true",
        help="Also scan Google Drive root for newly uploaded sales sheets",
    )
    parser.add_argument(
        "--organize-root-files",
        action="store_true",
        help="Move imported Drive root sales sheets into the matching monthly folder",
    )
    parser.add_argument(
        "--sync-supabase",
        action="store_true",
        help="Upload selected dates from SQLite to Supabase and verify them",
    )
    args = parser.parse_args()

    if args.incremental and args.from_date:
        raise SystemExit("--incremental and --from-date cannot be used together")

    files, skipped, month_folders = discover(args.folder_id, args.include_drive_root)
    chosen, duplicates = choose_latest(files)
    if args.incremental:
        chosen = incremental_files(args.db, chosen)
        print("incremental=unseen-or-modified")
    elif args.from_date:
        chosen = [file for file in chosen if file.sale_date >= args.from_date]

    print(f"discovered={len(files)}")
    print(f"selected={len(chosen)}")
    print(f"duplicates={len(duplicates)}")
    if skipped:
        print(f"skipped={len(skipped)}")
        for item in skipped:
            print(f"skip {item}")

    if args.dry_run:
        for file in chosen:
            print(f"select {file.sale_date} {file.id} {file.name}")
            if args.organize_root_files and file.from_drive_root:
                parsed = date.fromisoformat(file.sale_date)
                print(
                    f"move {file.sale_date} {file.id} -> "
                    f"{parsed.year:04d}년 {parsed.month:02d}월"
                )
        for file in duplicates:
            print(f"duplicate {file.sale_date} {file.id} {file.name}")
        return

    tmp_dir = Path(tempfile.mkdtemp(prefix="namseon_drive_sync_"))
    try:
        for index, file in enumerate(chosen, start=1):
            print(f"[{index}/{len(chosen)}] import {file.sale_date} {file.name}")
            csv_path = export_csv(file, tmp_dir)
            import_file(args.db, file, csv_path)
            if args.organize_root_files and file.from_drive_root:
                print(f"[{index}/{len(chosen)}] move {file.sale_date} {file.name}")
                move_to_month_folder(file, args.folder_id, month_folders)

        if args.trash_duplicates:
            for index, file in enumerate(duplicates, start=1):
                print(f"[dup {index}/{len(duplicates)}] trash {file.sale_date} {file.name}")
                trash_file(file)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if args.sync_supabase:
        sync_supabase(args.db, [file.sale_date for file in chosen])

    if args.upload_db:
        print(f"upload-db replace {args.db_drive_file_id}")
        upload_db(args.db, args.db_drive_file_id)


if __name__ == "__main__":
    main()
