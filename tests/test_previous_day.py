"""Tests for strict Polish calendar-day selection in Daily News."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_news as news


class PreviousDayTests(unittest.TestCase):
    def test_yesterday_is_full_day_in_warsaw(self):
        target, start, end = news.previous_day_window(
            datetime(2026, 10, 13, 6, tzinfo=ZoneInfo("Europe/Warsaw"))
        )
        self.assertEqual(target.isoformat(), "2026-10-12")
        self.assertEqual(start.isoformat(), "2026-10-11T22:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-12T22:00:00+00:00")
        self.assertEqual(end - start, timedelta(hours=24))
        self.assertTrue(news.published_in_window(start.isoformat(), start, end))
        self.assertTrue(news.published_in_window(
            (end - timedelta(seconds=1)).isoformat(), start, end
        ))
        self.assertFalse(news.published_in_window(end.isoformat(), start, end))
        self.assertFalse(news.published_in_window(
            (start - timedelta(seconds=1)).isoformat(), start, end
        ))
        self.assertFalse(news.published_in_window("", start, end))

    def test_spring_dst_day_has_23_hours(self):
        target, start, end = news.previous_day_window(
            datetime(2026, 3, 30, 6, tzinfo=ZoneInfo("Europe/Warsaw"))
        )
        self.assertEqual(target.isoformat(), "2026-03-29")
        self.assertEqual(end - start, timedelta(hours=23))

    def test_autumn_dst_day_has_25_hours(self):
        target, start, end = news.previous_day_window(
            datetime(2026, 10, 26, 6, tzinfo=ZoneInfo("Europe/Warsaw"))
        )
        self.assertEqual(target.isoformat(), "2026-10-25")
        self.assertEqual(end - start, timedelta(hours=25))

    def test_feed_ignores_today_and_prior_days_before_limiting(self):
        _, start, end = news.previous_day_window(
            datetime(2026, 10, 13, 6, tzinfo=ZoneInfo("Europe/Warsaw"))
        )
        def entry(title, published):
            return {
                "title": title,
                "link": "https://example.com/" + title,
                "published": format_datetime(published),
                "summary": "Test",
            }
        feed = SimpleNamespace(
            feed=SimpleNamespace(title="Test source"),
            entries=[
                entry("today", end),
                entry("yesterday-late", end - timedelta(seconds=1)),
                entry("yesterday-early", start),
                entry("too-old", start - timedelta(seconds=1)),
            ],
        )
        selected = []
        with patch.object(news.feedparser, "parse", return_value=feed):
            news.add_feed_entries(
                selected, set(), "https://example.com/rss", "Nauka", "quality",
                max_items=2, window_start=start, window_end=end,
            )
        self.assertEqual([item["title"] for item in selected],
                         ["yesterday-late", "yesterday-early"])

    def test_search_finds_early_previous_day(self):
        query = parse_qs(urlsplit(news.google_news_feed("science when:1d")).query)["q"][0]
        self.assertIn("when:3d", query)
        query = parse_qs(urlsplit(news.google_news_feed("science when:7d")).query)["q"][0]
        self.assertIn("when:7d", query)


if __name__ == "__main__":
    unittest.main()
