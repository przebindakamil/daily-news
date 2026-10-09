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

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    attempts = [cleaned]

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        attempts.append(cleaned[first_brace:last_brace + 1])

    # Gemini occasionally leaves a trailing comma before } or ].
    attempts.extend(
        re.sub(r",\s*([}\]])", r"\1", candidate)
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
        return text[:14000], final_url
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


def regenerate_long_digest(original):
    article_text = original.get("article_text", "")
    if not article_text:
        return ""

    prompt = f"""
Napisz po polsku płynne streszczenie artykułu do czytania przez około 3-4 minuty.

Zasady:
- 650-850 słów;
- 4-8 naturalnych akapitów;
- żadnych bullet pointów, śródtytułów ani checklist;
- zachowaj najważniejsze fakty, kontekst, zależności i sens oryginału;
- nie dodawaj opinii, porad ani faktów spoza tekstu;
- nie rozwlekaj sztucznie i nie powtarzaj tych samych informacji;
- tekst ma brzmieć jak skrócona wersja dobrego artykułu.

Zwróć wyłącznie JSON:
{{"digest_text":"..."}}

TYTUŁ:
{original.get("title", "")}

TREŚĆ:
{article_text}
""".strip()

    result = gemini_json(prompt)
    return str(result.get("digest_text") or "").strip()


def build_digest_batch(batch, batch_offset):
    finalists = []
    for local_idx, item in enumerate(batch):
        finalists.append(
            {
                "index": local_idx,
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
Redagujesz małą partię {len(finalists)} historii. Każda pozycja wejściowa ma zostać zwrócona dokładnie raz.

Najważniejsze kryterium: czy materiał jest naprawdę wart czasu czytelnika?
Nie dopisuj faktów spoza wejścia.

Dozwolone kategorie:
{json.dumps(ALLOWED_CATEGORIES, ensure_ascii=False)}

Dla każdego materiału przygotuj:
- index: ten sam indeks z wejścia,
- title: rzeczowy tytuł po polsku, bez clickbaitu,
- summary: maksymalnie 2 krótkie zdania na kafelek,
- why_it_matters: jedno krótkie zdanie,
- category: dokładnie jedna dozwolona kategoria,
- topics: 2-5 krótkich tematów,
- digest_text: płynne streszczenie artykułu do czytania, bez list, śródtytułów i punktów.

Zasady dla digest_text:
- ma brzmieć jak skrócona wersja normalnego artykułu, nie jak notatki;
- jeśli masz article_text, napisz około 650-850 słów, tak aby streszczenie zajmowało około 3-4 minut czytania; zachowaj najważniejsze fakty, kontekst i sens oryginału;
- używaj 3-6 naturalnych akapitów;
- nie dodawaj porad, ocen ani sekcji typu "co dalej", jeśli nie wynikają z tekstu;
- nie powtarzaj mechanicznie summary ani why_it_matters;
- jeśli article_text jest pusty, NIE rozwlekaj snippetu sztucznie: napisz tylko tyle, ile bezpiecznie wynika z dostępnych danych;
- nie dopisuj żadnych faktów spoza wejścia.

Zwróć WYŁĄCZNIE poprawny JSON bez markdownu.

JSON:
{{
  "items": [
    {{
      "index": 0,
      "title": "...",
      "summary": "...",
      "why_it_matters": "...",
      "category": "...",
      "topics": ["...", "..."],
      "digest_text": "Kilka naturalnych akapitów streszczenia..."
    }}
  ]
}}

PARTIA:
{json.dumps(finalists, ensure_ascii=False)}
""".strip()

    result = gemini_json(prompt)
    selected = []
    used = set()

    for edited in result.get("items", []):
        idx = int(edited.get("index", -1))
        if idx < 0 or idx >= len(batch) or idx in used:
            continue
        used.add(idx)
        original = batch[idx]

        category = str(edited.get("category") or original["category"]).strip()
        if category not in ALLOWED_CATEGORIES:
            category = original["category"]

        digest_text = str(edited.get("digest_text") or "").strip()
        if original.get("article_text") and len(digest_text.split()) < 450:
            print(
                f"Digest za krótki ({len(digest_text.split())} słów) dla: "
                f"{original['title'][:80]} — regeneruję osobno."
            )
            regenerated = regenerate_long_digest(original)
            if regenerated:
                digest_text = regenerated

        selected.append(
            {
                "_order": batch_offset + idx,
                "title": str(edited.get("title") or original["title"]).strip(),
                "summary": str(edited.get("summary") or "").strip(),
                "why_it_matters": str(edited.get("why_it_matters") or "").strip(),
                "category": category,
                "topics": [
                    str(topic).strip()
                    for topic in (edited.get("topics") or original.get("topics") or [])
                    if str(topic).strip()
                ][:5],
                "editorial_score": original.get("editorial_score", 0),
                "digest_text": digest_text,
                "source": original["source"],
                "url": original["url"],
                "published_at": original["published_at"],
                "full_text_used": bool(original.get("article_text")),
            }
        )

    # Fallback: don't lose an article only because Gemini skipped an item.
    for idx, original in enumerate(batch):
        if idx in used:
            continue
        selected.append(
            {
                "_order": batch_offset + idx,
                "title": original["title"],
                "summary": original.get("snippet", "")[:500],
                "why_it_matters": original.get("ranking_reason", ""),
                "category": original["category"],
                "topics": original.get("topics", [])[:5],
                "editorial_score": original.get("editorial_score", 0),
                "digest_text": original.get("snippet", "")[:900],
                "source": original["source"],
                "url": original["url"],
                "published_at": original["published_at"],
                "full_text_used": bool(original.get("article_text")),
            }
        )

    return selected


def edit_finalists(ranked, preferences):
    top_count = int(preferences.get("top_stories", 10))
    more_count = int(preferences.get("more_stories", 10))
    target = min(top_count + more_count, 20, len(ranked))

    prepared = enrich_for_digest(ranked, limit=target)

    # Large single JSON responses were getting truncated/malformed.
    # Small batches are more reliable and still keep total cost predictable.
    batch_size = 2
    selected = []
    for offset in range(0, len(prepared), batch_size):
        batch = prepared[offset:offset + batch_size]
        print(
            f"Redaguję partię {offset // batch_size + 1}/"
            f"{(len(prepared) + batch_size - 1) // batch_size} "
            f"({len(batch)} materiałów)..."
        )
        selected.extend(build_digest_batch(batch, offset))

    selected.sort(key=lambda item: item.pop("_order"))
    return selected[:target], min(top_count, target)



def choose_top_of_day(items, limit=3):
    """Pick editorially strongest stories, preferring category diversity."""
    ranked = sorted(
        items,
        key=lambda item: float(item.get("editorial_score", 0)),
        reverse=True,
    )
    selected = []
    used_categories = set()

    for item in ranked:
        category = item.get("category")
        if category in used_categories:
            continue
        selected.append(item)
        if category:
            used_categories.add(category)
        if len(selected) >= limit:
            return selected

    for item in ranked:
        if item in selected:
            continue
        selected.append(item)
        if len(selected) >= limit:
            break

    return selected

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
    top_of_day = choose_top_of_day(selected, limit=3)

    generated_at = datetime.now(timezone.utc)
    local_day = generated_at.astimezone(LOCAL_TZ).date().isoformat()

    result = {
        "date": local_day,
        "generated_at": generated_at.isoformat(),
        "top_of_day": top_of_day,
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
