#!/usr/bin/env python3
"""
cleaner.py - simple dedupe + quality filter
Reads: data/crawler_items.json
Writes: data/cleaned_items.json
"""

import json
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA = ROOT / "data"
INP = DATA / "crawler_items.json"
OUT = DATA / "cleaned_items.json"

MIN_SNIPPET = 40

def load_items():
    try:
        data = json.loads(INP.read_text(encoding="utf-8"))
        return data.get("items", [])
    except Exception:
        return []

def dedupe(items):
    seen = set()
    out = []
    for it in items:
        url = (it.get("url") or "").split("#")[0].lower()
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(it)
    return out

def quality_filter(items):
    return [i for i in items if len((i.get("snippet") or "")) >= MIN_SNIPPET]

def main():
    items = load_items()
    items = dedupe(items)
    items = quality_filter(items)
    ts = datetime.utcnow().isoformat()+"Z"
    for it in items:
        it.setdefault("cleaned_at", ts)
    OUT.write_text(json.dumps({"generated_at": ts, "items": items}, indent=2), encoding="utf-8")
    print("cleaner: wrote", OUT)

if __name__ == "__main__":
    main()
