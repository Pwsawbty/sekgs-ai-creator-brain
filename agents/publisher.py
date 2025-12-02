#!/usr/bin/env python3
"""
Safe, minimal and robust publisher agent.

- Reads data/graph.json
- Writes a Markdown report to reports/daily-YYYY-MM-DD.md
- Optionally posts summary to Notion if NOTION_TOKEN + NOTION_PAGE_ID provided
- Defensive: catches exceptions and always exits cleanly (non-zero only on fatal)
- Avoids complex comprehensions that may cause SyntaxError in various Python versions
"""
from pathlib import Path
import os
import json
from datetime import datetime
import traceback

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
LOG_DIR = DATA_DIR / "logs"

for p in (DATA_DIR, REPORTS_DIR, LOG_DIR):
    p.mkdir(parents=True, exist_ok=True)

GRAPH_FILE = DATA_DIR / "graph.json"
LOG_FILE = LOG_DIR / "publisher.log"

def log(msg):
    ts = datetime.utcnow().isoformat() + "Z"
    line = f"{ts} [publisher] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def safe_load_json(path: Path):
    if not path.exists():
        log(f"missing file {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"json load failed {e}")
        return None

def build_markdown_report(graph: dict):
    # simple and robust no-fancy-comprehensions
    meta = graph.get("meta", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    lines = []
    lines.append(f"# SEKGS Daily — {datetime.utcnow().strftime('%Y-%m-%d (UTC)')}")
    lines.append("")
    lines.append(f"Nodes: {len(nodes)}  Edges: {len(edges)}")
    lines.append("")

    if nodes:
        lines.append("## Nodes")
        for n in nodes:
            # ensure safe display of node id
            nid = str(n)
            lines.append(f"- `{nid}`")
        lines.append("")

    if edges:
        lines.append("## Edges")
        for e in edges:
            # an edge might be tuple/list or dict; normalize
            try:
                if isinstance(e, dict):
                    src = e.get("source", "src")
                    dst = e.get("target", "dst")
                elif isinstance(e, (list, tuple)) and len(e) >= 2:
                    src, dst = e[0], e[1]
                else:
                    src = str(e)
                    dst = ""
                lines.append(f"- `{src}` → `{dst}`")
            except Exception:
                lines.append(f"- `{str(e)}`")
        lines.append("")

    # add meta summary if present
    if meta:
        lines.append("## Meta")
        for k,v in meta.items():
            # Keep each meta on separate line to avoid complex formatting
            try:
                lines.append(f"- **{k}**: {v}")
            except Exception:
                lines.append(f"- **{k}**: (unserializable)")
        lines.append("")

    return "\n".join(lines)

def write_report(md_text: str):
    filename = f"daily-{datetime.utcnow().strftime('%Y-%m-%d')}.md"
    path = REPORTS_DIR / filename
    try:
        path.write_text(md_text, encoding="utf-8")
        log(f"wrote report: {path}")
        return path
    except Exception as e:
        log(f"failed write report: {e}")
        return None

def maybe_post_to_notion(md_text: str):
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    if not token or not page_id:
        log("NOT posting to Notion (no token/page_id)")
        return False
    # keep notion client optional to avoid import errors if not installed
    try:
        from notion_client import Client
    except Exception as e:
        log("notion-client not installed or import failed: " + str(e))
        return False
    try:
        notion = Client(auth=token)
        # Put a simple text block with timestamp + summary header
        summary = md_text.splitlines()[0] if md_text else "SEKGS report"
        # use a simple create block payload (no comprehensions)
        children = [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]}}
        ]
        notion.blocks.children.append(page_id, children=children)
        log("pushed summary to Notion")
        return True
    except Exception as e:
        log("notion push failed: " + str(e))
        return False

def main():
    try:
        graph = safe_load_json(GRAPH_FILE)
        if graph is None:
            log("graph missing or invalid - aborting publisher")
            return 1

        md = build_markdown_report(graph)
        report_path = write_report(md)
        # always try Notion but failure shouldn't crash pipeline
        maybe_post_to_notion(md)
        log("publisher finished OK")
        return 0
    except Exception as e:
        # never expose raw exception to break CI unpredictably
        log("publisher fatal error: " + str(e))
        log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit(main())
