#!/usr/bin/env python3
"""
crawler.py - lightweight, robust crawler for mobile/GitHub Actions.
Writes: data/crawler_items.json
"""

import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
OUT_FILE = DATA_DIR / "crawler_items.json"
SEEDS_FILE = ROOT / "agents" / "seeds.txt"

DEFAULT_SEEDS = [
    "https://openai.com/blog",
    "https://github.com/trending",
    "https://arxiv.org/list/cs.AI/recent",
    "https://towardsdatascience.com/",
    "https://thenextweb.com/search?query=ai"
]

HEADERS = {"User-Agent": "sekgs-crawler/1.0 (+https://github.com)"}
TIMEOUT = 12

def load_seeds():
    if SEEDS_FILE.exists():
        seeds = [s.strip() for s in SEEDS_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]
        if seeds:
            return seeds
    return DEFAULT_SEEDS

def fetch(u):
    try:
        r = requests.get(u, headers=HEADERS, timeout=TIMEOUT)
        if r.statuscode != 200:
            return None
        text = r.text
        title = ""
        lower = text.lower()
        if "<title>" in lower:
            try:
                s = lower.index("<title>")
                e = lower.index("</title>", s)
                title = text[s+7:e].strip()
            except:
                title = ""
        snippet = text.strip()[:1500].replace("\n", " ")
        return {"url": u, "title": title or u, "snippet": snippet[:1000], "fetched_at": datetime.utcnow().isoformat()+"Z"}
    except Exception as e:
        print("crawl error:", u, str(e))
        return None

def main():
    seeds = load_seeds()
    items = []
    for s in seeds:
        print("Crawling:", s)
        res = fetch(s)
        if res:
            items.append(res)
        time.sleep(1.2)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({"generated_at": datetime.utcnow().isoformat()+"Z", "items": items}, indent=2), encoding="utf-8")
    print("Crawl finished:", len(items))

if __name__ == "__main__":
    main()
