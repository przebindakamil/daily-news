"""Public, source-linked weekly rewind built from published daily editions.

No Gemini calls. Uses the last complete Polish Monday-Sunday week by default.
Never reads or publishes encrypted/private editorial audit material.
"""
import argparse
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive"
OUTPUT = ROOT / "data" / "rewind"


def previous_week(today=None):
    now = today or datetime.now(ZoneInfo("Europe/Warsaw")).date()
    monday = now - timedelta(days=now.weekday() + 7)
    return monday


def load_week(monday, archive=ARCHIVE):
    dates = [(monday + timedelta(days=i)).isoformat() for i in range(7)]
    days = []
    missing = []
    for day in dates:
        path = Path(archive) / (day + ".json")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            missing.append(day)
            continue
        if data.get("date") != day:
            missing.append(day)
            continue
        days.append(data)
    return days, missing


def item_key(item):
    return item.get("story_id") or item.get("canonical_url") or item.get("url")


def build_weekly(monday, archive=ARCHIVE):
    days, missing = load_week(monday, archive)
    if not days:
        raise ValueError("Brak wydań w wybranym tygodniu.")
    candidates = []
    category_counts = Counter()
    story_counts = Counter()
    for data in days:
        day = data["date"]
        items = data.get("top_stories", []) + data.get("more_stories", [])
        for item in items:
            category_counts[item.get("category") or "Inne"] += 1
            story_counts[item_key(item)] += 1
            candidates.append({**item, "date": day})
    by_story = {}
    for item in candidates:
        key = item_key(item)
        if not key:
            continue
        current = by_story.get(key)
        if not current:
            by_story[key] = item
        else:
            better = (float(item.get("editorial_score") or 0),
                      item.get("date", "")) > (
                          float(current.get("editorial_score") or 0),
                          current.get("date", ""))
            if better:
                by_story[key] = item
    selected = sorted(
        by_story.values(),
        key=lambda x: (-float(x.get("editorial_score") or 0), x["date"]),
    )
    # Broad coverage: no category more than 3 times while alternatives exist.
    chosen, counts = [], Counter()
    for item in selected:
        if counts[item.get("category")] >= 3:
            continue
        chosen.append(item)
        counts[item.get("category")] += 1
        if len(chosen) == 10:
            break
    for item in selected:
        if len(chosen) == 10:
            break
        if item not in chosen:
            chosen.append(item)
    stories = [
        {field: item.get(field, "") for field in
         ("date", "title", "summary", "category", "url", "story_id")}
        for item in chosen
    ]
    trends = [
        {"category": category, "count": count}
        for category, count in category_counts.most_common(3)
    ]
    watch_next = [
        {"title": item.get("title", ""), "story_id": item_key(item)}
        for item in sorted(candidates, key=lambda i: i["date"], reverse=True)
        if story_counts[item_key(item)] > 1
    ]
    seen, distinct = set(), []
    for item in watch_next:
        if item["story_id"] in seen:
            continue
        seen.add(item["story_id"])
        distinct.append(item)
        if len(distinct) == 3:
            break
    return {
        "week": f"{monday.isocalendar().year}-W{monday.isocalendar().week:02d}",
        "start": monday.isoformat(),
        "end": (monday + timedelta(days=6)).isoformat(),
        "complete": not missing,
        "missing_days": missing,
        "stories": stories,
        "trends": trends,
        "watch_next": distinct,
        "source": "public_archive",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", default="", help="ISO week YYYY-Www; default last complete week")
    args = parser.parse_args()
    if args.week:
        import re
        if not re.fullmatch(r"\d{4}-W\d{2}", args.week):
            raise ValueError("Wymagany format YYYY-Www")
        year, week = args.week.split("-W")
        monday = date.fromisocalendar(int(year), int(week), 1)
        if monday + timedelta(days=7) > datetime.now(ZoneInfo("Europe/Warsaw")).date():
            raise ValueError("Tygodniowy przegląd powstaje dopiero po zakończeniu tygodnia.")
    else:
        monday = previous_week()
    result = build_weekly(monday)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / (result["week"] + ".json")
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    path.write_text(serialized, encoding="utf-8")
    (OUTPUT / "latest.json").write_text(serialized, encoding="utf-8")
    print(f"Zapisano publiczne podsumowanie: {result['week']}, "
          f"artykułów: {len(result['stories'])}, brakujących dni: "
          f"{len(result['missing_days'])}.")


if __name__ == "__main__":
    main()
