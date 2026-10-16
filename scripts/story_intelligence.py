"""Conservative news source grouping and story continuity without extra AI calls.

All matching is intentionally high-precision: unrelated events must not merge.
Never claim source independence or fact-check certainty from domain count alone.
"""
import hashlib
import ipaddress
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

TRACKING_KEYS = {"fbclid", "gclid", "dclid", "mc_cid", "mc_eid", "igshid",
                 "ref_src", "ref_url", "utm_source", "utm_medium", "utm_campaign",
                 "utm_content", "utm_term"}
STOPWORDS = frozenset(
    "and the with from this that have after says said were will what when for about "
    "oraz dla jest jako przez nad pod oraz nie sie się czy już oraz także które "
    "który która więc były był jest jego jej ich tego tej takie mamy nowy nowe "
    "news says reports report latest update updates more than into"
    .split()
)
NUMERIC = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?%?(?![\w])")


def canonical_url(url):
    """Strip safe tracking bits only; preserve page identifiers and Google URLs."""
    try:
        u = urlsplit(str(url or "").strip())
        if u.scheme.lower() not in {"http", "https"} or not u.hostname:
            return ""
        if u.username or u.password:
            return ""
        host = u.hostname.lower().removeprefix("www.")
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
            return ""
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return ""
        except ValueError:
            pass
        port = f":{u.port}" if u.port and u.port not in (80, 443) else ""
        path = u.path or "/"
        if path != "/":
            path = path.rstrip("/")
        query = urlencode([
            (k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
            if k.lower() not in TRACKING_KEYS and not k.lower().startswith("utm_")
        ])
        return urlunsplit(("https", host + port, path, query, ""))
    except (ValueError, TypeError):
        return ""


def source_health(url, client=requests):
    """A best-effort, bounded public URL check, never an assertion of accuracy.

    HEAD may be blocked by legitimate paywalled publishers. Only treat
    confirmed 404/410 from BOTH HEAD and GET as missing.
    """
    target = canonical_url(url)
    if not target:
        return "invalid"
    try:
        result = client.head(target, allow_redirects=True, timeout=4)
        if result.status_code in (404, 410, 405):
            # A publisher can reject HEAD; verify using a streaming GET.
            fallback = client.get(
                target, allow_redirects=True, timeout=4, stream=True,
                headers={"Range": "bytes=0-127"},
            )
            try:
                return "missing" if fallback.status_code in (404, 410) else (
                    "reachable" if fallback.status_code < 400 else "unverified"
                )
            finally:
                fallback.close()
        if result.status_code < 400:
            return "reachable"
    except requests.RequestException:
        pass
    return "unverified"


def publisher_domain(url):
    canonical = canonical_url(url)
    if not canonical:
        return ""
    host = urlsplit(canonical).hostname or ""
    # Indexer and link shorteners are NOT independent publishers.
    if host in {"news.google.com", "google.com", "bit.ly", "t.co"}:
        return ""
    return host


def words(value):
    return set(w for w in re.findall(r"[^\W_]+", str(value or "").casefold(),
                                     flags=re.UNICODE)
               if len(w) > 3 and w not in STOPWORDS)


def title_similarity(a, b):
    one, two = words(a), words(b)
    if not one or not two:
        return 0.0
    # F1 overlap prevents a long generic article from matching a tiny headline.
    common = len(one & two)
    return 2 * common / (len(one) + len(two))


def same_event(a, b, threshold=0.92):
    if a.get("category", a.get("category_hint")) != b.get("category", b.get("category_hint")):
        return False
    if canonical_url(a.get("url")) and canonical_url(a.get("url")) == canonical_url(b.get("url")):
        return True
    return title_similarity(a.get("title"), b.get("title")) >= threshold


def group_candidates(candidates):
    """Attach alternate citations to a representative; never merge loosely.

    Run before model ranking so Gemini sees complete but deduplicated candidates.
    """
    groups = []
    for item in candidates:
        chosen = None
        for leader in groups:
            if same_event(leader, item):
                chosen = leader
                break
        if chosen is None:
            copy = dict(item)
            copy["related_sources"] = []
            groups.append(copy)
        else:
            link = canonical_url(item.get("url"))
            if link and link != canonical_url(chosen.get("url")):
                chosen["related_sources"].append({
                    "source": item.get("source") or publisher_domain(link) or "Źródło",
                    "url": item["url"],
                })
    return groups


def source_summary(item):
    options = [{"source": item.get("source", ""), "url": item.get("url", "")}]
    options.extend(item.get("related_sources") or [])
    cleaned, seen = [], set()
    for entry in options:
        url = canonical_url(entry.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        cleaned.append({"source": str(entry.get("source") or publisher_domain(url) or "Źródło"),
                        "url": url})
    domains = {publisher_domain(x["url"]) for x in cleaned}
    domains.discard("")
    return {
        "canonical_url": canonical_url(item.get("url")),
        "related_sources": cleaned[1:5],
        "source_count": len(cleaned),
        # Count distinct publisher domains, NOT independently verified reporting.
        "publisher_count": len(domains),
        "source_count_label": "publikacji",  # avoid claiming confirmations
    }


def plausible_publication(item, start, end):
    """Strict publication date/URL format, no network calls to hostile paywalls."""
    parsed_url = canonical_url(item.get("url"))
    try:
        published = datetime.fromisoformat(str(item.get("published_at", "")))
        if published.tzinfo is None:
            return False
        return bool(parsed_url and start <= published.astimezone(timezone.utc) < end)
    except (ValueError, TypeError):
        return False


def fact_warnings(item):
    """Flag numeric claims absent from original article, without silent rewriting.

    A flag indicates review needed, not a proven hallucination; formatted numbers
    may differ in source languages. No extra model calls are made.
    """
    source = str(item.get("article_text") or "")
    digest = str(item.get("digest_text") or "")
    if not source or not digest:
        return {"checked": False, "warnings": []}
    source_numbers = set(NUMERIC.findall(source))
    digest_numbers = set(NUMERIC.findall(digest))
    missing = sorted(digest_numbers - source_numbers)[:12]
    return {"checked": True, "warnings": missing}


def recent_entries(archive_dir, day, days=7):
    """Only read earlier calendar dates; never use current/future issues."""
    today = datetime.fromisoformat(str(day)).date()
    history = []
    for offset in range(1, days + 1):
        date = (today - timedelta(days=offset)).isoformat()
        file = Path(archive_dir) / f"{date}.json"
        if not file.is_file():
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for item in data.get("top_stories", []) + data.get("more_stories", []):
            history.append({**item, "archive_date": date})
    return history


def match_previous(item, history):
    """Conservative cross-day match: same category plus title and topic agreement."""
    topics = words(" ".join(item.get("topics") or []))
    best, best_score = None, 0.0
    for old in history:
        if item.get("category") != old.get("category"):
            continue
        overlap = title_similarity(item.get("title"), old.get("title"))
        past_topics = words(" ".join(old.get("topics") or []))
        topic_overlap = len(topics & past_topics)
        if overlap < 0.67 or (topics and past_topics and topic_overlap < 1):
            continue
        score = overlap + min(topic_overlap, 3) * .025
        if score > best_score:
            best, best_score = old, score
    return best


def new_story_id(item):
    # Stable within a single public item, independent of a model-generated label.
    normalized = canonical_url(item.get("url")) or item.get("title") or "unknown"
    return "s-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def article_history_entry(item, date):
    return {
        "date": date,
        "title": item.get("title", ""),
        "summary": item.get("summary", ""),
        "url": item.get("url", ""),
    }


def changed_snippets(item, previous):
    """Expose a short sourced sentence if it contains new details.

    The label in the UI is 'W nowszym materiale', not 'Verified new fact'.
    """
    if not previous:
        return []
    old_words = words(previous.get("summary", ""))
    result = []
    for sentence in re.split(r"(?<=[.!?])\s+", str(item.get("summary") or "")):
        text = sentence.strip()
        current = words(text)
        if 5 <= len(current) and len(current-old_words) >= 3:
            result.append(text[:400])
        if len(result) == 2:
            break
    return result


def enrich_edition(items, history, day):
    """Cross-day story ID, timeline, safe source metadata and review warnings."""
    completed = []
    previous_by_story = {}
    for old in history:
        sid = old.get("story_id") or new_story_id(old)
        previous_by_story.setdefault(sid, []).append(old)
    for item in items:
        original = dict(item)
        source = source_summary(original)
        earlier = match_previous(original, history)
        sid = (earlier.get("story_id") or new_story_id(earlier)) if earlier else new_story_id(original)
        previous = sorted(previous_by_story.get(sid, []),
                          key=lambda x: x["archive_date"], reverse=True)
        if earlier and not previous:
            previous = [earlier]
        # One source article may carry multiple prior updates; show unique dates.
        seen_dates, timeline = set(), []
        for old in previous:
            date = old.get("archive_date")
            if not date or date in seen_dates:
                continue
            seen_dates.add(date)
            timeline.append(article_history_entry(old, date))
        timeline = list(reversed(timeline[:5]))
        fact_status = fact_warnings(original)
        completed.append({
            **original,
            **source,
            "story_id": sid,
            "is_update": bool(earlier),
            "story_timeline": timeline,
            "what_changed": changed_snippets(original, earlier),
            "fact_review": {"checked": fact_status["checked"],
                            "numeric_warning_count": len(fact_status["warnings"])},
        })
    return completed


def dedupe_previous(items, history):
    """Skip verbatim repeats only; similar titles with new details are retained."""
    seen = {canonical_url(x.get("url")) for x in history}
    for item in items:
        key = canonical_url(item.get("url"))
        if key and key in seen:
            continue
        # Don't drop a story merely because broad title/topics match.
        yield item
