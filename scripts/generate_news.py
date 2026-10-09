import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "news.json"

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
PER_CATEGORY = int(os.environ.get("NEWS_PER_CATEGORY", "2"))

CATEGORIES = {
    "AI i technologia": "AI OR sztuczna inteligencja OR technologia",
    "Polska i świat": "Polska OR Europa OR świat najważniejsze wydarzenia",
    "Piłka nożna i sport": "piłka nożna OR football OR sport",
    "Finanse i biznes": "finanse OR gospodarka OR biznes OR rynki",
    "Nauka": "nauka OR badania OR kosmos OR medycyna",
    "Kultura": "film OR muzyka OR kultura OR książki",
}


def google_news_feed(query: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}&hl=pl&gl=PL&ceid=PL:pl"
    )


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def iso_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return value


def collect_candidates(query: str, limit: int = 14):
    feed = feedparser.parse(google_news_feed(query))
    items = []

    for entry in feed.entries[:limit]:
        source = ""
        if getattr(entry, "source", None):
            source = getattr(entry.source, "title", "") or ""

        title = (entry.get("title") or "").strip()
        if " - " in title and not source:
            title, source = title.rsplit(" - ", 1)

        items.append(
            {
                "title": title.strip(),
                "source": source.strip(),
                "url": entry.get("link", ""),
                "published_at": iso_date(entry.get("published", "")),
                "snippet": clean_html(entry.get("summary", ""))[:850],
            }
        )

    return items


def ask_gemini(category: str, candidates):
    if not API_KEY:
        raise RuntimeError("Brak GEMINI_API_KEY w GitHub Secrets.")

    count = min(PER_CATEGORY, len(candidates))
    prompt = f"""
Jesteś redaktorem minimalistycznego polskiego przeglądu wiadomości.
Kategoria: {category}

Z poniższej listy wybierz dokładnie {count} najważniejsze materiały.

Kryteria:
- znaczenie dla czytelnika,
- świeżość,
- wiarygodność źródła,
- brak duplikatów i tematów opisujących to samo wydarzenie,
- pierwszeństwo dla konkretnej informacji przed opinią lub clickbaitem.

Dla każdego wybranego materiału:
- użyj indeksu materiału z wejścia,
- popraw tytuł na naturalny, rzeczowy polski bez clickbaitu,
- napisz krótkie streszczenie 2-3 zdania,
- streszczenie może zawierać WYŁĄCZNIE fakty obecne w tytule lub snippecie,
- nie wymyślaj dat, liczb, nazw ani kontekstu, których nie ma w danych,
- nie dopisuj opinii.

Zwróć wyłącznie poprawny JSON:
{{"items":[{{"index":0,"title":"...","summary":"..."}}]}}

Materiały:
{json.dumps(candidates, ensure_ascii=False)}
""".strip()

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    response = requests.post(endpoint, json=payload, timeout=75)
    if not response.ok:
        raise RuntimeError(f"Gemini API error {response.status_code} for model {MODEL}: {response.text[:1200]}")
    body = response.json()

    text = body["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)

    selected = []
    used = set()

    for item in parsed.get("items", []):
        idx = int(item["index"])
        if idx in used or idx < 0 or idx >= len(candidates):
            continue

        used.add(idx)
        original = candidates[idx]
        selected.append(
            {
                "title": str(item.get("title") or original["title"]).strip(),
                "summary": str(item.get("summary") or "").strip(),
                "source": original["source"],
                "url": original["url"],
                "published_at": original["published_at"],
            }
        )

    return selected[:count]


def main():
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": [],
    }

    for category, query in CATEGORIES.items():
        candidates = collect_candidates(query)

        if not candidates:
            result["categories"].append({"name": category, "items": []})
            continue

        selected = ask_gemini(category, candidates)
        result["categories"].append({"name": category, "items": selected})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = sum(len(category["items"]) for category in result["categories"])
    print(f"Zapisano {total} wiadomości do {OUTPUT}")


if __name__ == "__main__":
    main()
