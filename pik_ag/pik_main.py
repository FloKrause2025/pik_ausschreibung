import PyPDF2
import re
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
import json
import os
from collections import Counter
from openai import OpenAI

# 🆕 ADD DATABASE IMPORTS
from product_matcher import ProductMatcher
matcher = ProductMatcher()

# 🆕 ADD CATEGORY SYSTEM
from category_standardization import standardize_category, STANDARD_CATEGORIES

# 🔐 API Keys (ScraperAPI removed - using direct scraping only)
client = OpenAI(api_key="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")
search_api_key = "qGo9tyZz3o7BQmmThZP6eSve"

# 🆕 TESTING LIMIT - Process only 10 entries to save credits
TESTING_LIMIT = 10
print(f"🚧 TESTING MODE: Limited to {TESTING_LIMIT} entries to save credits")

# 🧠 Function: Generate search query from description
def generate_search_query(description):
    prompt = f"""
Given the following product description, write a precise Google search query in English that would help find the exact or closest matching product online. Focus on keywords, skip filler.

Product Description:
{description}

Search Query:
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert at crafting high-intent search queries for product discovery."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# 🔍 Function: SearchAPI → top 3 organic results
def search_top_3_results(query):
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": search_api_key,
        "gl": "de",
        "hl": "de"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        results = data.get("organic_results", [])[:3]

        top_entries = []
        for result in results:
            top_entries.append({
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", "")
            })

        return top_entries

    except Exception as e:
        print(f"❌ SearchAPI error: {e}")
        return []

# 🕷️ Function: Direct scraping
def scrape_website_html(url):
    """Direct website scraping with realistic browser headers"""
    print(f"    🕷️ Direct scraping: {url[:60]}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=20, allow_redirects=True)

        if response.status_code == 200:
            print(f"    ✅ Direct scraping success ({len(response.text)} chars)")
            return response.text
        else:
            print(f"    ❌ Direct scraping failed: HTTP {response.status_code}")
            return None

    except requests.exceptions.SSLError as e:
        print(f"    ⚠️  SSL Error - trying with verify=False: {str(e)[:50]}...")
        try:
            response = session.get(url, timeout=20, verify=False, allow_redirects=True)
            if response.status_code == 200:
                print(f"    ✅ Direct scraping success (no SSL verify) ({len(response.text)} chars)")
                return response.text
        except Exception as e2:
            print(f"    ❌ SSL retry failed: {str(e2)[:50]}...")

    except requests.exceptions.Timeout:
        print(f"    ❌ Timeout after 20 seconds")
    except requests.exceptions.ConnectionError as e:
        print(f"    ❌ Connection error: {str(e)[:50]}...")
    except Exception as e:
        print(f"    ❌ Direct scraping error: {str(e)[:50]}...")

    return None

# 🧠 Function: Analyze COMBINED HTML from multiple websites
def extract_combined_product_info(combined_html_content, original_description, sources):
    """Use OpenAI to extract product info from multiple combined websites"""
    print(f"    🧠 Analyzing combined HTML from {len(sources)} sources with OpenAI...")

    soup = BeautifulSoup(combined_html_content, 'html.parser')

    # Remove script, style, and nav elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Get clean text
    text_content = soup.get_text()
    lines = (line.strip() for line in text_content.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = ' '.join(chunk for chunk in chunks if chunk)

    # Limit text to avoid token limits
    clean_text = clean_text[:8000]

    sources_list = "\n".join([f"- {source}" for source in sources])

    prompt = f"""
You are analyzing multiple product webpages for the same product. The original search was for: "{original_description}"

I have scraped content from these websites:
{sources_list}

Please extract the MOST ACCURATE and COMPREHENSIVE information by combining data from all sources:

1. BRAND: The manufacturer or brand name (look across all sources for consistency)
2. PRODUCT NAME: The specific product name/model (choose the most detailed/accurate version)
3. PRODUCT DESCRIPTION: Create a comprehensive description combining the best details from all sources
4. PRICE: Extract price information - look for prices in EUR, USD, CHF, or other currencies. Include currency symbol. If you find a price range, include both values. If no price found, use "Not found"

Combined Webpage Content:
{clean_text}

