import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
import trafilatura

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "news.json"
CURRENT_OUTPUT = ROOT / "data" / "current.json"
ARCHIVE_DIR = ROOT / "data" / "archive"
ARCHIVE_INDEX = ARCHIVE_DIR / "index.json"
LOCAL_TZ = ZoneInfo("Europe/Warsaw")
PREFERENCES = ROOT / "config" / "preferences.json"
SOURCES = ROOT / "config" / "sources.json"

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

SEARCHES = {
    "AI i technologia": ["AI sztuczna inteligencja technologia automatyzacja when:1d"],
    "Polska": ["Polska najważniejsze wydarzenia społeczeństwo gospodarka when:1d"],
    "Świat i geopolityka": ["świat geopolityka bezpieczeństwo Europa USA Azja when:1d"],
    "Piłka nożna": ["piłka nożna Ekstraklasa reprezentacja Champions League transfery when:1d"],
    "Sport i trening": ["sport trening bieganie kolarstwo regeneracja badania when:2d"],
    "Zdrowie": ["zdrowie medycyna profilaktyka badania zdrowotne when:2d"],
    "Finanse i inwestowanie": ["finanse inwestowanie giełda stopy procentowe inflacja when:1d"],
    "Biznes i startupy": ["biznes startup przedsiębiorczość firmy technologia when:1d"],
    "Nauka": ["nauka badania odkrycie fizyka biologia archeologia when:2d"],
    "Kosmos": ["kosmos astronomia NASA ESA SpaceX misja when:2d"],
    "Motoryzacja": ["motoryzacja samochody automotive nowe auta technologie when:2d"],
    "Podróże": ["podróże lotnictwo turystyka linie lotnicze city break when:2d"],
    "Kultura": ["film serial muzyka książki kultura kino premiera when:2d"],
    "Gaming": ["gry gaming PlayStation Xbox Nintendo PC premiera when:2d"],
    "Środowisko i klimat": ["klimat środowisko energia pogoda badania when:2d"],
    "Praca i kariera": ["praca kariera rynek pracy wynagrodzenia kompetencje when:2d"],
    "Nieruchomości i dom": ["nieruchomości mieszkania dom budownictwo remont when:2d"],
}

ALLOWED_CATEGORIES = list(SEARCHES.keys())


def load_preferences():
    return json.loads(PREFERENCES.read_text(encoding="utf-8"))


def load_sources():
    return json.loads(SOURCES.read_text(encoding="utf-8"))


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
    value = (value or "").lower().replace("ł", "l")
    value = re.sub(r"[^a-ząćęłńóśźż0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def candidate_key(title: str):
    normalized = normalize_title(title)
    # Keep enough words for dedupe while tolerating source suffix differences.
    return " ".join(normalized.split()[:14])


def add_feed_entries(items, seen, feed_url, category, tier, max_items, cutoff):
    feed = feedparser.parse(feed_url)
    for entry in feed.entries[:max_items]:
        source = ""
        if getattr(entry, "source", None):
            source = getattr(entry.source, "title", "") or ""
        source = source.strip() or (getattr(feed.feed, "title", "") or "").strip()

        title = (entry.get("title") or "").strip()
        if " - " in title and not source:
            title, source = title.rsplit(" - ", 1)

        published = iso_date(entry.get("published", "") or entry.get("updated", ""))
        published_dt = parse_dt(published)
        if published_dt and published_dt < cutoff:
            continue

        key = candidate_key(title)
        if not key or key in seen:
            continue
        seen.add(key)

        items.append(
            {
                "category_hint": category,
                "title": title,
                "source": source,
                "url": entry.get("link", ""),
                "published_at": published,
                "snippet": clean_html(entry.get("summary", "") or entry.get("description", ""))[:1000],
                "source_tier": tier,
                "discovery_origin": "direct_rss",
            }
        )


def add_google_query(items, seen, query, category, tier, max_items, cutoff, origin):
    feed = feedparser.parse(google_news_feed(query))
    for entry in feed.entries[:max_items]:
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

        key = candidate_key(title)
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
                "snippet": clean_html(entry.get("summary", ""))[:1000],
                "source_tier": tier,
                "discovery_origin": origin,
            }
        )


