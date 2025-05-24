import requests
import time
import re
from collections import Counter

def get_bitzarz_keywords():
    search_api_key = "qGo9tyZz3o7BQmmThZP6eSve"

    seed_keywords = [
        # Short-tail
        "bitstarz casino",
        "bitstarz review",
        "online casino",
        "crypto casino",

        # Mid-tail
        "bitstarz welcome bonus",
        "bitstarz legit or scam",
        "bitstarz casino payout time",
        "bitstarz vs stake",
        "bitstarz casino license",

        # Long-tail
        "is bitstarz casino safe for US players",
        "how long does bitstarz withdrawal take",
        "bitstarz no deposit bonus code 2024",
        "real user experience with bitstarz",
        "bitstarz KYC required before withdrawal"
    ]

    url = "https://www.searchapi.io/api/v1/search"
    all_phrases = []

    for i, keyword in enumerate(seed_keywords, 1):
        print(f"\n\n🔁 [{i}/{len(seed_keywords)}] 🔍 Keyword: {keyword.upper()}")

        params = {
            "engine": "google",
            "q": keyword,
            "api_key": search_api_key,
            "gl": "us",
            "hl": "en"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            phrases = []

            print("\n📄 Top SERP Results:")
            for result in data.get("organic_results", [])[:10]:
                title = result.get("title", "")
                print("-", title)
                phrases.append(title)

            print("\n🙋 People Also Ask:")
            for question in data.get("related_questions", []):
                q = question.get("question", "")
                print("-", q)
                phrases.append(q)

            print("\n🔗 Related Searches:")
            for term in data.get("related_searches", []):
                query = term.get("query", "")
                print("-", query)
                phrases.append(query)

            all_phrases.extend(phrases)

        except Exception as e:
            print(f"❌ Error fetching data for '{keyword}': {e}")

        time.sleep(1.5)  # avoid hammering the API too fast

    # ✅ Normalize, deduplicate, and extract keyword phrases
    cleaned_phrases = []
    for text in all_phrases:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        words = text.split()
        cleaned_phrases += [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        cleaned_phrases += [" ".join(words[i:i+3]) for i in range(len(words)-2)]

    # ✅ Filter only 'bitstarz' phrases
    phrase_counts = Counter(cleaned_phrases)
    filtered_phrases = {
        phrase: count
        for phrase, count in phrase_counts.items()
        if "bitstarz" in phrase
    }

    print("\n🔑 Top BitStarz-Related Keyword Phrases:")
    for phrase, count in Counter(filtered_phrases).most_common(20):
        print(f"{phrase} ({count})")

    # ✅ Return a list of phrases (ranked)
    return [phrase for phrase, _ in Counter(filtered_phrases).most_common(20)]