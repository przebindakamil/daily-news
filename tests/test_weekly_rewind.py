import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import weekly_rewind as wr


def article(title, url, category="Nauka", sid="story-a", score=9):
    return {
        "title": title, "url": url, "category": category,
        "story_id": sid, "editorial_score": score,
        "summary": "Potwierdzone streszczenie z archiwum.",
    }


class WeeklyRewindTests(unittest.TestCase):
    def test_previous_complete_week_is_monday(self):
        self.assertEqual(wr.previous_week(date(2026, 10, 16)), date(2026, 10, 5))
        self.assertEqual(wr.previous_week(date(2026, 10, 12)), date(2026, 10, 5))

    def test_incomplete_week_is_explicit_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"2026-10-05.json").write_text(json.dumps({
                "date":"2026-10-05",
                "top_stories":[article("Story one", "https://a/1",sid="a"),
                               article("Story two", "https://b/2",sid="b",score=7)],
                "more_stories":[]
            }),encoding="utf-8")
            (folder/"2026-10-07.json").write_text(json.dumps({
                "date":"2026-10-07",
                "top_stories":[article("Story one update", "https://a/3",sid="a",score=10)],
                "more_stories":[]
            }),encoding="utf-8")
            result=wr.build_weekly(date(2026,10,5),folder)
            self.assertFalse(result["complete"])
            self.assertEqual(len(result["missing_days"]),5)
            self.assertEqual(len(result["stories"]),2)
            self.assertEqual(result["stories"][0]["title"],"Story one update")
            self.assertEqual(len(result["watch_next"]),1)
            self.assertEqual(result["source"],"public_archive")

    def test_all_seven_days_mark_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for offset in range(7):
                day=(date(2026,10,5).toordinal()+offset)
                daystr=date.fromordinal(day).isoformat()
                (folder/f"{daystr}.json").write_text(json.dumps({
                    "date": daystr,
                    "top_stories":[article("Title "+str(offset),f"https://a/{offset}",
                                           sid="s-"+str(offset))],
                    "more_stories":[]
                }), encoding="utf-8")
            result=wr.build_weekly(date(2026,10,5),folder)
            self.assertTrue(result["complete"])
            self.assertEqual(len(result["missing_days"]),0)


if __name__=="__main__":
    unittest.main()
