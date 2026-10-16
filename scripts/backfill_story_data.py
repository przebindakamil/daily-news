"""One-time public-archive story metadata migration; zero API calls.

Only adds metadata to public news JSON. Never opens private editorial reports.
Safe and idempotent for the current seven-day archive.
"""
import json
from pathlib import Path
from story_intelligence import enrich_edition

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data"/"archive"
CURRENT=ROOT/"data"/"current.json"
NEWS=ROOT/"data"/"news.json"


def enrich_archive(archive=ARCHIVE, current=CURRENT, news=NEWS):
    index=json.loads((archive/"index.json").read_text(encoding="utf-8"))
    history=[]
    modified=0
    latest=index.get("latest")
    for day in sorted(index.get("dates", [])):
        path=archive/f"{day}.json"
        if not path.is_file():
            continue
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("date")!=day:
            raise ValueError(f"Archive mismatch at {day}")
        original=data.get("top_stories",[])+data.get("more_stories",[])
        # Reuse established ID and timestamps where already present.
        updated=enrich_edition(original, history, day)
        top_len=len(data.get("top_stories",[]))
        data["top_stories"]=updated[:top_len]
        data["more_stories"]=updated[top_len:]
        lookup={x.get("url"):x for x in updated}
        data["top_of_day"]=[
            lookup.get(item.get("url"),item) for item in data.get("top_of_day",[])
        ]
        serialized=json.dumps(data,ensure_ascii=False,indent=2)
        if path.read_text(encoding="utf-8").strip()!=serialized:
            path.write_text(serialized,encoding="utf-8")
            modified+=1
        if day==latest:
            current.write_text(serialized,encoding="utf-8")
            news.write_text(serialized,encoding="utf-8")
        history.extend({**item,"archive_date":day} for item in updated)
    return modified


if __name__=="__main__":
    print(f"Zmigrowano {enrich_archive()} publicznych wydań bez kosztów API.")
