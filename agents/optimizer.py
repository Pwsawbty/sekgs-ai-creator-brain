#!/usr/bin/env python3
"""
optimizer.py - apply decay and remove exact duplicate title nodes
Updates node files and data/graph.json
"""

import os, json
from glob import glob
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
NODES_DIR = DATA_DIR / "nodes"
GRAPH_FILE = DATA_DIR / "graph.json"

STALE_DAYS = 180
DECAY_PERCENT = 20

def load_graph():
    if not GRAPH_FILE.exists():
        return {"meta":{}, "nodes":[], "edges":[]}
    return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))

def save_graph(g):
    GRAPH_FILE.write_text(json.dumps(g, indent=2), encoding="utf-8")

def load_nodes():
    nodes = {}
    for p in glob(str(NODES_DIR / "*.json")):
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
            nodes[j["id"]] = {"path": p, "node": j}
    return nodes

def apply_decay(nodes):
    now = datetime.utcnow()
    for k, v in nodes.items():
        node = v["node"]
        lu = node.get("last_updated")
        if not lu:
            continue
        try:
            dt = datetime.fromisoformat(lu.replace("Z", ""))
        except Exception:
            continue
        age = (now - dt).days
        if age >= STALE_DAYS:
            node["relevance_score"] = max(0.0, node.get("relevance_score", 50.0) * (100 - DECAY_PERCENT) / 100.0)
            with open(v["path"], "w", encoding="utf-8") as f:
                json.dump(node, f, indent=2)

def merge_exact_title(nodes):
    titles = {}
    removed = []
    for nid, v in list(nodes.items()):
        node = v["node"]
        t = node.get("title","").strip().lower()
        if not t:
            continue
        if t in titles:
            keep = titles[t]
            kp = nodes[keep]["path"]
            knode = nodes[keep]["node"]
            # merge simple fields
            knode["relations"].extend(node.get("relations",[]))
            knode["examples"].extend(node.get("examples",[]))
            knode["trust_score"] = max(knode.get("trust_score",0), node.get("trust_score",0))
            with open(kp, "w", encoding="utf-8") as f:
                json.dump(knode, f, indent=2)
            # remove file
            try:
                os.remove(v["path"])
            except Exception:
                pass
            removed.append(nid)
        else:
            titles[t] = nid
    return removed

def main():
    nodes = load_nodes()
    if not nodes:
        print("No nodes to optimize.")
        return
    apply_decay(nodes)
    removed = merge_exact_title(nodes)
    graph = load_graph()
    graph["nodes"] = [n for n in graph.get("nodes", []) if n not in removed]
    graph.setdefault("meta", {})["optimized_at"] = datetime.utcnow().isoformat() + "Z"
    save_graph(graph)
    print("Optimizer finished. removed:", len(removed))

if __name__ == "__main__":
    main()
