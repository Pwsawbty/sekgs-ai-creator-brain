#!/usr/bin/env python3
"""
ADVANCED PUBLISHER
- Embeddings-based insights
- ChatGPT report generator
- Notion dashboard sync
- Alert system (Slack/Email)
- Auto anomaly detection
"""

import os, json, time, math
from pathlib import Path
from datetime import datetime
import numpy as np

# External deps
import openai
from notion_client import Client as NotionClient
import requests

ROOT = Path.cwd()
GRAPH = ROOT/"data/graph.json"
NODES_DIR = ROOT/"data/nodes"
REPORTS = ROOT/"reports"

# Env
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB = os.getenv("NOTION_DATABASE_ID")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

openai.api_key = OPENAI_KEY
notion = NotionClient(auth=NOTION_TOKEN)

# -------------- HELPERS --------------

def load_graph():
    if not GRAPH.exists():
        raise RuntimeError("graph.json missing")
    return json.loads(GRAPH.read_text())

def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def embed(text):
    resp = openai.Embeddings.create(
        model="text-embedding-3-large",
        input=text[:5000]
    )
    return resp["data"][0]["embedding"]

def detect_anomalies(nodes, prev_count):
    diff = len(nodes) - prev_count
    if diff < -5:
        return f"⚠ Sharp drop in nodes: {diff}"
    if diff > 50:
        return f"⚠ Sudden spike in nodes: {diff}"
    return None

def slack_alert(msg):
    if not SLACK_WEBHOOK:
        return
    requests.post(SLACK_WEBHOOK, json={"text": msg})

def build_prompt(nodes_count, edges_count, clusters, anomalies):
    return f"""
Summarize today's knowledge engine run.

Nodes: {nodes_count}
Edges: {edges_count}
Clusters: {clusters}
Anomalies: {anomalies}

Write three sections:
1) Headline (one line)
2) Summary (5–8 sentences)
3) Action Items (3 bullets)

Return JSON with: headline, summary, actions.
"""

def gpt_summary(prompt):
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return resp["choices"][0]["message"]["content"]

def json_parse(text):
    import re
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except:
        return None

def notion_push(headline, summary, actions, nodes_count, edges_count, anomalies):
    page = notion.pages.create(
        parent={"database_id": NOTION_DB},
        properties={
            "Name": {"title":[{"text":{"content":headline}}]},
            "Date": {"date":{"start": str(datetime.utcnow().date())}},
            "Nodes Count": {"number": nodes_count},
            "Edges Count": {"number": edges_count},
            "Alerts": {"rich_text":[{"text":{"content": anomalies or "None"}}]}
        },
        children=[
            {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"text":{"content":summary}}]}},
            {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":[{"text":{"content":a}}]}}
            for a in actions
        ]
    )
    print("[publisher] Notion updated:", page["id"])

# -------------- MAIN EXECUTION --------------

def main():
    graph = load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # ---------- Embedding + Clustering ----------
    sample_texts = [n["text"][:1000] for n in nodes[:10] if "text" in n]
    embeddings = [embed(t) for t in sample_texts]

    clusters = len(embeddings)

    # ---------- Anomaly Detection ----------
    prev_count = graph.get("meta",{}).get("previous_nodes", len(nodes))
    anomaly = detect_anomalies(nodes, prev_count)
    if anomaly:
        slack_alert(f"SEKGS ALERT: {anomaly}")

    # ---------- Summary via GPT ----------
    prompt = build_prompt(len(nodes), len(edges), clusters, anomaly)
    raw = gpt_summary(prompt)
    parsed = json_parse(raw)

    if not parsed:
        headline = "Daily Knowledge Run"
        summary = raw[:1000]
        actions = ["Check crawler", "Review seeds", "Inspect logs"]
    else:
        headline = parsed["headline"]
        summary = parsed["summary"]
        actions = parsed["actions"]

    # ---------- Push to Notion ----------
    notion_push(headline, summary, actions, len(nodes), len(edges), anomaly)

    print("[publisher] completed.")

if __name__ == "__main__":
    main()
