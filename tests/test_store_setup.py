import copy
import unittest
from datetime import date
from pathlib import Path

import yaml

from scripts.validate_store_setup import validate_records


class StoreSetupTests(unittest.TestCase):
    def setUp(self):
        self.stores = [
            {"id": "host", "class": "Store", "data": {"name": "방문 매장", "location": "장소"}},
            {"id": "team", "class": "Store", "data": {
                "name": "행사팀", "location": "순회", "operationType": "mobile_team",
                "setupStatus": "setup_pending", "seacodeStoreId": "team", "casStoreId": "team2",
            }},
        ]

    def visit(self, key="visit_1", start="2026-09-27", end=None):
        return {"id": key, "class": "StoreVisit", "data": {
            "location": "테스트 행사장", "startDate": start, "endDate": end,
        }, "relations": {"atStore": "team", "hostStore": "host"}}

    def test_empty_visits_and_legacy_stores_are_valid(self):
        validate_records(self.stores, [])

    def test_visit_does_not_change_team_attribution(self):
        records = [self.visit()]
        before = copy.deepcopy(records)
        validate_records(self.stores, records)
        self.assertEqual(records, before)
        self.assertEqual(records[0]["relations"]["atStore"], "team")

    def test_closed_and_next_day_visits_are_valid(self):
        validate_records(self.stores, [self.visit(end="2026-09-27"), self.visit("visit_2", date(2026, 9, 28))])

    def test_same_day_overlap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            validate_records(self.stores, [self.visit(end="2026-09-28"), self.visit("visit_2", "2026-09-28")])

    def test_open_period_overlap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            validate_records(self.stores, [self.visit(), self.visit("visit_2", "2026-10-01")])

    def test_invalid_dates_are_rejected(self):
        for value in ("2026-02-30", "2026-9-27", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_records(self.stores, [self.visit(start=value)])
        with self.assertRaisesRegex(ValueError, "before"):
            validate_records(self.stores, [self.visit(end="2026-09-26")])

    def test_wrong_team_or_host_is_rejected(self):
        for key, value in (("atStore", "host"), ("atStore", "missing"), ("hostStore", "missing"), ("hostStore", "team")):
            record = self.visit()
            record["relations"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_records(self.stores, [record])

    def test_duplicate_store_and_visit_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate Store ID"):
            validate_records(self.stores + [self.stores[0]], [])
        with self.assertRaisesRegex(ValueError, "duplicate StoreVisit"):
            validate_records(self.stores, [self.visit(), self.visit()])

    def test_duplicate_external_mapping_is_rejected(self):
        self.stores[0]["data"]["casStoreId"] = "team2"
        with self.assertRaisesRegex(ValueError, "duplicate casStoreId"):
            validate_records(self.stores, [])

    def test_legacy_implicit_app_mapping_cannot_be_reused(self):
        self.stores[1]["data"]["seacodeStoreId"] = "host"
        with self.assertRaisesRegex(ValueError, "duplicate seacodeStoreId"):
            validate_records(self.stores, [])

    def test_invalid_setup_status_is_rejected(self):
        self.stores[1]["data"]["setupStatus"] = "made_up"
        with self.assertRaisesRegex(ValueError, "invalid setupStatus"):
            validate_records(self.stores, [])

    def test_actual_registry_has_pending_dedicated_team_without_fake_visits(self):
        root = Path(__file__).resolve().parents[1]
        stores = yaml.safe_load((root / "instances/master/stores.yaml").read_text(encoding="utf-8"))["instances"]
        visits = yaml.safe_load((root / "instances/store_visits/mooner.yaml").read_text(encoding="utf-8"))["instances"]
        validate_records(stores, visits)
        team = next(record for record in stores if record["id"] == "mooner")
        self.assertEqual(team["data"]["casStoreId"], "mooner2")
        self.assertEqual(team["data"]["seacodeStoreId"], "mooner")
        self.assertEqual(team["data"]["operationType"], "mobile_team")
        # Connectivity remains a separate acceptance gate, not a fabricated visit.
        self.assertIn(team["data"]["setupStatus"], ("setup_pending", "ready"))


if __name__ == "__main__":
    unittest.main()
