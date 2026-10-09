import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "news.json"
CURRENT_OUTPUT = ROOT / "data" / "current.json"
ARCHIVE_DIR = ROOT / "data" / "archive"
ARCHIVE_INDEX = ARCHIVE_DIR / "index.json"
LOCAL_TZ = ZoneInfo("Europe/Warsaw")
PREFERENCES = ROOT / "config" / "preferences.json"

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

SEARCHES = {
    "AI i technologia": [
        "AI OR sztuczna inteligencja OR modele językowe when:1d",
        "OpenAI OR Google Gemini OR Anthropic OR Microsoft AI when:1d",
        "technologia OR narzędzia AI OR automatyzacja when:1d",
    ],
    "Polska i świat": [
        "Polska najważniejsze wydarzenia when:1d",
        "Europa świat najważniejsze wydarzenia when:1d",
        "geopolityka OR bezpieczeństwo OR gospodarka świat when:1d",
    ],
    "Piłka nożna": [
        "piłka nożna Polska OR reprezentacja OR Ekstraklasa when:1d",
        "Champions League OR Premier League OR Serie A OR La Liga when:1d",
        "football transfers OR transfery piłkarskie when:1d",
    ],
    "Sport i trening": [
        "bieganie OR kolarstwo OR trening OR regeneracja badania when:3d",
        "sport science OR endurance OR strength training research when:3d",
    ],
    "Finanse i biznes": [
        "finanse OR gospodarka OR biznes OR rynki Polska when:1d",
        "giełda OR inwestowanie OR stopy procentowe OR inflacja when:1d",
        "startup OR biznes technologia when:1d",
    ],
    "Nauka": [
        "nauka OR badania OR kosmos OR medycyna when:2d",
        "science breakthrough OR research OR space when:2d",
    ],
    "Motoryzacja": [
        "motoryzacja OR samochody OR nowe auta OR automotive when:2d",
        "BMW OR Mercedes OR Porsche OR Toyota OR Volkswagen when:2d",
    ],
    "Podróże": [
        "podróże OR lotnictwo OR turystyka when:2d",
        "linie lotnicze OR nowe połączenia OR city break when:2d",
    ],
    "Kultura": [
        "film OR serial OR muzyka OR książki OR kultura when:2d",
        "Netflix OR HBO OR kino OR album OR premiera when:2d",
    ],
}


def load_preferences():
    return json.loads(PREFERENCES.read_text(encoding="utf-8"))


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


