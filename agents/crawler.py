#!/usr/bin/env python3
from pathlib import Path
import os, time, json, hashlib, sys
try:
    import requests
except Exception as e:
    print("[CRAWLER] Missing dependency requests:", e)
    raise

try:
    from bs4 import BeautifulSoup
except Exception as e:
    print("[CRAWLER] Missing dependency bs4. Install with: pip install beautifulsoup4")
    raise

ROOT = Path.cwd()
DATA = ROOT / "data"
NODES = DATA / "nodes"
LOGS = DATA / "logs"
RULES = ROOT / "rules"
SEED_FILE = RULES / "seed_urls.txt"
CACHE = ROOT / ".cache/pages"

for p in (DATA, NODES, LOGS, RULES, CACHE):
    p.mkdir(parents=True, exist_ok=True)

LOG = LOGS / "crawler.log"
USER_AGENT = os.environ.get("CRAWLER_UA","SEKGS-Crawler/1.0")

def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{ts} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def safe_id(url):
    return url.replace("https://","").replace("http://","").replace("/","_").replace(" ","_")

def save_node(url, text, partial=False):
    nid = safe_id(url)
    path = NODES / f"{nid}.json"
    payload = {"id": nid, "url": url, "partial": bool(partial), "text": text[:20000]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[CRAWLER] saved node {path.name} partial={partial}")

def load_seeds():
    if not SEED_FILE.exists():
        log("[CRAWLER] seed file missing: " + str(SEED_FILE))
        return []
    return [l.strip() for l in SEED_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]

def extract_text(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script","style","noscript","header","footer","svg"]):
            tag.decompose()
        txt = soup.get_text(" ")
        txt = " ".join(txt.split())
        return txt
    except Exception as e:
        log("[CRAWLER] extract error: " + str(e))
        return ""

def fetch(url, retries=3, timeout=12):
    headers = {"User-Agent": USER_AGENT}
    attempt = 0
    while attempt < retries:
        attempt += 1
        try:
            log(f"[CRAWLER] GET {url} attempt={attempt}")
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            return r.text
        except Exception as e:
            log(f"[CRAWLER] fetch error: {e}")
            time.sleep(1.5 ** attempt)
    return None

def main():
    seeds = load_seeds()
    if not seeds:
        log("[CRAWLER] No seeds found.")
        return
    for url in seeds:
        html = fetch(url)
        if html:
            txt = extract_text(html)
            partial = len(txt) < 50
            save_node(url, txt or "", partial=partial)
        else:
            save_node(url, "", partial=True)
            log("[CRAWLER] All retries failed for " + url)

if __name__ == "__main__":
    main()