def collect_candidates(max_age_hours: int):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    seen = set()
    items = []
    sources = load_sources()

    # 1) Direct feeds from established outlets and primary sources.
    for source in sources.get("rss_sources", []):
        add_feed_entries(
            items,
            seen,
            source["url"],
            source["category"],
            source.get("tier", "quality"),
            max_items=10,
            cutoff=cutoff,
        )

    # 2) Trusted-domain discovery. Still uses Google News as an index,
    #    but only to discover material from selected high-quality/primary domains.
    for source in sources.get("trusted_google_queries", []):
        add_google_query(
            items,
            seen,
            source["query"],
            source["category"],
            source.get("tier", "quality"),
            max_items=7,
            cutoff=cutoff,
            origin="trusted_google",
        )

    # 3) Broad discovery is fallback/diversity, not the main source pool.
    for category, queries in SEARCHES.items():
        for query in queries:
            add_google_query(
                items,
                seen,
                query,
                category,
                "discovery",
                max_items=4,
                cutoff=cutoff,
                origin="broad_google",
            )

    return items


def parse_model_json(text: str):
    """Parse JSON defensively in case the model adds fences or minor syntax noise."""
    cleaned = (text or "").strip()

    if cleaned.startswith("\`\`\`"):
        cleaned = re.sub(r"^\`\`\`(?:json)?\\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\\s*\`\`\`$", "", cleaned)

    attempts = [cleaned]

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        attempts.append(cleaned[first_brace:last_brace + 1])

    # Gemini occasionally leaves a trailing comma before } or ].
    attempts.extend(
        re.sub(r",\\s*([}\\]])", r"\\1", candidate)
        for candidate in list(attempts)
    )

    last_error = None
    for candidate in attempts:
        try:
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict):
                raise ValueError("Oczekiwano obiektu JSON na najwyższym poziomie.")
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc

    raise last_error or ValueError("Nie udało się sparsować odpowiedzi JSON.")


