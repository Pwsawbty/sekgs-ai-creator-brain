#!/usr/bin/env python3
"""
crawler.py - minimal reliable crawler for GitHub Actions.
Writes: data/crawler_items.json
"""

import json
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except Exception:
    requests = None  # allow running without network in limited environments

ROOT = Path.cwd()
DATA = ROOT / "data"
OUT = DATA / "crawler_items.json"
DATA.mkdir(parents=True, exist_ok=True)

DEFAULT_SEEDS = [
    "https://openai.com/blog",
    "https://github.com/trending",
    "https://arxiv.org/list/cs.AI/recent",
    "https://towardsdatascience.com/"
]

def fetch_url(u):
    if not requests:
        return {"url": u, "title": u, "snippet": "requests not installed in runtime", "fetched_at": datetime.utcnow().isoformat()+"Z"}
    try:
        r = requests.get(u, timeout=12, headers={"User-Agent":"sekgs-crawler/1.0"})
        if r.status_code != 200:
            return {"url": u, "title": u, "snippet": f"status:{r.status_code}", "fetched_at": datetime.utcnow().isoformat()+"Z"}
        text = r.text[:1000].replace("\n"," ")
        title = ""
        lower = text.lower()
        if "<title>" in lower:
            try:
                s = lower.index("<title>")
                e = lower.index("</title>", s)
                title = text[s+7:e].strip()
            except Exception:
                title = u
        return {"url": u, "title": title or u, "snippet": text[:400], "fetched_at": datetime.utcnow().isoformat()+"Z"}
    except Exception as e:
        return {"url": u, "title": u, "snippet": f"err:{str(e)[:200]}", "fetched_at": datetime.utcnow().isoformat()+"Z"}

def main():
    seeds = DEFAULT_SEEDS
    items = []
    for s in seeds:
        items.append(fetch_url(s))
        time.sleep(0.5)
    payload = {"generated_at": datetime.utcnow().isoformat()+"Z", "items": items}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("crawler: wrote", OUT)

if __name__ == "__main__":
    main()