Return your answer as a JSON object with exactly these keys:
{{
    "brand": "Brand name here",
    "product_name": "Most accurate product name here",
    "product_description": "Comprehensive description combining best info from all sources",
    "price": "Price with currency (e.g., €299.99, $150-200, CHF 450) or 'Not found'"
}}

Focus on accuracy and completeness. If sources conflict, choose the most detailed/authoritative information.
If you cannot find any information, use "Not found" as the value.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at extracting and combining product information from multiple web sources. Always return valid JSON with the most accurate information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        json_response = response.choices[0].message.content.strip()

        # Remove markdown formatting if present
        if json_response.startswith('```json'):
            json_response = json_response.replace('```json', '').replace('```', '').strip()
        elif json_response.startswith('```'):
            json_response = json_response.replace('```', '').strip()

        # Parse JSON
        product_info = json.loads(json_response)

        print(f"    ✅ Combined Analysis - Brand: {product_info.get('brand', 'N/A')}")
        print(f"    ✅ Combined Analysis - Product: {product_info.get('product_name', 'N/A')}")
        print(f"    ✅ Combined Analysis - Price: {product_info.get('price', 'N/A')}")

        # 🆕 STANDARDIZE CATEGORY
        if product_info.get('brand') and product_info.get('brand') != 'Not found':
            print(f"    🏷️  Determining standard category...")
            standard_category = standardize_category(
                product_info.get('product_description', ''),
                product_info.get('product_name', ''),
                product_info.get('brand', ''),
                client
            )
            product_info['standard_category'] = standard_category
            print(f"    ✅ Category: {standard_category}")
        else:
            product_info['standard_category'] = 'Other'

        # Debug: Show description length and preview
        description = product_info.get('product_description', 'N/A')
        if description and description != 'N/A' and description != 'Not found':
            desc_preview = description[:150] + "..." if len(description) > 150 else description
            print(f"    ✅ Combined Analysis - Description: {desc_preview} (Length: {len(description)} chars)")
        else:
            print(f"    ⚠️  Combined Description: {description}")

        return product_info

    except Exception as e:
        print(f"    ❌ Error analyzing combined HTML: {e}")
        return {
            "brand": "Analysis Error",
            "product_name": "Analysis Error",
            "product_description": f"Error: {str(e)}",
            "price": "Analysis Error",
            "standard_category": "Other"
        }

# Other functions remain the same...
def analyze_brand_distribution(df):
    """Analyze brand distribution and find the most common brand"""
    print(f"\n📊 PHASE 1: BRAND ANALYSIS")
    print(f"=" * 50)

    valid_brands = df[
        (df['Scraped_Brand'].notna()) &
        (~df['Scraped_Brand'].isin(['Not found', 'Analysis Error', 'All Scraping Failed', 'No Results', 'Processing Error']))
    ]['Scraped_Brand']

    if len(valid_brands) == 0:
        print("❌ No valid brands found in the data")
        return None, {}

    brand_counts = Counter(valid_brands)
    print(f"🔍 Found {len(valid_brands)} products with valid brand information")
    print(f"📈 Brand distribution ({len(brand_counts)} unique brands):")
    print()

    sorted_brands = brand_counts.most_common()

    for i, (brand, count) in enumerate(sorted_brands, 1):
        percentage = (count / len(valid_brands)) * 100
        print(f"  {i:2d}. {brand:20s} → {count:3d} products ({percentage:5.1f}%)")

    most_common_brand = sorted_brands[0][0]
    most_common_count = sorted_brands[0][1]

    print(f"\n🏆 MOST COMMON BRAND: {most_common_brand}")
    print(f"   📊 Appears in {most_common_count} out of {len(valid_brands)} products ({(most_common_count/len(valid_brands)*100):.1f}%)")

    # 🆕 ANALYZE CATEGORIES TOO
    if 'Standard_Category' in df.columns:
        print(f"\n🏷️  CATEGORY ANALYSIS:")
        valid_categories = df[df['Standard_Category'].notna()]['Standard_Category']
        category_counts = Counter(valid_categories)
        sorted_categories = category_counts.most_common()
        
        for i, (category, count) in enumerate(sorted_categories[:10], 1):
            percentage = (count / len(valid_categories)) * 100
            print(f"  {i:2d}. {category!s:25} → {count:3d} products ({percentage:5.1f}%)")

    return most_common_brand, dict(brand_counts)

