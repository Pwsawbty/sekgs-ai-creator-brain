import json

def run():
    try:
        raw = json.load(open("data/crawler_items.json"))
    except:
        raw = []

    cleaned = [item for item in raw if "title" in item]

    with open("data/cleaned_items.json", "w") as f:
        json.dump(cleaned, f, indent=2)

if __name__ == "__main__":
    run()