def gemini_json(prompt: str, retries: int = 3):
    if not API_KEY:
        raise RuntimeError("Brak GEMINI_API_KEY w GitHub Secrets.")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={API_KEY}"
    )

    last_error = None
    last_text = ""

    for attempt in range(1, retries + 1):
        strict_prompt = prompt
        if attempt > 1:
            strict_prompt += (
                "\\n\\nUWAGA: poprzednia odpowiedź nie była poprawnym JSON-em. "
                "Zwróć TYLKO jeden poprawny obiekt JSON. "
                "Używaj wyłącznie podwójnych cudzysłowów, bez komentarzy, "
                "bez markdownu i bez przecinków po ostatnim elemencie."
            )

        payload = {
            "contents": [{"parts": [{"text": strict_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1 if attempt > 1 else 0.18,
                "maxOutputTokens": 8192,
            },
        }

        response = requests.post(endpoint, json=payload, timeout=120)
        if not response.ok:
            raise RuntimeError(
                f"Gemini API error {response.status_code} for model {MODEL}: "
                f"{response.text[:1400]}"
            )

        body = response.json()

        try:
            last_text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Gemini zwrócił odpowiedź bez oczekiwanej treści: "
                f"{json.dumps(body, ensure_ascii=False)[:1400]}"
            ) from exc

        try:
            return parse_model_json(last_text)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            print(
                f"Niepoprawny JSON z Gemini — próba {attempt}/{retries}: {exc}. "
                f"Fragment odpowiedzi: {last_text[:500]!r}"
            )

    raise RuntimeError(
        "Gemini po kilku próbach nadal nie zwrócił poprawnego JSON. "
        f"Ostatni błąd: {last_error}. "
        f"Fragment odpowiedzi: {last_text[:1200]!r}"
    )


def rank_candidates(candidates, preferences):
    indexed = [
        {
            "index": idx,
            "category_hint": item["category_hint"],
            "title": item["title"],
            "source": item["source"],
            "published_at": item["published_at"],
            "snippet": item["snippet"],
            "source_tier": item.get("source_tier", "discovery"),
            "discovery_origin": item.get("discovery_origin", "unknown"),
        }
        for idx, item in enumerate(candidates)
    ]

    prompt = f"""
Jesteś redaktorem szerokiego, wysokiej jakości briefingu informacyjnego.
Tworzysz wspólną pulę materiałów, z której później różni użytkownicy dostaną własny feed.

Ogólny profil redakcyjny:
{preferences["reader_profile"]}

Premiuj:
{json.dumps(preferences["selection_rules"]["prefer"], ensure_ascii=False)}

Odrzucaj:
{json.dumps(preferences["selection_rules"]["avoid"], ensure_ascii=False)}

Dozwolone kategorie:
{json.dumps(ALLOWED_CATEGORIES, ensure_ascii=False)}

Oceń każdy wartościowy materiał od 0 do 10:
- importance: obiektywne znaczenie,
- novelty: nowość / zaskoczenie,
- usefulness: praktyczna lub poznawcza wartość,
- quality: jakość i konkretność informacji,
- worth_time: czy ten materiał jest wart 2 minut uwagi przeciętnego, ciekawego świata czytelnika.

Źródła mają oznaczenie source_tier:
- primary: źródło pierwotne / instytucja / organizacja,
- wire: agencja informacyjna,
- quality: uznane medium,
- discovery: szerokie discovery o niższym priorytecie.

Przy podobnej wartości preferuj primary, wire i quality nad discovery.
Nie faworyzuj jednej grupy zainteresowań. Pula ma być szeroka i różnorodna.
Usuń duplikaty dotyczące tego samego wydarzenia i zostaw najlepsze źródło.
Zwróć maksymalnie 36 najlepszych historii.

JSON:
{{
  "ranked": [
    {{
      "index": 0,
      "importance": 0,
      "novelty": 0,
      "usefulness": 0,
      "quality": 0,
      "worth_time": 0,
      "category": "jedna z dozwolonych kategorii",
      "topics": ["2-6 konkretnych tematów, nazw lub zjawisk"],
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
            float(item.get("importance", 0)) * 0.35
            + float(item.get("novelty", 0)) * 0.20
            + float(item.get("usefulness", 0)) * 0.25
            + float(item.get("quality", 0)) * 0.15
            + float(item.get("worth_time", 0)) * 0.20
        )

        tier_bonus = {
            "primary": 0.65,
            "wire": 0.55,
            "quality": 0.35,
            "discovery": 0.0,
        }.get(candidates[idx].get("source_tier", "discovery"), 0.0)
        score += tier_bonus

        enriched = dict(candidates[idx])
        category = str(item.get("category") or candidates[idx]["category_hint"]).strip()
        if category not in ALLOWED_CATEGORIES:
            category = candidates[idx]["category_hint"]

        enriched["category"] = category
        enriched["topics"] = [
            str(topic).strip()
            for topic in item.get("topics", [])
            if str(topic).strip()
        ][:6]
        enriched["editorial_score"] = round(score, 2)
        enriched["ranking_reason"] = str(item.get("reason") or "")
        ranked.append(enriched)

    ranked.sort(key=lambda x: x["editorial_score"], reverse=True)
    return ranked[:36]


def extract_article_text(url: str):
    if not url:
        return "", url

    try:
        response = requests.get(
            url,
            timeout=15,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; DailyNewsBriefing/1.0; "
                    "+https://github.com/przebindakamil/daily-news)"
                )
            },
        )
        response.raise_for_status()
        final_url = response.url

        text = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            output_format="txt",
        ) or ""

        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 450:
            return "", final_url
        return text[:3200], final_url
    except Exception:
        return "", url


def enrich_for_digest(ranked, limit=20):
    enriched = []
    for item in ranked[:limit]:
        copy = dict(item)
        full_text, final_url = extract_article_text(item.get("url", ""))
        copy["article_text"] = full_text
        if final_url and "news.google.com" not in urlparse(final_url).netloc:
            copy["url"] = final_url
        enriched.append(copy)
    return enriched


def edit_finalists(ranked, preferences):
    top_count = int(preferences.get("top_stories", 10))
    more_count = int(preferences.get("more_stories", 10))
    target = min(top_count + more_count, 20, len(ranked))

    prepared = enrich_for_digest(ranked, limit=target)
    finalists = []

    for idx, item in enumerate(prepared):
        finalists.append(
            {
                "index": idx,
                "title": item["title"],
                "source": item["source"],
                "published_at": item["published_at"],
                "snippet": item["snippet"],
                "article_text": item.get("article_text", ""),
                "category": item["category"],
                "topics": item.get("topics", []),
                "editorial_score": item["editorial_score"],
                "source_tier": item.get("source_tier", "discovery"),
                "discovery_origin": item.get("discovery_origin", "unknown"),
            }
        )

    prompt = f"""
Jesteś redaktorem końcowym aplikacji z wiadomościami.
Masz przygotować {target} wartościowych historii z szerokiej puli.
Nie musisz rozkładać ich równo między kategoriami, ale unikaj monotematyczności.
Najważniejsze kryterium końcowe brzmi: "czy ten materiał jest naprawdę wart czasu czytelnika?"
Nie zapełniaj zestawu słabymi newsami tylko dlatego, że reprezentują kategorię.
Jeśli kilka materiałów dotyczy tego samego wydarzenia, zostaw jeden najlepszy.
Przy porównywalnej wartości preferuj źródła pierwotne, agencje i uznane media.

Dozwolone kategorie:
{json.dumps(ALLOWED_CATEGORIES, ensure_ascii=False)}

Dla każdego materiału przygotuj:
- title: rzeczowy tytuł po polsku bez clickbaitu,
- summary: 2-3 zdania na kafelek,
- why_it_matters: jedno zdanie, dlaczego warto to wiedzieć,
- category: dokładnie jedna dozwolona kategoria,
- topics: 2-6 krótkich tematów,
- digest:
  - what_happened: 2-4 zdania,
  - key_points: 3-5 konkretnych punktów,
  - context: krótki kontekst, jeśli wynika z danych,
  - what_next: czego warto wypatrywać dalej, ale tylko jeśli wynika z danych.

Najważniejsza zasada:
NIE DOPISUJ faktów spoza wejścia.
Jeśli article_text jest pusty, digest ma bazować wyłącznie na tytule i snippecie.
Jeśli article_text jest dostępny, możesz wykorzystać zawarte tam informacje.
Nie udawaj, że znasz pełny artykuł, jeśli go nie masz.

JSON:
{{
  "items": [
    {{
      "index": 0,
      "title": "...",
      "summary": "...",
      "why_it_matters": "...",
      "category": "...",
      "topics": ["..."],
      "digest": {{
        "what_happened": "...",
        "key_points": ["...", "...", "..."],
        "context": "...",
        "what_next": "..."
      }}
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
        if idx < 0 or idx >= len(prepared) or idx in used:
            continue
        used.add(idx)
        original = prepared[idx]

        category = str(edited.get("category") or original["category"]).strip()
        if category not in ALLOWED_CATEGORIES:
            category = original["category"]

        digest = edited.get("digest") or {}
        selected.append(
            {
                "title": str(edited.get("title") or original["title"]).strip(),
                "summary": str(edited.get("summary") or "").strip(),
                "why_it_matters": str(edited.get("why_it_matters") or "").strip(),
                "category": category,
                "topics": [
                    str(topic).strip()
                    for topic in (edited.get("topics") or original.get("topics") or [])
                    if str(topic).strip()
                ][:6],
                "editorial_score": original.get("editorial_score", 0),
                "digest": {
                    "what_happened": str(digest.get("what_happened") or "").strip(),
                    "key_points": [
                        str(point).strip()
                        for point in digest.get("key_points", [])
                        if str(point).strip()
                    ][:5],
                    "context": str(digest.get("context") or "").strip(),
                    "what_next": str(digest.get("what_next") or "").strip(),
                },
                "source": original["source"],
                "url": original["url"],
                "published_at": original["published_at"],
                "full_text_used": bool(original.get("article_text")),
            }
        )

    return selected[:target], top_count


def main():
    preferences = load_preferences()
    max_age_hours = int(preferences.get("max_age_hours", 72))

    candidates = collect_candidates(max_age_hours)
    if not candidates:
        raise RuntimeError("Nie znaleziono świeżych kandydatów z żadnego skonfigurowanego źródła.")

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

    OUTPUT.write_text(serialized, encoding="utf-8")
    CURRENT_OUTPUT.write_text(serialized, encoding="utf-8")
    (ARCHIVE_DIR / f"{local_day}.json").write_text(serialized, encoding="utf-8")

    archive_dates = []
    if ARCHIVE_INDEX.exists():
        try:
            archive_dates = json.loads(
                ARCHIVE_INDEX.read_text(encoding="utf-8")
            ).get("dates", [])
        except (json.JSONDecodeError, AttributeError):
            archive_dates = []

    archive_dates = sorted(set(archive_dates + [local_day]), reverse=True)
    ARCHIVE_INDEX.write_text(
        json.dumps(
            {"latest": local_day, "dates": archive_dates},
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
