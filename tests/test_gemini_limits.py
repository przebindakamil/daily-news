"""Gemini RPM pacing and transient quota failure tests."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_news as news


def gemini_response(status_code, payload, headers=None):
    return SimpleNamespace(
        status_code=status_code,
        ok=200 <= status_code < 300,
        headers=headers or {},
        text="rate limit",
        json=lambda: payload,
    )


class GeminiLimitsTests(unittest.TestCase):
    def test_retryinfo_wait_time_is_respected(self):
        response = gemini_response(429, {
            "error": {
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo",
                     "retryDelay": "14.425s"}
                ]
            }
        })
        self.assertAlmostEqual(news.gemini_retry_delay(response, 1), 16.425)

    def test_retry_after_http_header_is_respected(self):
        response = gemini_response(429, {}, headers={"Retry-After": "34"})
        self.assertEqual(news.gemini_retry_delay(response, 1), 36)

    def test_long_quota_exhaustion_fails_instead_of_retrying_indefinitely(self):
        response = gemini_response(429, {}, headers={"Retry-After": "3600"})
        with self.assertRaisesRegex(RuntimeError, "wyczerpany limit"):
            news.gemini_retry_delay(response, 1)

    def test_retry_429_then_return_valid_json(self):
        limited = gemini_response(429, {
            "error": {"details": [
                {"@type": "type.googleapis.com/google.rpc.RetryInfo",
                 "retryDelay": "12s"}
            ]}
        })
        good = gemini_response(200, {
            "candidates": [{"content": {"parts": [{"text": '{"items":[1,2]}'}]}}]
        })
        with patch.object(news, "API_KEY", "fake"), \
             patch.object(news, "wait_for_gemini_slot") as slot, \
             patch.object(news.time, "sleep") as sleep, \
             patch.object(news.requests, "post", side_effect=[limited, good]) as post:
            result = news.gemini_json("Select stories")
        self.assertEqual(result, {"items": [1, 2]})
        self.assertEqual(slot.call_count, 2)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(14)

    def test_pacing_between_calls(self):
        with patch.object(news, "_last_gemini_call", None), \
             patch.object(news.time, "monotonic", side_effect=[100.0, 100.0, 102.0, 106.0]), \
             patch.object(news.time, "sleep") as sleep:
            news.wait_for_gemini_slot()
            news.wait_for_gemini_slot()
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], news.GEMINI_MIN_INTERVAL-2.0)

    def test_short_digest_does_not_trigger_extra_api_call_by_default(self):
        original = {
            "title": "Test title",
            "source": "BBC",
            "url": "https://example.com/news",
            "published_at": "2026-10-14T12:00:00+00:00",
            "snippet": "Verified excerpt",
            "article_text": "Actual source text",
            "category": "Nauka",
            "topics": ["science"],
            "editorial_score": 9,
        }
        response = {"items": [{
            "index": 0, "title": "Tytuł",
            "summary": "Krótki opis",
            "why_it_matters": "Ważny kontekst",
            "category": "Nauka", "topics": ["science"],
            "digest_text": "Streszczenie oparte na źródle",
        }]}
        with patch.dict(news.os.environ, {"REGENERATE_SHORT_DIGESTS": "false"}), \
             patch.object(news, "gemini_json", return_value=response) as gemini, \
             patch.object(news, "regenerate_long_digest", side_effect=AssertionError("Unexpected extra API call")):
            selected = news.build_digest_batch([original], 0)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["digest_text"], "Streszczenie oparte na źródle")
        gemini.assert_called_once()


if __name__ == "__main__":
    unittest.main()
