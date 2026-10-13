"""Regression tests for candidate coverage and missed-major-event reporting."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_news as news


class CoverageReportTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {
                "title": "Two economists win Nobel Prize in Economics",
                "url": "https://example.org/nobel-economics",
                "source": "Example newspaper",
                "category_hint": "Finanse i inwestowanie",
            },
            {
                "title": "Launch of a new mobile phone",
                "url": "https://example.org/phone",
                "source": "Tech newspaper",
                "category_hint": "AI i technologia",
            },
        ]

    def test_nobel_found_but_not_ranked_is_flagged(self):
        ranked = [{**self.candidates[1], "editorial_score": 7.0}]
        report = news.build_coverage_report(
            "2026-10-12", self.candidates, ranked,
            [self.candidates[1]], source_stats=[]
        )
        self.assertEqual(report["potential_gaps"][0]["id"], "nobel")
        watch = next(item for item in report["watched_events"] if item["id"] == "nobel")
        self.assertTrue(watch["needs_review"])
        self.assertEqual(watch["sightings"][0]["stage"], "not_ranked")

    def test_nobel_ranked_but_not_published_is_flagged(self):
        report = news.build_coverage_report(
            "2026-10-12", self.candidates, self.candidates,
            [self.candidates[1]], source_stats=[]
        )
        watch = next(item for item in report["watched_events"] if item["id"] == "nobel")
        self.assertEqual(watch["sightings"][0]["stage"], "ranked_not_published")

    def test_published_nobel_is_not_flagged(self):
        report = news.build_coverage_report(
            "2026-10-12", self.candidates, self.candidates,
            self.candidates, source_stats=[]
        )
        self.assertEqual(report["potential_gaps"], [])
        watch = next(item for item in report["watched_events"] if item["id"] == "nobel")
        self.assertEqual(watch["sightings"][0]["stage"], "published")

    def test_no_important_candidates_is_not_success_proof(self):
        report = news.build_coverage_report(
            "2026-10-12", [self.candidates[1]],
            [self.candidates[1]], [self.candidates[1]], source_stats=[]
        )
        self.assertEqual(report["watched_events"], [])
        self.assertEqual(report["potential_gaps"], [])
        self.assertEqual(report["category_coverage"]["AI i technologia"]["published"], 0)
        # The sample lacks a category field, so it is intentionally not classified.

    def test_empty_feed_is_visible(self):
        source = {
            "name": "Missing feed", "origin": "direct_rss", "entries_read": 0,
            "candidates_added": 0, "feed_parse_warning": True,
        }
        report = news.build_coverage_report(
            "2026-10-12", [], [], [], source_stats=[source]
        )
        self.assertEqual(report["empty_feeds"], ["Missing feed"])


if __name__ == "__main__":
    unittest.main()
