#!/usr/bin/env python3
"""
publisher.py - writes daily report + optional Notion sync
"""

import os,json
from pathlib import Path
from datetime import datetime

ROOT=Path.cwd()
DATA_DIR=ROOT/"data"
NODES_DIR=DATA_DIR/"nodes"
GRAPH_FILE=DATA_DIR/"graph.json"
REPORTS=ROOT/"reports"

NOTION_TOKEN=os.environ.get("NOTION_TOKEN")
NOTION_DB=os.environ.get("NOTION_DATABASE_ID")

def load_graph():
    if not GRAPH_FILE.exists():
        return {"meta":{},"nodes":[],"edges":[]}
    return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))

def read_node(nid):
    p=NODES_DIR/f"{nid}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def write_report(graph):
    REPORTS.mkdir(parents=True,exist_ok=True)
    d=datetime.utcnow().strftime("%Y-%m-%d")
    path=REPORTS/f"daily-{d}.md"
    nodes=graph.get("nodes",[])
    top=[]
    for nid in nodes[:5]:
        n=read_node(nid)
        if n:
            top.append((nid,n.get("title",""),n.get("relevance_score",0),n.get("trust_score",0),n.get("summary","")[:120]))
    with open(path,"w",encoding="utf-8") as f:
        f.write(f"# SEKGS-A Daily Insights — {d}\n\n")
        f.write("Top 5 nodes:\n")
        for i,t in enumerate(top,1):
            f.write(f"{i}. {t[0]} — {t[1]} — relevance:{t[2]} trust:{t[3]} — {t[4]}\n")
        f.write("\nRelations:\n")
        for e in graph.get("edges",[])[:3]:
            f.write(f"- {e['source']} -> {e['target']} (w:{e['weight']})\n")
    print("Report written:", path)
    return path

def main():
    graph=load_graph()
    write_report(graph)
    print("Publisher done.")

if __name__=="__main__":
    main()