def load_existing_results(output_file):
    """Load existing Excel file or return empty DataFrame with correct columns"""
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            if 'OZ' in existing_df.columns:
                processed_pos = set(existing_df['OZ'].astype(str))
            else:
                print(f"⚠️  Existing Excel file '{output_file}' does not contain an 'OZ' column. Treating all entries as unprocessed.")
                processed_pos = set()
            print(f"📊 Found existing file with {len(existing_df)} entries")
            print(f"🔄 Will resume processing from where we left off")
            return existing_df, processed_pos
        except Exception as e:
            print(f"⚠️  Error reading existing file: {e}")
            print(f"🆕 Creating new file instead")

    empty_df = pd.DataFrame(columns=[
        'OZ', 'Menge', 'Description', 'Search Query',
        'Title 1', 'Link 1', 'Snippet 1',
        'Title 2', 'Link 2', 'Snippet 2',
        'Title 3', 'Link 3', 'Snippet 3',
        'Scraped_Brand', 'Scraped_Product_Name',
        'Scraped_Product_Description', 'Scraped_Price', 'Standard_Category', 'Sources_Scraped'
    ])
    return empty_df, set()

def save_results_incrementally(existing_df, new_results, output_file):
    """Save results by appending new data to existing DataFrame"""
    if new_results:
        new_df = pd.DataFrame(new_results)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_excel(output_file, index=False)
        print(f"💾 Saved {len(new_results)} new entries to {output_file}")
        return combined_df
    return existing_df

