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
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SALES_SCRIPT = ROOT / "scripts" / "namseon_sales.py"
DEFAULT_FOLDER_ID = "1MQkVkt795mKLqCi8zFbJS3mqJ3k9FO2i"
DEFAULT_DB_DRIVE_FILE_ID = "10lBIcYzcqktWEdF9xYfnM82S-mFGzG-m"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: str
    parent_name: str
    sale_date: str


def run_json(args: list[str]) -> dict:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def drive_ls(parent_id: str) -> list[dict]:
    files: list[dict] = []
    page = ""
    while True:
        args = [
            "gog",
            "drive",
            "ls",
            "--parent",
            parent_id,
            "--max",
            "100",
            "--json",
            "--no-input",
        ]
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


def infer_sale_date(file_name: str, parent_name: str) -> str | None:
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
        if not year_match:
            return None
        year = int(year_match.group(1))

    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def discover(root_folder_id: str) -> tuple[list[DriveFile], list[str]]:
    root_files = drive_ls(root_folder_id)
    folders = [
        f for f in root_files if f.get("mimeType") == "application/vnd.google-apps.folder"
    ]
    containers = [(root_folder_id, "남선매출")]
    containers.extend((f["id"], f["name"]) for f in folders)

    discovered: list[DriveFile] = []
    skipped: list[str] = []
    for folder_id, folder_name in containers:
        entries = root_files if folder_id == root_folder_id else drive_ls(folder_id)
        for item in entries:
            mime_type = item.get("mimeType", "")
            if mime_type == "application/vnd.google-apps.folder":
                continue
            if not (
                mime_type == GOOGLE_SHEET_MIME
                or item.get("name", "").lower().endswith((".xlsx", ".xls", ".csv"))
            ):
                continue
            sale_date = infer_sale_date(item.get("name", ""), folder_name)
            if not sale_date:
                skipped.append(f"{folder_name}/{item.get('name', '')}")
                continue
            discovered.append(
                DriveFile(
                    id=item["id"],
                    name=item.get("name", ""),
                    mime_type=mime_type,
                    modified_time=item.get("modifiedTime", ""),
                    parent_name=folder_name,
                    sale_date=sale_date,
                )
            )
    return discovered, skipped


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


def next_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return (parsed + timedelta(days=1)).isoformat()


def next_unimported_date(db: Path) -> str | None:
    if not db.exists():
        return None
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT MAX(sale_date) FROM source_files").fetchone()
    if not row or not row[0]:
        return None
    return next_date(row[0])


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
    args = parser.parse_args()

    if args.incremental and args.from_date:
        raise SystemExit("--incremental and --from-date cannot be used together")

    from_date = args.from_date
    if args.incremental:
        from_date = next_unimported_date(args.db)
        if not from_date:
            print("incremental_from=<none>; DB is empty or missing, syncing all files")
        else:
            print(f"incremental_from={from_date}")

    files, skipped = discover(args.folder_id)
    chosen, duplicates = choose_latest(files)
    if from_date:
        chosen = [file for file in chosen if file.sale_date >= from_date]

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
        for file in duplicates:
            print(f"duplicate {file.sale_date} {file.id} {file.name}")
        return

    tmp_dir = Path(tempfile.mkdtemp(prefix="namseon_drive_sync_"))
    try:
        for index, file in enumerate(chosen, start=1):
            print(f"[{index}/{len(chosen)}] import {file.sale_date} {file.name}")
            csv_path = export_csv(file, tmp_dir)
            import_file(args.db, file, csv_path)

        if args.trash_duplicates:
            for index, file in enumerate(duplicates, start=1):
                print(f"[dup {index}/{len(duplicates)}] trash {file.sale_date} {file.name}")
                trash_file(file)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if args.upload_db:
        print(f"upload-db replace {args.db_drive_file_id}")
        upload_db(args.db, args.db_drive_file_id)


if __name__ == "__main__":
    main()
