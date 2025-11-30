#!/usr/bin/env python3
"""
relationer.py - generate basic edges by sequence
Reads: data/graph.json and data/nodes/*.json
Writes: data/graph.json (edges updated)
"""

import json
from pathlib import Path
from glob import glob

ROOT = Path.cwd()
DATA = ROOT / "data"
GRAPH = DATA / "graph.json"
NODES_DIR = DATA / "nodes"

def load_graph():
    try:
        return json.loads(GRAPH.read_text(encoding="utf-8"))
    except Exception:
        return {"nodes": [], "edges": []}

def main():
    graph = load_graph()
    node_files = sorted(glob(str(NODES_DIR / "*.json")))
    edges = []
    for i in range(len(node_files)-1):
        a = Path(node_files[i]).stem
        b = Path(node_files[i+1]).stem
        edges.append({"source": a, "target": b, "type": "related_to", "weight": 0.5})
    graph["edges"] = edges
    graph.setdefault("meta", {})["relations_generated_at"] = _from datetime import datetime

graph.setdefault("meta", {})
graph["meta"]["relations_generated_at"] = datetime.utcnow().isoformat() + "Z"
    GRAPH.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print("relationer: wrote", len(edges), "edges")

if __name__ == "__main__":
    main()
