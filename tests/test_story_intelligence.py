import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import story_intelligence as si


def story(title, url, category="Nauka", date="2026-10-15T11:30:00+00:00"):
    return {
        "title": title, "url": url, "category": category, "published_at": date,
        "topics": ["Mars", "misja"], "source": "Example", "summary": title,
    }


class StoryIntelligenceTests(unittest.TestCase):
    def test_safe_url_normalization(self):
        self.assertEqual(
            si.canonical_url("HTTP://WWW.Example.COM/p/?utm_source=x&id=17#top"),
            "https://example.com/p?id=17",
        )
        self.assertEqual(si.canonical_url("javascript:alert(1)"), "")
        self.assertEqual(si.canonical_url("https://alice:password@example.com/p"), "")
        self.assertEqual(si.publisher_domain("https://news.google.com/rss/a"), "")
        self.assertEqual(si.canonical_url("http://127.0.0.1/private"), "")
        self.assertEqual(si.canonical_url("http://192.168.1.8/private"), "")
        self.assertEqual(si.canonical_url("http://localhost/private"), "")

    def test_same_event_high_precision_and_multiple_sources(self):
        a = story("NASA announces new Mars rover landing mission",
                  "https://news.example.com/story?a=1&utm_source=rss")
        b = story("NASA announces new Mars rover landing mission",
                  "https://another.com/story?utm_medium=rss")
        c = story("NASA announces new Moon rover landing mission",
                  "https://somewhere.com/moon")
        grouped = si.group_candidates([a, b, c])
        self.assertEqual(len(grouped), 2)
        meta = si.source_summary(grouped[0])
        self.assertEqual(meta["source_count"], 2)
        self.assertEqual(meta["publisher_count"], 2)
        self.assertNotIn("independent", meta["source_count_label"])

    def test_publication_validation_rejects_unknown_dates(self):
        start = datetime(2026, 10, 15, tzinfo=timezone.utc)
        end = datetime(2026, 10, 16, tzinfo=timezone.utc)
        candidate = story("Test", "https://example.com/news")
        self.assertTrue(si.plausible_publication(candidate, start, end))
        self.assertFalse(si.plausible_publication(
            {**candidate, "published_at": "2026-10-14T21:00:00+00:00"}, start, end
        ))
        self.assertFalse(si.plausible_publication(
            {**candidate, "url": "bad:"}, start, end
        ))

    def test_link_health_detects_confirmed_missing_without_blocking_paywalls(self):
        from unittest.mock import Mock
        def answer(code):
            response = Mock()
            response.status_code = code
            return response
        client = Mock()
        client.head.return_value = answer(404)
        client.get.return_value = answer(404)
        self.assertEqual(si.source_health("https://publisher.example/story", client), "missing")
        client.head.return_value = answer(403)
        client.get.reset_mock()
        self.assertEqual(si.source_health("https://publisher.example/story", client), "unverified")
        client.get.assert_not_called()
        client.head.return_value = answer(405)
        client.get.return_value = answer(200)
        self.assertEqual(si.source_health("https://publisher.example/story", client), "reachable")
        self.assertEqual(si.source_health("http://127.0.0.1/private", client), "invalid")

    def test_previous_url_duplicates_but_not_developing_updates(self):
        previous = [story("Mars rover new exploration",
                          "https://example.com/a?utm_medium=x")]
        newer = [
            story("Mars rover new exploration", "https://example.com/a"),
            story("Mars rover landed successfully", "https://example.com/b"),
        ]
        self.assertEqual(list(si.dedupe_previous(newer, previous)), newer[1:])

    def test_unchanged_repeat_is_skipped_but_updated_content_is_kept(self):
        old = story("NASA announces Mars rover launch",
                    "https://first.example/old")
        old["summary"] = "NASA confirms Mars rover launch will happen tomorrow."
        same = {**old, "url": "https://newspaper.example/copy"}
        updated = {**same, "summary": "NASA confirms Mars rover launched safely today."}
        result = list(si.filter_unchanged_stories([same, updated], [old]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["summary"], updated["summary"])

    def test_multi_word_name_check_generates_review_hint_not_rejection(self):
        flagged = si.fact_warnings({
            "article_text": "Maria Kowalska gave a presentation to the press.",
            "digest_text": "Anna Nowak dała prezentację dla prasy.",
        })
        self.assertTrue(flagged["checked"])
        self.assertIn("Anna Nowak", flagged["name_warnings"])

    def test_numeric_fact_warning_is_only_heuristic(self):
        good = si.fact_warnings({
            "article_text": "Rescued 12 people after the crash.",
            "digest_text": "12 people were rescued.",
        })
        bad = si.fact_warnings({
            "article_text": "Rescued 12 people after the crash.",
            "digest_text": "13 people were rescued.",
        })
        self.assertTrue(good["checked"])
        self.assertEqual(good["warnings"], [])
        self.assertEqual(bad["warnings"], ["13"])
        self.assertFalse(si.fact_warnings({"digest_text": "13 people"})["checked"])

    def test_archive_matching_does_not_associate_different_topics(self):
        older = {**story("Mars probe reaches new region",
                           "https://a.example.com/old"),
                 "archive_date": "2026-10-14", "story_id": "s-existing"}
        newer = story("Mars probe reaches new region",
                      "https://b.example.com/updated")
        result = si.enrich_edition([newer], [older], "2026-10-15")[0]
        self.assertEqual(result["story_id"], "s-existing")
        self.assertTrue(result["is_update"])
        self.assertEqual(len(result["story_timeline"]), 1)
        unrelated = {**newer, "category": "Polska"}
        again = si.enrich_edition([unrelated], [older], "2026-10-15")[0]
        self.assertNotEqual(again["story_id"], "s-existing")
        self.assertFalse(again["is_update"])

    def test_only_reads_past_week_from_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for day in ["2026-10-13", "2026-10-16", "2026-10-01"]:
                (root / f"{day}.json").write_text(json.dumps({
                    "top_stories": [story(day, f"https://example.com/{day}")],
                    "more_stories": [],
                }), encoding="utf-8")
            found = si.recent_entries(root, "2026-10-15", days=7)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["archive_date"], "2026-10-13")


if __name__ == "__main__":
    unittest.main()
