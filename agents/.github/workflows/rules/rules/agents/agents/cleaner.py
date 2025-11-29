#!/usr/bin/env python3
"""
cleaner.py - dedupe + quality filter
Reads: data/crawler_items.json
Writes: data/cleaned_items.json
"""

import json, re
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
IN_FILE = DATA_DIR / "crawler_items.json"
OUT_FILE = DATA_DIR / "cleaned_items.json"

MIN_SNIPPET = 80
TRUST_DOMAINS_HIGH = ["openai.com","arxiv.org","github.com","medium.com","towardsdatascience.com"]

def load_items():
    if not IN_FILE.exists():
        return []
    j = json.loads(IN_FILE.read_text(encoding="utf-8"))
    return j.get("items", [])

def dedupe(items):
    seen = set()
    out = []
    for it in items:
        url = it.get("url","")
        if not url:
            continue
        key = url.split("#")[0].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def quality_filter(items):
    out = []
    for it in items:
        snippet = (it.get("snippet") or "").strip()
        if len(snippet) < MIN_SNIPPET:
            continue
        out.append(it)
    return out

def trust_score(url):
    if not url:
        return 30
    for d in TRUST_DOMAINS_HIGH:
        if d in url:
            return 80
    return 40

def main():
    items = quality_filter(dedupe(load_items()))
    now = datetime.utcnow().isoformat()+"Z"
    for it in items:
        it["trust_score"] = trust_score(it.get("url"))
        it["cleaned_at"] = now
    OUT_FILE.write_text(json.dumps({"generated_at": now, "items": items}, indent=2), encoding="utf-8")
    print("Cleaner done:", len(items))

if __name__ == "__main__":
    main()
