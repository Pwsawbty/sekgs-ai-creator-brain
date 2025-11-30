#!/usr/bin/env python3
"""
Robust relationer for SEKGS.

- No external dependencies (only Python stdlib).
- Deterministic, idempotent, atomic writes.
- Uses difflib.SequenceMatcher for a stable text similarity metric.
- Safeguards:
  * skips relation stage if <2 nodes
  * writes partial graph if anything fails
  * computes top-k relations per node with dedupe
  * writes checksums and timestamps in meta
  * logs to data/logs/relationer.log
- Configurable with environment variables:
  RELATIONS_TOP_K (default 3)
  RELATIONS_MIN_SIM (default 0.05)
  DATA_DIR (default ./data)
"""
from pathlib import Path
import json, os, time, traceback, hashlib
from difflib import SequenceMatcher
from typing import List, Tuple

# ---------- config ----------
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
NODES_DIR = DATA_DIR / "nodes"
GRAPH_FILE = DATA_DIR / "graph.json"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "relationer.log"

RELATIONS_TOP_K = int(os.environ.get("RELATIONS_TOP_K", "3"))
RELATIONS_MIN_SIM = float(os.environ.get("RELATIONS_MIN_SIM", "0.05"))
# ---------- end config ----------

def log(msg: str):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{ts} [relationer] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # If logging fails, don't crash
        pass

def safe_read_json(path: Path):
    try:
        s = path.read_text(encoding="utf-8")
        return json.loads(s)
    except Exception as e:
        log(f"safe_read_json failed for {path}: {e}")
        return None

def sorted_node_list() -> List[Path]:
    """Return deterministic sorted list of node file paths."""
    try:
        files = [p for p in NODES_DIR.iterdir() if p.is_file() and p.suffix == ".json"]
        # sort by name to keep deterministic order
        files.sort(key=lambda p: p.name)
        return files
    except Exception as e:
        log(f"sorted_node_list error: {e}")
        return []

def normalize_text(s: str) -> str:
    # Minimal normalization: lowercase, collapse whitespace
    return " ".join(s.replace("\r", " ").replace("\n", " ").split()).lower()

def similarity(a: str, b: str) -> float:
    """Stable similarity measure using SequenceMatcher ratio."""
    try:
        if not a or not b:
            return 0.0
        # SequenceMatcher is deterministic and in stdlib
        return float(SequenceMatcher(None, a, b).ratio())
    except Exception as e:
        log(f"similarity error: {e}")
        return 0.0

def compute_relations(nodes: List[Tuple[str, str]]) -> Tuple[List[dict], int]:
    """
    nodes: list of tuples (node_id, text)
    returns (edges, relations_count)
    edges entries: { "source": id1, "target": id2, "score": float }
    """
    n = len(nodes)
    edges = []
    seen_pairs = set()
    # Pre-normalize texts
    norm_texts = [normalize_text(t) for (_, t) in nodes]

    for i in range(n):
        id_i, _ = nodes[i]
        sims = []
        for j in range(n):
            if i == j:
                continue
            id_j, _ = nodes[j]
            pair = (min(id_i, id_j), max(id_i, id_j))
            if pair in seen_pairs:
                # skip duplicate computation for performance and determinism
                continue
            score = similarity(norm_texts[i], norm_texts[j])
            sims.append((id_j, score, pair))
        # pick top-k by score descending and above min similarity
        sims.sort(key=lambda x: (-x[1], x[0]))
        chosen = []
        for id_j, score, pair in sims:
            if score >= RELATIONS_MIN_SIM:
                chosen.append((id_j, score, pair))
            if len(chosen) >= RELATIONS_TOP_K:
                break
        for id_j, score, pair in chosen:
            # add only if not already added by reverse
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            # pick deterministic direction: lexicographically smaller -> larger
            source, target = pair
            edges.append({"source": source, "target": target, "score": round(float(score), 6)})
    return edges, len(edges)

def atomic_write(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)

def file_checksum(path: Path) -> str:
    try:
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        return h
    except Exception:
        return ""

def main():
    start = time.time()
    log("START relationer run")
    try:
        node_files = sorted_node_list()
        if not node_files:
            log("No node files found - nothing to do")
            # If graph exists, still update relations_generated_at
            if GRAPH_FILE.exists():
                g = safe_read_json(GRAPH_FILE) or {}
            else:
                g = {"meta": {}, "nodes": [], "edges": []}
            g.setdefault("meta", {})
            g["meta"]["relations_generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            g["meta"]["relations_count"] = 0
            atomic_write(GRAPH_FILE, json.dumps(g, ensure_ascii=False, indent=2))
            log("Wrote empty graph meta")
            return 0

        nodes = []
        for p in node_files:
            j = safe_read_json(p)
            if not j:
                log(f"Skipping unreadable node file {p}")
                continue
            node_id = j.get("id") or p.stem
            text = j.get("text") or ""
            nodes.append((node_id, text))
        # if not enough nodes, write meta and exit
        if len(nodes) < 2:
            log(f"Only {len(nodes)} node(s) present - skipping relation computation")
            if GRAPH_FILE.exists():
                g = safe_read_json(GRAPH_FILE) or {}
            else:
                g = {"meta": {}, "nodes": [], "edges": []}
            g.setdefault("meta", {})
            g["meta"]["relations_generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            g["meta"]["relations_count"] = 0
            atomic_write(GRAPH_FILE, json.dumps(g, ensure_ascii=False, indent=2))
            log("Wrote graph meta for small corpus")
            return 0

        # compute relations
        edges, count = compute_relations(nodes)
        # prepare graph structure
        meta = {
            "domain": "ai-tools-creator-workflows",
            "version": "0.1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "relations_generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "relations_count": int(count),
            "relations_top_k": int(RELATIONS_TOP_K),
            "relations_min_similarity": float(RELATIONS_MIN_SIM),
            "relations_checksum": "",  # will fill after write
            "optimized": True
        }
        node_ids = [nid for (nid, _) in nodes]
        graph_obj = {"meta": meta, "nodes": node_ids, "edges": edges}

        # atomic write graph
        atomic_write(GRAPH_FILE, json.dumps(graph_obj, ensure_ascii=False, indent=2))
        # compute checksum and update meta (atomic replace)
        cs = file_checksum(GRAPH_FILE)
        graph_obj["meta"]["relations_checksum"] = cs
        atomic_write(GRAPH_FILE, json.dumps(graph_obj, ensure_ascii=False, indent=2))

        duration = time.time() - start
        log(f"OK: wrote graph: {GRAPH_FILE} | nodes: {len(node_ids)} edges: {count} | dt={duration:.2f}s")
        return 0
    except Exception as e:
        # write safe partial graph meta
        log("EXCEPTION in relationer: " + str(e))
        tb = traceback.format_exc()
        log(tb)
        try:
            g = {"meta": {"relations_generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "relations_count": 0}, "nodes": [], "edges": []}
            atomic_write(GRAPH_FILE, json.dumps(g, ensure_ascii=False, indent=2))
            log("Wrote fallback partial graph.json after exception")
        except Exception as e2:
            log("Failed to write fallback graph.json: " + str(e2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
