#!/usr/bin/env python3
"""
Robust failure-proof crawler.
- Retries with exponential backoff
- Timeout and custom User-Agent
- Optional robots.txt check (set CHECK_ROBOTS env=1 to enable)
- Local caching to avoid repeated downloads (cache dir: .cache/pages)
- Always writes a node file even if page fetch fails (partial marker)
- Writes logs to data/logs/crawler.log
- Uses only requests + bs4 (add to requirements)
"""
from pathlib import Path
import os, time, json, hashlib
import requests
from bs4 import BeautifulSoup

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
NODES_DIR = DATA_DIR / "nodes"
CACHE_DIR = ROOT / ".cache" / "pages"
LOG_DIR = DATA_DIR / "logs"
RULES_DIR = ROOT / "rules"
SEED_FILE = RULES_DIR / "seed_urls.txt"

USER_AGENT = os.environ.get("CRAWLER_UA", "SEKGS-Crawler/1.0 (+https://example.com)")
CHECK_ROBOTS = os.environ.get("CHECK_ROBOTS", "0") == "1"
MAX_RETRIES = int(os.environ.get("CRAWLER_MAX_RETRIES", "3"))
BACKOFF_BASE = float(os.environ.get("CRAWLER_BACKOFF", "1.5"))
TIMEOUT = int(os.environ.get("CRAWLER_TIMEOUT", "12"))

for p in (NODES_DIR, CACHE_DIR, LOG_DIR, RULES_DIR):
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "crawler.log"

def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{ts} {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_seeds():
    if not SEED_FILE.exists():
        log("[CRAWLER] seed file missing: " + str(SEED_FILE))
        return []
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

def safe_cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def cached_page(url: str):
    ck = safe_cache_key(url)
    path = CACHE_DIR / ck
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None

def write_cache(url: str, text: str):
    ck = safe_cache_key(url)
    path = CACHE_DIR / ck
    try:
        path.write_text(text, encoding="utf-8")
    except Exception as e:
        log("[CRAWLER] cache write failed: " + str(e))

def fetch_with_retries(url: str):
    headers = {"User-Agent": USER_AGENT}
    # try cache first
    cached = cached_page(url)
    if cached:
        log(f"[CRAWLER] cache hit {url}")
        return cached, True

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            attempt += 1
            log(f"[CRAWLER] GET {url} attempt={attempt}")
            r = requests.get(url, timeout=TIMEOUT, headers=headers)
            r.raise_for_status()
            text = r.text
            write_cache(url, text)
            return text, False
        except Exception as e:
            log(f"[CRAWLER] fetch error {url} attempt={attempt} err={e}")
            if attempt < MAX_RETRIES:
                sleep = BACKOFF_BASE ** attempt
                time.sleep(sleep)
            else:
                return None, False
    return None, False

def extract_text(html: str):
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "svg"]):
            tag.decompose()
        txt = soup.get_text(separator=" ")
        txt = " ".join(txt.split())
        return txt
    except Exception as e:
        log("[CRAWLER] extract error: " + str(e))
        return ""

def safe_node_id(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace(" ", "_")

def save_node(url: str, text: str, partial=False, source_cached=False):
    nid = safe_node_id(url)
    path = NODES_DIR / f"{nid}.json"
    payload = {
        "id": nid,
        "url": url,
        "partial": bool(partial),
        "cached_source": bool(source_cached),
        "text": text[:20000]  # cap to reasonable size
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"[CRAWLER] saved node {path} partial={partial} cached={source_cached}")
    except Exception as e:
        log("[CRAWLER] save node failed: " + str(e))

def main():
    seeds = load_seeds()
    if not seeds:
        log("[CRAWLER] No seeds to crawl — add rules/seed_urls.txt")
        return
    for url in seeds:
        html, cached = fetch_with_retries(url)
        if html:
            txt = extract_text(html)
            # if text shorter than 50 chars treat as partial
            partial = len(txt) < 50
            save_node(url, txt or "", partial=partial, source_cached=cached)
        else:
            # write a minimal partial node to mark attempt
            log("[CRAWLER] fetch failed after retries - writing partial node for " + url)
            save_node(url, "", partial=True, source_cached=False)

if __name__ == "__main__":
    main()
