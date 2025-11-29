import json

def run():
    data = [
        {"title": "OpenAI releases new model", "source": "news"},
        {"title": "GitHub announces automation updates", "source": "dev"}
    ]

    with open("data/crawler_items.json", "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    run()    try:
        r = requests.get(u, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        text = r.text
        title = ""
        lower = text.lower()
        if "<title>" in lower:
            try:
                s = lower.index("<title>")
                e = lower.index("</title>", s)
                title = text[s+7:e].strip()
            except Exception:
                title = ""
        snippet = text.strip()[:1500].replace("\n", " ")
        return {"url": u, "title": title or u, "snippet": snippet[:1000], "fetched_at": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        print("crawl error:", u, str(e))
        return None

def main():
    seeds = load_seeds()
    items = []
    for s in seeds:
        print("Crawling:", s)
        res = fetch(s)
        if res:
            items.append(res)
        time.sleep(1.2)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({"generated_at": datetime.utcnow().isoformat()+"Z", "items": items}, indent=2), encoding="utf-8")
    print("Crawl finished:", len(items))

if __name__ == "__main__":
    main()
