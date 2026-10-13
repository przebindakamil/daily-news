"""Regression tests for historical audits without model/API access."""
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_news as audit


class WeeklyAuditTests(unittest.TestCase):
    def test_iso_week_boundaries(self):
        label, monday, sunday = audit.weekly_window(
            "2026-W41", now=datetime(2026, 10, 13, 10, tzinfo=ZoneInfo("Europe/Warsaw"))
        )
        self.assertEqual(label, "2026-W41")
        self.assertEqual(monday.isoformat(), "2026-10-05")
        self.assertEqual(sunday.isoformat(), "2026-10-11")

    def test_current_or_future_week_cannot_be_audited(self):
        with self.assertRaises(ValueError):
            audit.weekly_window(
                "2026-W42", now=datetime(2026, 10, 13, 10, tzinfo=ZoneInfo("Europe/Warsaw"))
            )

    def test_incomplete_week_does_not_claim_coverage_score(self):
        mock_data = {
            "issues": [{"date": "2026-10-09"}],
            "coverages": [],
            "published": [{"day": "2026-10-09", "title": "A", "url": "https://example.com/a"}],
            "references": [],
            "missing_issues": [d for d in audit.day_strings(date(2026, 10, 5)) if d != "2026-10-09"],
            "missing_coverages": audit.day_strings(date(2026, 10, 5)),
        }
        report = audit.build_report(
            "2026-W41", date(2026, 10, 5), date(2026, 10, 11), mock_data
        )
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["metrics"]["coverage_percent"])
        self.assertEqual(report["metrics"]["issues_available"], 1)
        self.assertEqual(report["metrics"]["published"], 1)

    def test_complete_week_has_weighted_sample_score_and_pipeline(self):
        data = {
            "issues": [{}] * 7,
            "coverages": [{
                "candidate_pool": [{"url": "https://example.com/nobel", "title": "Nobel ceremony"}],
                "ranked_pool": [],
                "empty_feeds": [],
            }] * 7,
            "published": [{"day": "2026-10-12", "title": "Some other news", "url": "https://example.com/a"}],
            "references": [{"title": str(i), "url": "https://example.com/" + str(i), "day": (date(2026, 10, 12) + timedelta(days=i % 7)).isoformat()} for i in range(10)],
            "missing_issues": [],
            "missing_coverages": [],
        }
        events = [
            {"title": "Nobel ceremony", "url": "https://example.com/nobel", "category": "Nauka",
             "day": "2026-10-12", "source": "Test", "importance": 5},
            {"title": "Some other news", "url": "https://example.com/a", "category": "Świat",
             "day": "2026-10-12", "source": "Test", "importance": 3},
        ]
        matches = {
            0: {"status": "missing", "published_indices": [], "reason": "brak"},
            1: {"status": "covered", "published_indices": [0], "reason": "jest"},
        }
        report = audit.build_report(
            "2026-W42", date(2026, 10, 12), date(2026, 10, 18), data, events, matches
        )
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["metrics"]["coverage_percent"], 50.0)
        self.assertEqual(report["events"][0]["pipeline"], "discovered_not_ranked")
        self.assertEqual(report["metrics"]["missing"], 1)

    def test_index_preserves_history_and_latest(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with patch.object(audit, "AUDIT_DIR", directory), \
                 patch.object(audit, "AUDIT_INDEX", directory / "index.json"):
                for week, start, end in [
                    ("2026-W41", "2026-10-05", "2026-10-11"),
                    ("2026-W42", "2026-10-12", "2026-10-18"),
                ]:
                    report = {
                        "week": week, "start_date": start, "end_date": end,
                        "status": "incomplete",
                        "metrics": {"coverage_percent": None, "audited_events": 0,
                                    "missing": 0, "published": 12},
                    }
                    audit.save_report(report)
                content = audit.read_json(directory / "index.json")
                self.assertEqual(content["latest"], "2026-W42")
                self.assertEqual([row["week"] for row in content["weeks"]],
                                 ["2026-W42", "2026-W41"])

    def test_ai_indexes_are_validated(self):
        references = [{"title": "Nobel research", "url": "https://example.org/1",
                       "source": "Example", "day": "2026-10-12"}]
        with patch.object(audit, "gemini_json", return_value={
            "events": [
                {"reference_index": 9, "importance": 5},
                {"reference_index": 0, "importance": 5, "category": "Nauka"},
            ]
        }):
            self.assertEqual(len(audit.select_key_events(references)), 1)

    def test_model_must_grade_every_event(self):
        with patch.object(audit, "gemini_json", return_value={"matches": []}):
            with self.assertRaises(RuntimeError):
                audit.compare_publication(
                    [{"title":"Nobel", "day":"2026-10-12", "source":"source"}], []
                )


if __name__ == "__main__":
    unittest.main()
