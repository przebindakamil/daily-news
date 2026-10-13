"""Weekly editorial quality audit for the Daily News static site.

Each audited event must originate in captured daily headline references.
Never infer a percentage from missing reference snapshots.
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from generate_news import ARCHIVE_DIR, COVERAGE_DIR, LOCAL_TZ, ROOT, gemini_json

AUDIT_DIR = ROOT / "reports" / "audits"
AUDIT_INDEX = AUDIT_DIR / "index.json"
MAX_REFERENCES = 210
MAX_EVENTS = 25


def weekly_window(iso_week=None, now=None):
    """Return ISO week label and inclusive Monday/Sunday dates."""
    if iso_week:
        matched = re.fullmatch(r"(\d{4})-W(\d{2})", iso_week)
        if not matched:
            raise ValueError("Podaj tydzień jako YYYY-Www, np. 2026-W42.")
        year, week = map(int, matched.groups())
        monday = date.fromisocalendar(year, week, 1)
    else:
        today = (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ).date()
        monday = today - timedelta(days=today.weekday() + 7)
    sunday = monday + timedelta(days=6)
    if sunday >= (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ).date():
        raise ValueError("Można audytować tylko zakończone tygodnie.")
    iso = monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}", monday, sunday


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def day_strings(monday):
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]


def collect_week(monday):
    issues, coverages = [], []
    missing_issues, missing_coverages = [], []
    published = []
    references = []
    for day in day_strings(monday):
        issue = read_json(ARCHIVE_DIR / f"{day}.json")
        coverage = read_json(COVERAGE_DIR / f"{day}.json")
        if issue is None:
            missing_issues.append(day)
        else:
            issues.append(issue)
            for story in (issue.get("top_stories") or []) + (issue.get("more_stories") or []):
                published.append({
                    "title": story.get("title", ""),
                    "summary": story.get("summary", ""),
                    "category": story.get("category", ""),
                    "url": story.get("url", ""),
                    "source": story.get("source", ""),
                    "day": day,
                })
        if coverage is None:
            missing_coverages.append(day)
        else:
            coverages.append(coverage)
            headline_review = coverage.get("independent_headline_review") or {}
            for headline in headline_review.get("headlines", []):
                if headline.get("title") and headline.get("url"):
                    references.append({
                        "title": headline["title"],
                        "url": headline["url"],
                        "source": headline.get("reference") or "Niezależne nagłówki",
                        "day": day,
                    })
    # The same syndicated headline often appears on consecutive days.
    seen = set()
    unique_references = []
    for item in references:
        key = re.sub(r"\W+", " ", item["title"].casefold()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique_references.append(item)
    return {
        "issues": issues, "coverages": coverages, "published": published,
        "references": unique_references[:MAX_REFERENCES],
        "missing_issues": missing_issues, "missing_coverages": missing_coverages,
    }


def select_key_events(references):
    indexed = [
        {"id": idx, "title": item["title"], "date": item["day"], "source": item["source"]}
        for idx, item in enumerate(references)
    ]
    prompt = f"""
Jesteś niezależnym redaktorem-audytorem cotygodniowej prasówki.
Masz wyłącznie poniższe PRAWDZIWE nagłówki referencyjne, zebrane w dniach publikacji.
Wybierz 15–25 (maksymalnie {MAX_EVENTS}) najważniejszych RÓŻNYCH WYDARZEŃ tygodnia,
a nie najbardziej chwytliwych artykułów. Uwzględnij świat, Polskę, biznes, naukę,
medycynę, AI, sport i kulturę, ale nie wymuszaj sztucznego balansu.
Wysoko oceniaj przełomowe odkrycia, Nagrody Nobla, istotne decyzje polityczne
i gospodarcze. Połącz nagłówki dotyczące tego samego wydarzenia, wybierając jeden.
Zwróć wyłącznie indeksy z listy, nigdy nie wymyślaj wydarzenia.
Każda pozycja ma mieć krótkie objaśnienie jej znaczenia.
Zwróć JEDEN poprawny JSON:
{{"events":[{{"reference_index":0,"importance":5,"why_important":"...","category":"..."}}]}}
Wartość importance: 1–5 (5 = bardzo ważne).
NAGŁÓWKI:
{json.dumps(indexed, ensure_ascii=False)}
""".strip()
    answer = gemini_json(prompt)
    events, used = [], set()
    for row in answer.get("events", []):
        try:
            idx = int(row["reference_index"])
        except (ValueError, TypeError, KeyError):
            continue
        if idx < 0 or idx >= len(references) or idx in used:
            continue
        used.add(idx)
        category = str(row.get("category") or "Inne").strip()[:80]
        events.append({
            **references[idx],
            "reference_index": idx,
            "importance": min(5, max(1, int(row.get("importance", 3)))),
            "category": category,
            "why_important": str(row.get("why_important") or "").strip()[:350],
        })
        if len(events) == MAX_EVENTS:
            break
    if not events:
        raise RuntimeError("Gemini nie wybrał żadnego poprawnego wydarzenia audytowego.")
    return events


def compare_publication(events, published):
    event_input = [
        {"id": i, "title": item["title"], "day": item["day"], "source": item["source"]}
        for i, item in enumerate(events)
    ]
    publication_input = [
        {"id": i, "title": item["title"], "summary": item["summary"][:220], "day": item["day"]}
        for i, item in enumerate(published)
    ]
    prompt = f"""
