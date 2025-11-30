#!/usr/bin/env python3
"""
mapper.py - create node files and update data/graph.json
Reads: data/cleaned_items.json
Writes: data/nodes/<slug>.json and updates data/graph.json
"""

import json, re
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA = ROOT / "data"
NODES = DATA / "data_nodes_temp"  # temporary if nodes dir missing; will write to data/nodes below
CLEANED = DATA / "cleaned_items.json"
GRAPH = DATA / "graph.json"

NODES_DIR = DATA / "nodes"
NODES_DIR.mkdir(parents=True, exist_ok=True)

def slugify(text):
    s = (text or "").lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:80] or "node-" + datetime.utcnow().strftime("%s")

def load_cleaned():
    try:
        j = json.loads(CLEANED.read_text(encoding="utf-8"))
        return j.get("items", [])
    except Exception:
        return []

def load_graph():
    try:
        return json.loads(GRAPH.read_text(encoding="utf-8"))
    except Exception:
        return {"meta": {"domain":"ai-tools-creator-workflows","version":"0.1"}, "nodes": [], "edges": []}

def save_graph(g):
    GRAPH.write_text(json.dumps(g, indent=2), encoding="utf-8")

def write_node(node):
    path = NODES_DIR / f"{node['id']}.json"
    path.write_text(json.dumps(node, indent=2), encoding="utf-8")

def main():
    items = load_cleaned()
    graph = load_graph()
    created = 0
    for i, it in enumerate(items):
        title = it.get("title") or it.get("url") or f"untitled-{i}"
        slug = slugify(title)
        now = datetime.utcnow().isoformat()+"Z"
        node = {
            "id": slug,
            "title": title[:200],
            "summary": (it.get("snippet") or "")[:1000],
            "sources": [{"url": it.get("url",""), "fetched_at": it.get("fetched_at", now)}],
            "created_at": now,
            "trust_score": it.get("trust_score", 50)
        }
        write_node(node)
        if slug not in graph.get("nodes", []):
            graph.setdefault("nodes", []).append(slug)
        created += 1
    graph.setdefault("meta", {})["generated_at"] = datetime.utcnow().isoformat()+"Z"
    save_graph(graph)
    print("mapper: created", created, "nodes and updated", GRAPH)

if __name__ == "__main__":
    main()