def parse_dt(value: str):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def normalize_title(value: str) -> str:
    value = (value or "").lower()
    value = value.replace("ł", "l")
    value = re.sub(r"[^a-ząćęłńóśźż0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def collect_candidates(max_age_hours: int):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    seen = set()
    items = []

    for category, queries in SEARCHES.items():
        for query in queries:
            feed = feedparser.parse(google_news_feed(query))
            for entry in feed.entries[:10]:
                source = ""
                if getattr(entry, "source", None):
                    source = getattr(entry.source, "title", "") or ""

                title = (entry.get("title") or "").strip()
                if " - " in title and not source:
                    title, source = title.rsplit(" - ", 1)

                published = iso_date(entry.get("published", ""))
                published_dt = parse_dt(published)
                if published_dt and published_dt < cutoff:
                    continue

                key = normalize_title(title)
                if not key or key in seen:
                    continue
                seen.add(key)

                items.append(
                    {
                        "category_hint": category,
                        "title": title,
                        "source": source.strip(),
                        "url": entry.get("link", ""),
                        "published_at": published,
                        "snippet": clean_html(entry.get("summary", ""))[:900],
                    }
                )

    return items


def gemini_json(prompt: str):
    if not API_KEY:
        raise RuntimeError("Brak GEMINI_API_KEY w GitHub Secrets.")

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

    response = requests.post(endpoint, json=payload, timeout=90)
    if not response.ok:
        raise RuntimeError(
            f"Gemini API error {response.status_code} for model {MODEL}: "
            f"{response.text[:1400]}"
        )

    body = response.json()
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def rank_candidates(candidates, preferences):
    profile = preferences["reader_profile"]
    priorities = preferences["priority_topics"]
    prefer = preferences["selection_rules"]["prefer"]
    avoid = preferences["selection_rules"]["avoid"]

    indexed = [
        {
            "index": idx,
            "category_hint": item["category_hint"],
            "title": item["title"],
            "source": item["source"],
            "published_at": item["published_at"],
            "snippet": item["snippet"],
        }
        for idx, item in enumerate(candidates)
    ]

    prompt = f"""
Jesteś redaktorem osobistego briefingu informacyjnego.

PROFIL CZYTELNIKA:
{profile}

PRIORYTETY:
{json.dumps(priorities, ensure_ascii=False)}

PREMIOWANIE:
{json.dumps(prefer, ensure_ascii=False)}

ODRZUCANIE:
{json.dumps(avoid, ensure_ascii=False)}

Oceń materiały od 0 do 10 w czterech wymiarach:
- importance: obiektywne znaczenie,
- personal_relevance: dopasowanie do profilu,
- novelty: nowość / zaskoczenie,
- usefulness: praktyczna lub poznawcza wartość.

Dodatkowo:
- połącz w głowie duplikaty dotyczące tego samego wydarzenia,
- dla każdego klastra wybierz najwyżej jeden najlepszy materiał,
- preferuj źródła bardziej wiarygodne i konkretne,
- nie podbijaj słabego materiału tylko dlatego, że pasuje do zainteresowań.

Zwróć maksymalnie 24 najlepsze pozycje jako JSON:
{{
  "ranked": [
    {{
      "index": 0,
      "importance": 0,
      "personal_relevance": 0,
      "novelty": 0,
      "usefulness": 0,
      "category": "AI i technologia",
      "topics": ["konkretny temat", "marka lub zjawisko"],
      "reason": "krótkie uzasadnienie"
    }}
  ]
}}

MATERIAŁY:
{json.dumps(indexed, ensure_ascii=False)}
""".strip()

    result = gemini_json(prompt)
    ranked = []

    for item in result.get("ranked", []):
        idx = int(item.get("index", -1))
        if idx < 0 or idx >= len(candidates):
            continue
        score = (
            float(item.get("importance", 0)) * 0.30
            + float(item.get("personal_relevance", 0)) * 0.35
            + float(item.get("novelty", 0)) * 0.15
            + float(item.get("usefulness", 0)) * 0.20
        )
        enriched = dict(candidates[idx])
        enriched["category"] = str(item.get("category") or candidates[idx]["category_hint"])
        enriched["topics"] = [
            str(topic).strip()
            for topic in item.get("topics", [])
            if str(topic).strip()
        ][:6]
        enriched["editorial_score"] = round(score, 2)
        enriched["ranking_reason"] = str(item.get("reason") or "")
        ranked.append(enriched)

    ranked.sort(key=lambda x: x["editorial_score"], reverse=True)
    return ranked[:24]


def edit_finalists(ranked, preferences):
    top_count = int(preferences.get("top_stories", 5))
    more_count = int(preferences.get("more_stories", 4))
    target = min(top_count + more_count, len(ranked))

    finalists = []
    for idx, item in enumerate(ranked[:18]):
        finalists.append(
            {
                "index": idx,
                "title": item["title"],
                "source": item["source"],
                "published_at": item["published_at"],
                "snippet": item["snippet"],
                "category": item["category"],
                "topics": item.get("topics", []),
                "editorial_score": item["editorial_score"],
                "ranking_reason": item["ranking_reason"],
            }
        )

    prompt = f"""
Jesteś redaktorem końcowym osobistego briefingu wiadomości.

Wybierz dokładnie {target} najlepszych historii z finalistów.
Pierwsze {top_count} ma trafić do sekcji "Dzisiaj warto wiedzieć".
Pozostałe {more_count} mogą trafić do "Jeszcze warto zobaczyć".

Najważniejsze:
- briefing ma być ciekawy, nie reprezentatywny za wszelką cenę,
- NIE musisz mieć po jednym newsie z każdej kategorii,
- jeśli trzy najlepsze materiały są z AI albo piłki, mogą wygrać,
- nie wybieraj dwóch historii o tym samym wydarzeniu,
- odrzuć materiały przeciętne, nawet jeśli przez to jakaś kategoria zniknie,
- unikaj starych, lokalnych lub marginalnych historii bez szerszego znaczenia.

Dla każdej wybranej historii:
- zachowaj index,
- napisz rzeczowy tytuł po polsku, bez clickbaitu,
- napisz 2-3 zdania konkretnego streszczenia wyłącznie z danych wejściowych,
- dodaj "why_it_matters": jedno zdanie wyjaśniające, dlaczego czytelnik powinien to wiedzieć,
- przypisz krótką kategorię,
- nie wymyślaj faktów, których nie ma w danych.

Zwróć JSON:
{{
  "items": [
    {{
      "index": 0,
      "title": "...",
      "summary": "...",
      "why_it_matters": "...",
      "category": "...",
      "topics": ["2-5 krótkich tematów opisujących materiał"]
    }}
  ]
}}

FINALIŚCI:
{json.dumps(finalists, ensure_ascii=False)}
""".strip()

    result = gemini_json(prompt)
    selected = []
    used = set()

    for edited in result.get("items", []):
        idx = int(edited.get("index", -1))
        if idx < 0 or idx >= len(ranked[:18]) or idx in used:
            continue
        used.add(idx)
        original = ranked[idx]

        selected.append(
            {
                "title": str(edited.get("title") or original["title"]).strip(),
                "summary": str(edited.get("summary") or "").strip(),
                "why_it_matters": str(edited.get("why_it_matters") or "").strip(),
                "category": str(edited.get("category") or original["category"]).strip(),
                "topics": [
                    str(topic).strip()
                    for topic in (edited.get("topics") or original.get("topics") or [])
                    if str(topic).strip()
                ][:6],
                "editorial_score": original.get("editorial_score", 0),
                "source": original["source"],
                "url": original["url"],
                "published_at": original["published_at"],
            }
        )

    return selected[:target], top_count


def main():
    preferences = load_preferences()
    max_age_hours = int(preferences.get("max_age_hours", 72))

    candidates = collect_candidates(max_age_hours)
    if not candidates:
        raise RuntimeError("Nie znaleziono świeżych kandydatów z Google News RSS.")

    ranked = rank_candidates(candidates, preferences)
    if not ranked:
        raise RuntimeError("Gemini nie zwrócił żadnych poprawnych finalistów.")

    selected, top_count = edit_finalists(ranked, preferences)
    top_stories = selected[:top_count]
    more_stories = selected[top_count:]

    generated_at = datetime.now(timezone.utc)
    local_day = generated_at.astimezone(LOCAL_TZ).date().isoformat()

    result = {
        "date": local_day,
        "generated_at": generated_at.isoformat(),
        "top_stories": top_stories,
        "more_stories": more_stories,
        "stats": {
            "candidates": len(candidates),
            "ranked": len(ranked),
            "published": len(selected),
        },
    }

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # news.json zostaje dla zgodności wstecznej, current.json jest jawnym
    # wskaźnikiem na najnowszy briefing, a archiwum nigdy nie jest nadpisywane
    # przez kolejny dzień.
    OUTPUT.write_text(serialized, encoding="utf-8")
    CURRENT_OUTPUT.write_text(serialized, encoding="utf-8")
    (ARCHIVE_DIR / f"{local_day}.json").write_text(serialized, encoding="utf-8")

    archive_dates = []
    if ARCHIVE_INDEX.exists():
        try:
            archive_dates = json.loads(ARCHIVE_INDEX.read_text(encoding="utf-8")).get("dates", [])
        except (json.JSONDecodeError, AttributeError):
            archive_dates = []

    archive_dates = sorted(set(archive_dates + [local_day]), reverse=True)
    ARCHIVE_INDEX.write_text(
        json.dumps(
            {
                "latest": local_day,
                "dates": archive_dates,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Zebrano {len(candidates)} kandydatów, "
        f"oceniono {len(ranked)}, opublikowano {len(selected)}. "
        f"Archiwum: {local_day}."
    )


if __name__ == "__main__":
    main()
