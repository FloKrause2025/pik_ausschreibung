import requests
import time
import re
from bs4 import BeautifulSoup
from collections import Counter
from openai import OpenAI

# API KEYS
scraperapi_key = "e4e66def28c17bea868ba8f1b75f7455"
search_api_key = "qGo9tyZz3o7BQmmThZP6eSve"
openai_key = "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"

# ✅ Step 1: Get relevant keywords first
def get_bitzarz_keywords():
    seed_keywords = [
        "bitstarz casino", "bitstarz review", "online casino", "crypto casino",
        "bitstarz welcome bonus", "bitstarz legit or scam", "bitstarz casino payout time",
        "bitstarz vs stake", "bitstarz casino license",
        "is bitstarz casino safe for US players", "how long does bitstarz withdrawal take",
        "bitstarz no deposit bonus code 2024", "real user experience with bitstarz",
        "bitstarz KYC required before withdrawal"
    ]
    url = "https://www.searchapi.io/api/v1/search"
    all_phrases = []

    for keyword in seed_keywords:
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
            phrases += [r.get("title", "") for r in data.get("organic_results", [])[:10]]
            phrases += [q.get("question", "") for q in data.get("related_questions", [])]
            phrases += [s.get("query", "") for s in data.get("related_searches", [])]
            all_phrases.extend(phrases)
        except Exception as e:
            print(f"❌ Error during keyword fetch: {e}")
        time.sleep(1.5)

    cleaned_phrases = []
    for text in all_phrases:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        words = text.split()
        cleaned_phrases += [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        cleaned_phrases += [" ".join(words[i:i+3]) for i in range(len(words)-2)]

    phrase_counts = Counter(cleaned_phrases)
    filtered_phrases = {
        phrase: count for phrase, count in phrase_counts.items()
        if "bitstarz" in phrase
    }

    return [phrase for phrase, _ in Counter(filtered_phrases).most_common(15)]


# ✅ Step 2: Fetch SERP pages and extract competitor headings
def get_competitor_headings(query):
    search_url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": search_api_key
    }

    response = requests.get(search_url, params=params)
    data = response.json()

    top_10_urls = [result.get("link") for result in data.get("organic_results", [])[:10] if result.get("link")]
    print("\n🌐 Top URLs:")
    for i, link in enumerate(top_10_urls, 1):
        print(f"{i}. {link}")

    successful_htmls = []
    for each_url in top_10_urls:
        try:
            api_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={each_url}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                successful_htmls.append(response.text)
                print(f"✅ {each_url}")
        except Exception as e:
            print(f"❌ {each_url} - {e}")

    all_headings = []
    for html in successful_htmls:
        soup = BeautifulSoup(html, 'html.parser')
        headings = soup.find_all(['h1', 'h2', 'h3'])
        if len(headings) > 5:
            for tag in headings:
                text = tag.get_text(strip=True)
                if text:
                    all_headings.append(text)

    return all_headings


# ✅ Step 3: Generate the outline using GPT
def generate_outline_from_data(headings, keywords):
    headings_text = "\n".join(headings)
    keywords_text = ", ".join(keywords)

    prompt = f"""Here are sample headings from competitor pages about BitStarz Casino:

{headings_text}

Also, here are 15 SEO-relevant keyword phrases for BitStarz:
{keywords_text}

Here are some rules you should follow in order to provide a TOP-Notch Page-Structure:

1. For each heading try to use any of the Keywords you can find here {keywords_text}
2. Try to use Longtail keywords in headings and FAQ's
3. Write a proper Purpose of each heading like this: 
"## Introduction to BitStarz Casino
Goal: In this section we want to give the user a clear instruction about the crypto casino. Keep this section short and descpritive. Dont use fluffy words or expression. 
Use short sentences and try to add the keyword you have added in the Heading from {keywords_text} in the first sentence."
4. Make sure that the "Goal" section is absoluitely descriptive and written for dummies!
5. Structure the Page-Structure by importance. That means everything which is valueable for the user needs to be in the 1/2 of the page. Everything which not really important
for the user but necessary to mention should be in the second half of this page. 
6. For each Heading use the appropiate html tag like <h1></h1>, <h2></h2> etc.. 

"""

    client = OpenAI(api_key=openai_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an SEO content architect."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# ✅ FINAL RUNNING ORDER
if __name__ == "__main__":
    print("🔍 Running BitStarz keyword research...\n")
    keywords = get_bitzarz_keywords()

    print("\n✅ Keywords Found:")
    for i, kw in enumerate(keywords, 1):
        print(f"{i}. {kw}")

    print("\n📄 Fetching competitor page structures...\n")
    headings = get_competitor_headings("bitstarz casino review")

    print("\n🧠 Generating final outline with GPT...\n")
    outline = generate_outline_from_data(headings, keywords)

    print("\n🧩 FINAL PAGE STRUCTURE:\n")
    print(outline)