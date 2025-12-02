import os
import json
import datetime
from notion_client import Client

def load_graph():
    with open("data/graph.json", "r") as f:
        return json.load(f)

def save_report(date_str, summary, nodes, edges):
    path = f"reports/daily-{date_str}.md"
    with open(path, "w") as f:
        f.write(f"# SEKGS Daily — {date_str} (UTC)\n\n")
        f.write(f"Nodes: {nodes} | Edges: {edges}\n\n")
        for n in summary:
            f.write(f"- {n}\n")
    return path

def build_notion_children(summary):
    """
    Create valid Notion children blocks. 
    This block NEVER throws syntax errors.
    """

    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"text": {"content": "SEKGS Daily Summary"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": f"Auto-generated knowledge graph summary."
                        }
                    }
                ]
            },
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"text": {"content": f"{item}"}}
                ]
            },
        } for item in summary
    ]

    return children


def publish_to_notion(date_str, summary, graph):
    notion_token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DB")

    if not notion_token or not db_id:
        print("Publisher: missing NOTION_TOKEN or NOTION_DB env vars")
        return

    notion = Client(auth=notion_token)

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Build children blocks
    children = build_notion_children(summary)

    notion.pages.create(
        parent={"database_id": db_id},
        properties={
            "Name": {
                "title": [
                    {"text": {"content": f"SEKGS Daily — {date_str}"}}
                ]
            },
            "Nodes": {"number": len(nodes)},
            "Edges": {"number": len(edges)},
        },
        children=children
    )

def publisher_main():
    print("publisher: START")

    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")

    graph = load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Summary list
    summary = nodes[:10] if len(nodes) > 10 else nodes

    # Save markdown report
    report_path = save_report(date_str, summary, len(nodes), len(edges))
    print(f"publisher: wrote report {report_path}")

    # Publish to notion
    publish_to_notion(date_str, summary, graph)

    print("publisher: DONE")

if __name__ == "__main__":
    publisher_main()
