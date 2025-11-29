#!/usr/bin/env python3
"""
mapper.py - create/update node JSON files and update master graph.json
Inputs: data/cleaned_items.json
Writes: data/nodes/<slug>.json and updates data/graph.json
"""

import json, re
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
NODES_DIR = DATA_DIR / "nodes"
CLEANED = DATA_DIR / "cleaned_items.json"
GRAPH_FILE = DATA_DIR / "graph.json"

def slugify(text):
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s[:80] or "node-" + datetime.utcnow().strftime("%s")

def load_graph():
    if not GRAPH_FILE.exists():
        return {"meta":{"domain":"ai-tools-creator-workflows","version":"0.1"}, "nodes":[], "edges":[]}
    return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))

def save_graph(g):
    GRAPH_FILE.write_text(json.dumps(g, indent=2), encoding="utf-8")

def load_cleaned():
    if not CLEANED.exists():
        return []
    return json.loads(CLEANED.read_text(encoding="utf-8")).get("items", [])

def write_node(node):
    NODES_DIR.mkdir(parents=True, exist_ok=True)
    path = NODES_DIR / f"{node['id']}.json"
    path.write_text(json.dumps(node, indent=2), encoding="utf-8")

def main():
    items = load_cleaned()
    graph = load_graph()
    created = 0
    for it in items:
        title = it.get("title") or it.get("url", "") or "untitled"
        slug = slugify(title)
        now = datetime.utcnow().isoformat() + "Z"
        node_path = NODES_DIR / f"{slug}.json"
        if node_path.exists():
            node = json.loads(node_path.read_text(encoding="utf-8"))
            node["last_updated"] = now
            node["trust_score"] = max(node.get("trust_score", 0), it.get("trust_score", 30))
            write_node(node)
        else:
            ntype = "tool" if ("tool" in title.lower() or "github" in it.get("url","")) else "concept"
            node = {
                "id": slug,
                "title": title[:80],
                "domain": "ai-tools-creator-workflows",
                "type": ntype,
                "summary": (it.get("snippet") or "")[:280],
                "full_text": (it.get("snippet") or "")[:2000],
                "keywords": [],
                "sources": [{"title": title[:60], "url": it.get("url",""), "date": now.split("T")[0]}],
                "relations": [],
                "popularity_score": 5.0,
                "relevance_score": 10.0,
                "last_updated": now,
                "trust_score": it.get("trust_score", 30),
                "examples": [],
                "metadata": {"lang":"en","created_by":"crawler"}
            }
            write_node(node)
            if slug not in graph.get("nodes", []):
                graph.setdefault("nodes", []).append(slug)
            created += 1
    graph.setdefault("meta", {})["generated_at"] = datetime.utcnow().isoformat() + "Z"
    save_graph(graph)
    print("Mapper done. created:", created)
    
if __name__ == "__main__":
    main()
