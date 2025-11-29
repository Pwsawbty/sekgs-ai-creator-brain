#!/usr/bin/env python3
"""
relationer.py - build simple edges by token overlap and keywords
Reads: data/nodes/*.json
Writes: data/graph.json (edges updated)
"""

import json
from pathlib import Path
from glob import glob

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
NODES_DIR = DATA_DIR / "nodes"
GRAPH_FILE = DATA_DIR / "graph.json"

def load_nodes():
    out = {}
    for p in glob(str(NODES_DIR / "*.json")):
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
            out[j["id"]] = j
    return out

def build_edges(nodes):
    edges = []
    ids = list(nodes.keys())
    for i in range(len(ids)):
        a = ids[i]
        ta = (nodes[a].get("title","") + " " + " ".join(nodes[a].get("keywords",[]))).lower().split()
        for j in range(i+1, len(ids)):
            b = ids[j]
            tb = (nodes[b].get("title","") + " " + " ".join(nodes[b].get("keywords",[]))).lower().split()
            common = set(ta) & set(tb)
            if len(common) >= 3:
                weight = min(1.0, 0.25 + 0.05 * len(common))
                edges.append({"source": a, "target": b, "type": "related_to", "weight": round(weight, 3)})
    return edges

def load_graph():
    if not GRAPH_FILE.exists():
        return {"meta":{}, "nodes":[], "edges":[]}
    return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))

def save_graph(g):
    GRAPH_FILE.write_text(json.dumps(g, indent=2), encoding="utf-8")

def main():
    nodes = load_nodes()
    if not nodes:
        print("No nodes found, skipping relationer.")
        return
    graph = load_graph()
    edges = build_edges(nodes)
    seen = set()
    merged = []
    for e in edges:
        key = (e["source"], e["target"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(e)
    graph["nodes"] = list(nodes.keys())
    graph["edges"] = merged
    graph.setdefault("meta", {})["relations_generated_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    save_graph(graph)
    print("Relationer done. edges:", len(merged))

if __name__ == "__main__":
    main()
