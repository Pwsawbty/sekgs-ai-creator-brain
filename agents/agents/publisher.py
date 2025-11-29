#!/usr/bin/env python3
"""
publisher.py - create daily report and optional Notion upsert
Reads: data/graph.json and data/nodes/*.json
Writes: reports/daily-YYYY-MM-DD.md
"""

import os, json
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
GRAPH_FILE = DATA_DIR / "graph.json"
REPORTS = ROOT / "reports"

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB = os.environ.get("NOTION_DATABASE_ID")

def load_graph():
    if not GRAPH_FILE.exists():
        return {"meta":{}, "nodes":[], "edges":[]}
    return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))

def read_node(nid):
    p = DATA_DIR / "nodes" / f"{nid}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def write_report(graph):
    REPORTS.mkdir(parents=True, exist_ok=True)
    d = datetime.utcnow().strftime("%Y-%m-%d")
    path = REPORTS / f"daily-{d}.md"
    nodes = graph.get("nodes", [])
    top = []
    for nid in nodes[:5]:
        node = read_node(nid)
        if node:
            top.append((nid, node.get("title",""), node.get("relevance_score",0), node.get("trust_score",0), node.get("summary","")[:120]))
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# SEKGS-A Daily Insights — {d} (UTC)\n\n")
        f.write("Top 5 new/updated nodes:\n")
        for i, t in enumerate(top, 1):
            f.write(f"{i}. {t[0]} — {t[1]} — relevance:{t[2]} trust:{t[3]} — summary: {t[4]}\n")
        f.write("\nTop 3 trending relations:\n")
        for e in graph.get("edges", [])[:3]:
            f.write(f"- {e.get('source')} -> {e.get('target')} (weight:{e.get('weight')})\n")
        f.write("\nQuick Actions:\n- [ ] Flag nodes for manual review:\n- [ ] Promote to report:\n")
    print("Report written:", str(path))
    return str(path)

def notion_upsert(graph):
    if not NOTION_TOKEN or not NOTION_DB:
        print("Notion credentials not set - skipping Notion sync.")
        return
    try:
        import requests
        headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
        for nid in graph.get("nodes", [])[:5]:
            node = read_node(nid)
            if not node:
                continue
            body = {
                "parent": {"database_id": NOTION_DB},
                "properties": {
                    "ID": {"title":[{"text":{"content": node.get("id")}}]},
                    "Title": {"rich_text":[{"text":{"content": node.get("title")}}]},
                    "Type": {"select":{"name": node.get("type","concept")}},
                    "Summary": {"rich_text":[{"text":{"content": node.get("summary","")}}]}
                }
            }
            r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=body, timeout=15)
            if r.status_code not in (200,201):
                print("Notion upsert failed:", r.status_code, r.text[:200])
            else:
                print("Notion upsert ok:", nid)
    except Exception as e:
        print("Notion sync error:", str(e))

def main():
    graph = load_graph()
    report = write_report(graph)
    notion_upsert(graph)
    print("Publisher done.")

if __name__ == "__main__":
    main()