Jesteś audytorem Daily News. Porównaj WYDARZENIA REFERENCYJNE z OPUBLIKOWANYMI
materiałami i dla KAŻDEGO indeksu wydarzenia zwróć ocenę:
- covered: to samo wydarzenie wyraźnie zostało opisane w publikacji;
- partial: wspomniane, ale bez głównej informacji;
- missing: brak tego konkretnego wydarzenia.
Dopasowuj semantycznie: polski i angielski tytuł mogą oznaczać to samo.
Nie uznawaj podobnego tematu za to samo wydarzenie (np. wszystkie odkrycia naukowe).
Nie dopisuj faktów ani tytułów. Pisz krótką przyczynę po polsku.
Zwróć wyłącznie JSON:
{{"matches":[{{"event_index":0,"status":"covered","published_indices":[0],"reason":"..."}}]}}
INDEKSY WYDARZEŃ:
{json.dumps(event_input, ensure_ascii=False)}
OPUBLIKOWANE MATERIAŁY:
{json.dumps(publication_input, ensure_ascii=False)}
""".strip()
    answer = gemini_json(prompt)
    matches = {}
    for row in answer.get("matches", []):
        try:
            idx = int(row["event_index"])
        except (ValueError, KeyError, TypeError):
            continue
        if idx < 0 or idx >= len(events) or idx in matches:
            continue
        status = row.get("status")
        if status not in ("covered", "partial", "missing"):
            continue
        story_indices = []
        for x in row.get("published_indices", []):
            try:
                n = int(x)
                if 0 <= n < len(published) and n not in story_indices:
                    story_indices.append(n)
            except (TypeError, ValueError):
                pass
        if status == "covered" and not story_indices:
            # A claimed match without a supporting article must be reviewed.
            status = "partial"
        if status == "missing":
            story_indices = []
        matches[idx] = {
            "status": status,
            "published_indices": story_indices[:4],
            "reason": str(row.get("reason") or "").strip()[:350],
        }
    if len(matches) != len(events):
        raise RuntimeError(f"Porównano tylko {len(matches)}/{len(events)} wydarzeń; audyt przerwany.")
    return matches


def diagnose_omission(event, coverages):
    """Exact URL and conservative title tokens only; do not invent a root cause."""
    normalized = re.sub(r"\W+", " ", event["title"].casefold()).strip()
    candidates, ranked = [], []
    for daily in coverages:
        candidates.extend(daily.get("candidate_pool") or [])
        ranked.extend(daily.get("ranked_pool") or [])

    def matching(row):
        if event["url"] and row.get("url") == event["url"]:
            return True
        title = re.sub(r"\W+", " ", str(row.get("title", "")).casefold()).strip()
        return len(normalized) >= 24 and title == normalized

    if any(matching(row) for row in ranked):
        return "ranked_not_published"
    if any(matching(row) for row in candidates):
        return "discovered_not_ranked"
    return "not_confirmed_in_candidate_pool"


def repeated_articles(published):
    by_key = defaultdict(list)
    for item in published:
        key = item.get("url") or re.sub(r"\W+", " ", item.get("title", "").casefold()).strip()
        if key:
            by_key[key].append(item)
    return [
        {"title": rows[0]["title"], "days": sorted({r["day"] for r in rows})}
        for rows in by_key.values()
        if len({r["day"] for r in rows}) > 1
    ][:30]


def build_report(week, monday, sunday, data, events=None, matches=None):
    missing_issues = data["missing_issues"]
    missing_coverages = data["missing_coverages"]
    references = data["references"]
    publications = data["published"]
    complete = (
        not missing_issues and not missing_coverages
        and len(references) >= 10 and events is not None and matches is not None
    )
    audited_events = []
    category_results = defaultdict(lambda: {"audited": 0, "covered": 0, "partial": 0, "missing": 0})
    if complete:
        for idx, event in enumerate(events):
            match = matches[idx]
            status = match["status"]
            category = event["category"]
            category_results[category]["audited"] += 1
            category_results[category][status] += 1
            audited_events.append({
                **event,
                "status": status,
                "reason": match["reason"],
                "pipeline": (
                    "published" if status == "covered"
                    else diagnose_omission(event, data["coverages"])
                ),
                "matched_stories": [
                    {k: publications[p][k] for k in ("title", "day", "url")}
                    for p in match["published_indices"]
                ],
            })
    covered = sum(e["status"] == "covered" for e in audited_events)
    partial = sum(e["status"] == "partial" for e in audited_events)
    missing = sum(e["status"] == "missing" for e in audited_events)
    total = len(audited_events)
    reports_count = len(data["coverages"])
    feed_failures = sum(
        len(item.get("empty_feeds") or [])
        for item in data["coverages"]
    )
    report = {
        "schema_version": 1,
        "week": week,
        "start_date": monday.isoformat(),
        "end_date": sunday.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if complete else "incomplete",
        "methodology": (
            "Wynik próbkowy: istotne wydarzenia wybrane przez AI spośród zapisanych "
            "niezależnych nagłówków dnia, a następnie dopasowane semantycznie do wydań. "
            "Nie jest to pomiar wszystkich wydarzeń na świecie ani pełny fact-check."
        ),
        "metrics": {
            "coverage_percent": round((covered + 0.5 * partial) * 100 / total, 1) if complete and total else None,
            "audited_events": total,
            "covered": covered,
            "partial": partial,
            "missing": missing,
            "published": len(publications),
            "issues_available": len(data["issues"]),
            "coverage_reports_available": reports_count,
            "reference_headlines": len(references),
            "feed_failures": feed_failures,
            "repeated_stories": len(repeated_articles(publications)),
        },
        "missing_issue_days": missing_issues,
        "missing_coverage_days": missing_coverages,
        "incomplete_reason": (
            "Brak kompletu siedmiu wydań, dziennych raportów źródeł lub wystarczającej "
            "próby niezależnych nagłówków; nie obliczamy sztucznego wyniku."
            if not complete else None
        ),
        "category_results": dict(category_results),
        "events": audited_events,
        "repeats": repeated_articles(publications),
        "daily": [
            {
                "day": day,
                "published": sum(p["day"] == day for p in publications),
                "reference_headlines": sum(r["day"] == day for r in references),
            }
            for day in day_strings(monday)
        ],
    }
    return report


def save_report(report):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    week = report["week"]
    (AUDIT_DIR / f"{week}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    existing = read_json(AUDIT_INDEX) or {"weeks": []}
    summaries = {
        item["week"]: item for item in existing.get("weeks", [])
        if item.get("week") and item["week"] != week
    }
    summaries[week] = {
        "week": week,
        "start_date": report["start_date"],
        "end_date": report["end_date"],
        "status": report["status"],
        "coverage_percent": report["metrics"]["coverage_percent"],
        "audited_events": report["metrics"]["audited_events"],
        "missing": report["metrics"]["missing"],
        "published": report["metrics"]["published"],
    }
    ordered = [summaries[key] for key in sorted(summaries, reverse=True)]
    AUDIT_INDEX.write_text(
        json.dumps({"latest": ordered[0]["week"], "weeks": ordered}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as out:
            out.write(f"## Audyt tygodniowy {week}\n\n")
            out.write(f"Status: **{report['status']}**. Pokrycie próby: **"
                      f"{report['metrics']['coverage_percent'] if report['status']=='complete' else 'brak danych'}**.\n\n")
            out.write(f"Publikacji: {report['metrics']['published']}; "
                      f"wydarzeń w próbie: {report['metrics']['audited_events']}; "
                      f"pominiętych: {report['metrics']['missing']}.\n\n")
            if report["status"] != "complete":
                out.write(f"**Ograniczenie:** {report['incomplete_reason']}\n\n")
            out.write(f"Raport: \`reports/audits/{week}.json\`\n")


def run(week=None, now=None):
    label, monday, sunday = weekly_window(week, now)
    week_data = collect_week(monday)
    sufficiently_grounded = (
        not week_data["missing_issues"]
        and not week_data["missing_coverages"]
        and len(week_data["references"]) >= 10
    )
    events = matches = None
    if sufficiently_grounded:
        events = select_key_events(week_data["references"])
        matches = compare_publication(events, week_data["published"])
    report = build_report(label, monday, sunday, week_data, events, matches)
    save_report(report)
    print(f"Audyt {label}: {report['status']}; "
          f"pokrycie {report['metrics']['coverage_percent']}; "
          f"opublikowanych {report['metrics']['published']}.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audyt redakcyjny Daily News")
    parser.add_argument("--week", default=None, help="Zakończony tydzień ISO, np. 2026-W42")
    args = parser.parse_args()
    run(args.week)
