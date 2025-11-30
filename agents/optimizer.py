#!/usr/bin/env python3
"""
optimizer.py - simple graph optimizer (adds flag)
Reads/Writes: data/graph.json
"""

import json
from pathlib import Path

ROOT = Path.cwd()
GRAPH = ROOT / "data" / "graph.json"

def main():
    try:
        g = json.loads(GRAPH.read_text(encoding="utf-8"))
    except Exception:
        g = {"nodes": [], "edges": []}
    g.setdefault("meta", {})["optimized"] = True
    GRAPH.write_text(json.dumps(g, indent=2), encoding="utf-8")
    print("optimizer: updated graph meta")

if __name__ == "__main__":
    main()
