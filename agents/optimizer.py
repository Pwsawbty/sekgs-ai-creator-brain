#!/usr/bin/env python3
"""
optimizer.py - decay + merge duplicate titles
"""

import os, json
from glob import glob
from pathlib import Path
from datetime import datetime, timedelta

ROOT=Path.cwd()
DATA_DIR=ROOT/"data"
NODES_DIR=DATA_DIR/"nodes"
GRAPH_FILE=DATA_DIR/"graph.json"

STALE_DAYS=180
DECAY_PERCENT=20

def load_graph():
    if not GRAPH_FILE.exists():
        return {"meta":{},"nodes":[],"edges":[]}
    return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))

def load_nodes():
    out={}
    for p in glob(str(NODES_DIR/"*.json")):
        j=json.loads(Path(p).read_text(encoding="utf-8"))
        out[j["id"]]={"path":p,"node":j}
    return out

def apply_decay(nodes):
    now=datetime.utcnow()
    for nid,v in nodes.items():
        node=v["node"]
        lu=node.get("last_updated")
        if not lu: continue
        try:
            dt=datetime.fromisoformat(lu.replace("Z",""))
        except: continue
        age=(now-dt).days
        if age>=STALE_DAYS:
            node["relevance_score"]=max(
                0.0,
                node.get("relevance_score",10.0)*(100-DECAY_PERCENT)/100
            )
            Path(v["path"]).write_text(json.dumps(node,indent=2),encoding="utf-8")

def merge_titles(nodes):
    titles={}
    removed=[]
    for nid,v in list(nodes.items()):
        node=v["node"]
        t=node.get("title","").strip().lower()
        if not t: continue
        if t in titles:
            keep=titles[t]
            kp=nodes[keep]["path"]
            kn=nodes[keep]["node"]
            kn["relations"].extend(node.get("relations",[]))
            kn["examples"].extend(node.get("examples",[]))
            kn["trust_score"]=max(kn.get("trust_score",0),node.get("trust_score",0))
            Path(kp).write_text(json.dumps(kn,indent=2),encoding="utf-8")
            os.remove(v["path"])
            removed.append(nid)
        else:
            titles[t]=nid
    return removed

def main():
    nodes=load_nodes()
    if not nodes: return
    apply_decay(nodes)
    removed=merge_titles(nodes)
    graph=load_graph()
    graph["nodes"]=[n for n in graph.get("nodes",[]) if n not in removed]
    graph["meta"]["optimized_at"]=datetime.utcnow().isoformat()+"Z"
    GRAPH_FILE.write_text(json.dumps(graph,indent=2),encoding="utf-8")
    print("Optimizer removed:", len(removed))

if __name__=="__main__":
    main()
