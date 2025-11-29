import json

def run():
    data = [
        {"title": "OpenAI releases new model", "source": "news"},
        {"title": "GitHub announces automation updates", "source": "dev"}
    ]

    with open("data/crawler_items.json", "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    run()
