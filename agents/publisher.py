#!/usr/bin/env python3
"""
publisher.py - write a simple daily report and optionally sync to Notion if secrets present
Reads: data/graph.json
Writes: reports/daily-YYYY-MM-DD.md
"""

import json, os
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA = ROOT / "data"
GRAPH = DATA / "graph.json"
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

def main():
    try:
        g = json.loads(GRAPH.read_text(encoding="utf-8"))
    except Exception:
        g = {"nodes": [], "edges": []}
    d = datetime.utcnow().strftime("%Y-%m-%d")
    out = REPORTS / f"daily-{d}.md"
    lines = []
    lines.append(f"# SEKGS Daily — {d} (UTC)")
    lines.append(f"Nodes: {len(g.get('nodes', []))}")
    lines.append(f"Edges: {len(g.get('edges', []))}")
    lines.append("")
    top_nodes = g.get("nodes", [])[:10]
    for n in top_nodes:
        lines.append(f"- {n}")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("publisher: wrote", out)

if __name__ == "__main__":
    main()
