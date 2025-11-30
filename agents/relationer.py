#!/usr/bin/env python3
"""
Ultra-pro relationer.py
- Deterministic lightweight similarity edges (no external libs)
- Verbose logs for GitHub Actions (prints counts & quick diagnostics)
- Atomic write and checksum for auditability
- Config via env vars: RELATIONS_TOP_K, MIN_SIMILARITY
- Safe: will never crash workflow on malformed nodes; prints reasons
"""

import os, json, tempfile, hashlib, time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
NODES_DIR = DATA_DIR / "nodes"
GRAPH_FILE = DATA_DIR / "graph.json"

RELATIONS_TOP_K = int(os.environ.get("RELATIONS_TOP_K", "3"))
MIN_SIMILARITY = float(os.environ.get("MIN_SIMILARITY", "0.05"))
MAX_SUMMARY_CHARS = int(os.environ.get("MAX_SUMMARY_CHARS", "2000"))

def log(*args):
    print("[relationer]", *args)

def safe_read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        log("WARN: failed to read", str(p), "-", type(e).__name__, str(e)[:120])
        return None

def safe_list_nodes() -> List[Path]:
    if not NODES_DIR.exists():
        log("INFO: nodes dir not found:", NODES_DIR)
        return []
    return sorted([p for p in NODES_DIR.glob("*.json") if p.is_file()])

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").strip()
    s = " ".join(s.split())
    return s.lower()

def tokenize(s: str) -> Set[str]:
    s = normalize_text(s)
    if len(s) > MAX_SUMMARY_CHARS:
        s = s[:MAX_SUMMARY_CHARS]
    import re
    toks = [t for t in re.split(r"\W+", s) if t]
    return set(toks)

def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = a.intersection(b)
    union = a.union(b)
    return len(inter) / len(union) if union else 0.0

def atomic_write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        Path(tmp).replace(path)
    finally:
        if tmp and Path(tmp).exists():
            try:
                Path(tmp).unlink()
            except Exception:
                pass

def compute_checksum(g: Dict) -> str:
    payload = {
        "nodes": sorted(g.get("nodes", [])),
        "edges": sorted([f"{e['source']}|{e['target']}|{e.get('type')}|{e.get('weight')}" for e in g.get("edges", [])])
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_graph() -> Dict:
    g = safe_read_json(GRAPH_FILE)
    if not g:
        g = {"meta": {"domain":"ai-tools-creator-workflows","version":"0.1"}, "nodes": [], "edges": []}
    # ensure keys
    g.setdefault("nodes", [])
    g.setdefault("edges", [])
    g.setdefault("meta", {})
    return g

def read_node_files() -> List[Dict]:
    files = safe_list_nodes()
    nodes = []
    for p in files:
        j = safe_read_json(p)
        if not j:
            continue
        nid = j.get("id") or p.stem
        title = normalize_text(j.get("title",""))
        summary = normalize_text(j.get("summary",""))
        text = (title + " " + summary).strip()
        nodes.append({"id": nid, "title": title, "summary": summary, "text": text, "file": str(p)})
    log("INFO: loaded", len(nodes), "node files")
    return nodes

def compute_edges(nodes: List[Dict]) -> List[Dict]:
    token_map = {}
    for nd in nodes:
        token_map[nd["id"]] = tokenize(nd["text"])
    edges_map = {}
    n = len(nodes)
    for i in range(n):
        a = nodes[i]
        scores = []
        for j in range(n):
            if i == j:
                continue
            b = nodes[j]
            score = jaccard(token_map[a["id"]], token_map[b["id"]])
            if score >= MIN_SIMILARITY:
                scores.append((b["id"], score))
        scores.sort(key=lambda x: (-x[1], x[0]))
        top = scores[:RELATIONS_TOP_K]
        for tid, w in top:
            s,t = sorted([a["id"], tid])
            key = f"{s}__{t}__related_to"
            # keep max weight for same edge
            if key not in edges_map or edges_map[key]["weight"] < w:
                edges_map[key] = {"source": s, "target": t, "type": "related_to", "weight": round(float(w),3)}
    edges = sorted(edges_map.values(), key=lambda e: (e["source"], e["target"], -e["weight"]))
    log("INFO: computed", len(edges), "edges")
    return edges

def main():
    start = time.time()
    log("START relationer run")
    graph = load_graph()
    nodes = read_node_files()
    # ensure graph nodes reflect disk
    disk_ids = [n["id"] for n in nodes]
    merged = []
    seen = set()
    for x in disk_ids + graph.get("nodes", []):
        if x not in seen:
            merged.append(x); seen.add(x)
    graph["nodes"] = merged
    # compute edges
    edges = compute_edges(nodes)
    graph["edges"] = edges
    now = datetime.utcnow().isoformat() + "Z"
    graph["meta"]["relations_generated_at"] = now
    graph["meta"]["relations_count"] = len(edges)
    graph["meta"]["relations_top_k"] = RELATIONS_TOP_K
    graph["meta"]["relations_min_similarity"] = MIN_SIMILARITY
    graph["meta"]["relations_checksum"] = compute_checksum(graph)
    try:
        atomic_write(GRAPH_FILE, graph)
        log("OK: wrote graph:", GRAPH_FILE, "| nodes:", len(graph["nodes"]), "edges:", len(edges))
    except Exception as e:
        log("ERROR: failed to write graph:", str(e))
        raise
    elapsed = time.time() - start
    log("DONE relationer run in %.2fs" % elapsed)

if __name__ == "__main__":
    main()