# 📄 Load PDF and extract full text
print("📄 Loading and processing PDF...")
try:
    with open("philip_case.pdf", "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            text += page_text + "\n---PAGE_BREAK---\n"
except FileNotFoundError:
    print(f"❌ Error: PDF file 'philip_case.pdf' not found. Please ensure it's in the same directory.")
    exit(1)
except Exception as e:
    print(f"❌ Error reading PDF: {e}")
    exit(1)

# 🔍 Extracting entries from PDF
print("🔍 Extracting entries from PDF...")

entries = []
lines = text.split('\n')
current_oz = None
current_description_lines = []
menge_pattern = re.compile(r'(\d+(?:[.,]\d+)?)\s*(Stk|St|Stück|Stck|pcs|pc|pieces|x|psch|m|Std|Wo)\s*$', re.IGNORECASE)

def process_current_entry():
    global current_oz, current_description_lines, entries, menge_pattern
    if current_oz is not None and current_description_lines:
        full_description_raw = " ".join(current_description_lines).strip()
        
        menge = "Not found"
        description_text = full_description_raw

        # Attempt to extract menge
        last_line_with_menge = None
        for i in reversed(range(len(current_description_lines))):
            if menge_pattern.search(current_description_lines[i]):
                last_line_with_menge = current_description_lines[i]
                break

        if last_line_with_menge:
            menge_match_in_line = menge_pattern.search(last_line_with_menge)
            if menge_match_in_line:
                menge = menge_match_in_line.group(0).strip()
                temp_line_without_menge = re.sub(menge_pattern, '', last_line_with_menge).strip()
                reconstructed_lines = current_description_lines[:-1] + [temp_line_without_menge]
                description_text = " ".join(reconstructed_lines).strip()
        
        if menge == "Not found" or not description_text.strip():
            menge_match_in_full_desc = menge_pattern.search(full_description_raw)
            if menge_match_in_full_desc:
                menge = menge_match_in_full_desc.group(0).strip()
                description_text = re.sub(menge_pattern, '', full_description_raw).strip()
            else:
                description_text = full_description_raw

        # Final cleanup
        description_text = re.sub(r'\s*\n\s*', ' ', description_text).strip()
        description_text = re.sub(r'\s+', ' ', description_text).strip()
        
        entries.append((current_oz.rstrip('.'), menge, description_text))

    current_oz = None
    current_description_lines = []

for line in lines:
    line_stripped = line.strip()

    if not line_stripped or line_stripped == "---PAGE_BREAK---" or \
       line_stripped.startswith('LV-Datum:') or line_stripped.startswith('Seite '):
        continue
    
    # FIXED REGEX PATTERNS
    oz_line_match = re.match(r'^(\d{2}\.\d{2}\.\d{4}\.?)\s*(.*)$', line_stripped)
    summe_line_match = re.match(r'^Summe \d{2}(?:\.\d{2})?(?:.*?)$', line_stripped)

    if oz_line_match and not summe_line_match:
        process_current_entry()
        current_oz = oz_line_match.group(1).strip()
        current_description_lines = [oz_line_match.group(2).strip()]
        
    elif current_oz is not None:
        if not summe_line_match and line_stripped:
            current_description_lines.append(line_stripped)

# Process the very last entry
process_current_entry()

print(f"📊 Extracted {len(entries)} entries with OZ, Menge, and Description")

# 🔄 Load existing results and determine what to process
output_file = "philip_case_results_with_scraping.xlsx"
existing_df, processed_pos = load_existing_results(output_file)

# Process entries
if not entries:
    print("❌ No new entries extracted from PDF.")
    exit(0)
else:
    remaining_entries = [(oz, menge, desc) for oz, menge, desc in entries if oz not in processed_pos]

    # Apply testing limit
    if TESTING_LIMIT and len(remaining_entries) > TESTING_LIMIT:
        remaining_entries = remaining_entries[:TESTING_LIMIT]
        print(f"🚧 Limited to first {TESTING_LIMIT} entries for testing")

    if not remaining_entries:
        print("✅ All entries have been processed.")
        exit(0)
    
    print(f"📊 Processing {len(remaining_entries)} unprocessed entries out of {len(entries)} total.")

    new_results_buffer = []
    save_interval = 10
    start_time = time.time()

    for idx, (oz_number, menge, desc) in enumerate(remaining_entries, 1):
        try:
            print(f"\n🔢 Processing {oz_number} ({idx}/{len(remaining_entries)})")
            
            # Check cache first
            cache_result = matcher.check_before_processing(oz_number, desc, menge)
            if cache_result['found']:
                row = {
                    "OZ": oz_number,
                    "Menge": menge,
                    "Description": desc,
                    "Search Query": "From Cache",
                    "Scraped_Brand": cache_result.get('scraped_brand', ''),
                    "Scraped_Product_Name": cache_result.get('scraped_product_name', ''),
                    "Scraped_Product_Description": cache_result.get('scraped_product_description', ''),
                    "Scraped_Price": cache_result.get('scraped_price', ''),
                    "Standard_Category": cache_result.get('standard_category', 'Other'),
                    "Sources_Scraped": f"Cached ({cache_result.get('method', 'exact')})"
                }
                for i in range(1, 4): 
                    row[f"Title {i}"] = ""
                    row[f"Link {i}"] = ""
                    row[f"Snippet {i}"] = ""
                new_results_buffer.append(row)
                print("⚡ Used cached result - saved time and credits!")
                continue
            
            # Generate search query
            query = generate_search_query(desc)
            print(f"  🔍 Search query: {query}")
            
            # Get search results
            top3 = search_top_3_results(query)

            # Build basic row
            row = {
                "OZ": oz_number,
                "Menge": menge,
                "Description": desc,
                "Search Query": query
            }

            # Add search results
            for idx_result, entry in enumerate(top3, start=1):
                row[f"Title {idx_result}"] = entry["title"]
                row[f"Link {idx_result}"] = entry["link"]
                row[f"Snippet {idx_result}"] = entry["snippet"]

            for idx_result in range(len(top3) + 1, 4):
                row[f"Title {idx_result}"] = ""
                row[f"Link {idx_result}"] = ""
                row[f"Snippet {idx_result}"] = ""

            # Scrape and analyze
            if top3:
                print(f"  🎯 Direct scraping all {len(top3)} results")
                
                all_html_content = []
                scraped_sources = []
                
                for idx_scrape, result in enumerate(top3, start=1):
                    print(f"    🕷️ [{idx_scrape}/3] Scraping: {result['title'][:50]}...")
                    
                    html_content = scrape_website_html(result["link"])
                    
                    if html_content:
                        all_html_content.append(html_content)
                        scraped_sources.append(f"Source {idx_scrape}: {result['title']}")
                        print(f"    ✅ [{idx_scrape}/3] Success")
                    else:
                        print(f"    ❌ [{idx_scrape}/3] Failed")
                    
                    time.sleep(1)
                
                if all_html_content:
                    print(f"  🧠 Analyzing combined content from {len(all_html_content)} websites")
                    
                    combined_html = "\n\n--- WEBSITE SEPARATOR ---\n\n".join(all_html_content)
                    product_info = extract_combined_product_info(combined_html, desc, scraped_sources)
                    
                    row["Scraped_Brand"] = product_info["brand"]
                    row["Scraped_Product_Name"] = product_info["product_name"]
                    row["Scraped_Product_Description"] = product_info["product_description"]
                    row["Scraped_Price"] = product_info["price"]
                    row["Standard_Category"] = product_info.get("standard_category", "Other")
                    row["Sources_Scraped"] = f"{len(all_html_content)}/3 websites"
                    
                    # Save to cache
                    matcher.save_to_cache(oz_number, desc, menge, {
                        'scraped_brand': product_info["brand"],
                        'scraped_product_name': product_info["product_name"],
                        'scraped_product_description': product_info["product_description"],
                        'scraped_price': product_info["price"],
                        'standard_category': product_info.get("standard_category", "Other")
                    })
                    
                    time.sleep(2)
                else:
                    row["Scraped_Brand"] = "All Scraping Failed"
                    row["Scraped_Product_Name"] = "All Scraping Failed"
                    row["Scraped_Product_Description"] = "Could not scrape any websites"
                    row["Scraped_Price"] = "All Scraping Failed"
                    row["Standard_Category"] = "Other"
                    row["Sources_Scraped"] = "0/3 websites"
            else:
                row["Scraped_Brand"] = "No Results"
                row["Scraped_Product_Name"] = "No Results"
                row["Scraped_Product_Description"] = "No search results found"
                row["Scraped_Price"] = "No Results"
                row["Standard_Category"] = "Other"
                row["Sources_Scraped"] = "0/0 websites"

            new_results_buffer.append(row)

            # Save incrementally
            if len(new_results_buffer) % save_interval == 0:
                existing_df = save_results_incrementally(existing_df, new_results_buffer, output_file)
                new_results_buffer = []
                print(f"🔄 Incremental save completed - {idx}/{len(remaining_entries)} processed")

        except Exception as e:
            print(f"❌ Error processing {oz_number}: {e}")
            error_row = {
                "OZ": oz_number,
                "Menge": menge,
                "Description": desc,
                "Search Query": "Error",
                "Scraped_Brand": "Processing Error",
                "Scraped_Product_Name": "Processing Error",
                "Scraped_Product_Description": str(e),
                "Scraped_Price": "Processing Error",
                "Standard_Category": "Other",
                "Sources_Scraped": "Error"
            }
            new_results_buffer.append(error_row)

    # Final save
    if new_results_buffer:
        existing_df = save_results_incrementally(existing_df, new_results_buffer, output_file)
        print("✅ Final incremental save completed.")

    # Brand analysis
    print("--- Starting Brand Analysis ---")
    most_common_brand, brand_distribution = analyze_brand_distribution(existing_df)

    # Create Excel sheets
    final_df, _ = load_existing_results(output_file)

    print(f"\n--- Creating Excel Sheets: raw_data and filtered_data ---")

    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='raw_data', index=False)
            print(f"✅ Full data saved to 'raw_data' sheet.")

            filtered_columns = [
                'OZ', 'Description', 'Scraped_Brand', 'Scraped_Product_Name',
                'Standard_Category', 'Scraped_Price', 'Menge'
            ]

            existing_filtered_columns = [col for col in filtered_columns if col in final_df.columns]
            filtered_df = final_df[existing_filtered_columns]
            filtered_df.to_excel(writer, sheet_name='filtered_data', index=False)
            print(f"✅ Filtered data saved to 'filtered_data' sheet.")

            # Category summary
            if 'Standard_Category' in final_df.columns:
                category_summary = final_df['Standard_Category'].value_counts().reset_index()
                category_summary.columns = ['Category', 'Count']
                category_summary['Percentage'] = (category_summary['Count'] / len(final_df) * 100).round(2)
                category_summary.to_excel(writer, sheet_name='category_summary', index=False)
                print(f"✅ Category summary saved.")

    except Exception as e:
        print(f"❌ Error creating Excel sheets: {e}")

    print(f"--- Excel processing complete. Check '{output_file}' ---")
    print(f"🏷️  Categories used: {len(STANDARD_CATEGORIES)} standard categories")
    print(f"📊 Sheets created: raw_data, filtered_data, category_summary")