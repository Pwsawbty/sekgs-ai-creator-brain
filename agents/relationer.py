#!/usr/bin/env python3
"""
relationer.py - builds edges by token overlap
"""

import os, json
from pathlib import Path
from glob import glob

ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
NODES_DIR = DATA_DIR / "nodes"
GRAPH_FILE = DATA_DIR / "graph.json"

def load_nodes():
    out = {}
    for p in glob(str(NODES_DIR/"*.json")):
        j = json.loads(Path(p).read_text(encoding="utf-8"))
        out[j["id"]] = j
    return out

def build_edges(nodes):
    edges=[]
    ids=list(nodes.keys())
    for i in range(len(ids)):
        a=ids[i]
        ta=(nodes[a].get("title","")+" "+" ".join(nodes[a].get("keywords",[]))).lower().split()
        for j in range(i+1,len(ids)):
            b=ids[j]
            tb=(nodes[b].get("title","")+" "+" ".join(nodes[b].get("keywords",[]))).lower().split()
            common=set(ta)&set(tb)
            if len(common)>=3:
                w=min(1.0,0.25+0.05*len(common))
                edges.append({"source":a, "target":b, "type":"related_to","weight":round(w,3)})
    return edges

def main():
    if not GRAPH_FILE.exists():
        return
    nodes=load_nodes()
    if not nodes:
        return
    edges=build_edges(nodes)
    seen=set()
    final=[]
    for e in edges:
        key=(e["source"],e["target"])
        if key in seen: continue
        seen.add(key)
        final.append(e)
    graph=json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    graph["nodes"]=list(nodes.keys())
    graph["edges"]=final
    graph.setdefault("meta",{})["relations_generated_at"]=__import__("datetime").datetime.utcnow().isoformat()+"Z"
    GRAPH_FILE.write_text(json.dumps(graph,indent=2),encoding="utf-8")
    print("Relationer edges:", len(final))

if __name__=="__main__":
    main()
