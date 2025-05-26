import requests
from bs4 import BeautifulSoup
import time
from openai import OpenAI

scraperapi_key = "e4e66def28c17bea868ba8f1b75f7455"
search_api_key = "qGo9tyZz3o7BQmmThZP6eSve"


query = "bitStarz casino review"
# Step 1: Fetch top 10 URLs from Google
url = "https://searchapi.io/api/v1/search"
params = {
    "engine": "google",
    "q": query,
    "api_key": search_api_key
}

response = requests.get(url, params=params)
data = response.json()

top_10_urls = []
for results in data.get("organic_results", [])[:10]:
    link = results.get('link')
    if link:
        top_10_urls.append(link)

for i, link in enumerate(top_10_urls, 1):
    print(f"{i}, {link}")

# Step 2: Fetch HTML content via ScraperAPI
successful_urls = []

for each_url in top_10_urls:
    try:
        api_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={each_url}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            successful_urls.append(response.text)
            print(f"✅ Successfully fetched: {each_url}")
    except Exception as e:
        print(f"❌ Error fetching {each_url}: {e}")

# Step 3: Extract all H1, H2, H3 headings from each page
print("\n📄 Extracting H1, H2, H3 from all successful pages:\n")

for index, html in enumerate(successful_urls, 1):
    soup = BeautifulSoup(html, 'html.parser')
    headings = soup.find_all(['h1', 'h2', 'h3'])

all_headings = []
   # Filter: only include pages with more than 5 headings
if len(headings) > 5:
    for tag in headings:
        clean_text = tag.get_text(strip=True)
        if clean_text:
            all_headings.append(clean_text)


# Build prompt from collected headings
headings_text = "\n".join(all_headings)

prompt = f"""Here are sample headings from competitor pages about BitStarz Casino:

{headings_text}

Based on these, create an ideal structured outline for a crypto casino review page.
Use proper H1, H2, H3 hierarchy. Be concise and logical in structure.
"""

# Send to ChatGPT
from openai import OpenAI

client = OpenAI(api_key="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")  # or set via environment variable

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are an SEO expert."},
        {"role": "user", "content": "Create an ideal outline for a crypto casino review page."}
    ]
)

print(response.choices[0].message.content)