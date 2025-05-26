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

# 🔐 API Keys (ScraperAPI removed - using direct scraping only)
client = OpenAI(api_key="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")
search_api_key = "qGo9tyZz3o7BQmmThZP6eSve"

# --- Testing Limits (REMOVED) ---
# All limits have been removed to allow full processing.
# --- End of Testing Limits ---

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

# 🕷️ Function: Direct scraping ONLY (ScraperAPI removed)
def scrape_website_html(url):
    """Direct website scraping with realistic browser headers"""
    print(f"    🕷️ Direct scraping: {url[:60]}...")

    # Enhanced headers to look more like a real browser
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
        # Add session for better connection handling
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
            # Retry with SSL verification disabled for problematic sites
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

    # Clean HTML and extract text from combined content
    soup = BeautifulSoup(combined_html_content, 'html.parser')

    # Remove script, style, and nav elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Get clean text
    text_content = soup.get_text()
    lines = (line.strip() for line in text_content.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = ' '.join(chunk for chunk in chunks if chunk)

    # Limit text to avoid token limits (keep first 8000 chars since we have multiple sources)
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

        # Get and clean JSON response
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
            "price": "Analysis Error"
        }

# 📊 Function: Analyze brand distribution
def analyze_brand_distribution(df):
    """Analyze brand distribution and find the most common brand"""
    print(f"\n📊 PHASE 1: BRAND ANALYSIS")
    print(f"=" * 50)

    # Filter out non-brand entries
    valid_brands = df[
        (df['Scraped_Brand'].notna()) &
        (~df['Scraped_Brand'].isin(['Not found', 'Analysis Error', 'All Scraping Failed', 'No Results', 'Processing Error']))
    ]['Scraped_Brand']

    if len(valid_brands) == 0:
        print("❌ No valid brands found in the data")
        return None, {}

    # Count brand occurrences
    brand_counts = Counter(valid_brands)

    # Display brand statistics
    print(f"🔍 Found {len(valid_brands)} products with valid brand information")
    print(f"📈 Brand distribution ({len(brand_counts)} unique brands):")
    print()

    # Sort brands by count (descending)
    sorted_brands = brand_counts.most_common()

    for i, (brand, count) in enumerate(sorted_brands, 1):
        percentage = (count / len(valid_brands)) * 100
        print(f"  {i:2d}. {brand:20s} → {count:3d} products ({percentage:5.1f}%)")

    # Find most common brand
    most_common_brand = sorted_brands[0][0]
    most_common_count = sorted_brands[0][1]

    print(f"\n🏆 MOST COMMON BRAND: {most_common_brand}")
    print(f"   📊 Appears in {most_common_count} out of {len(valid_brands)} products ({(most_common_count/len(valid_brands)*100):.1f}%)")

    return most_common_brand, dict(brand_counts)

# 🔄 Function: Phase 2 - Re-scrape with dominant brand
def phase2_brand_focused_scraping(df, dominant_brand, output_file):
    """Re-scrape products where current brand != dominant brand"""
    print(f"\n🔄 PHASE 2: BRAND-FOCUSED RE-SCRAPING")
    print(f"=" * 50)

    # Find products that need re-scraping (different brand than dominant)
    rescrape_mask = (
        (df['Scraped_Brand'].notna()) &
        (~df['Scraped_Brand'].isin(['Not found', 'Analysis Error', 'All Scraping Failed', 'No Results', 'Processing Error'])) &
        (df['Scraped_Brand'] != dominant_brand)
    )

    rescrape_products = df[rescrape_mask].copy()

    # NO PHASE2_TESTING_LIMIT APPLIED HERE - removed
    # The line `if PHASE2_TESTING_LIMIT is not None and PHASE2_TESTING_LIMIT > 0:`
    # and its corresponding `rescrape_products.head()` have been removed.

    if len(rescrape_products) == 0:
        print(f"✅ All products already use the dominant brand '{dominant_brand}'")
        return df

    print(f"🎯 Found {len(rescrape_products)} products with different brands than '{dominant_brand}'")
    print(f"🔄 Will re-scrape these products with brand-focused queries")

    # Create new columns for brand-focused results
    brand_focused_columns = [
        'Brand_Focused_Search_Query', 'Brand_Focused_Brand', 'Brand_Focused_Product_Name',
        'Brand_Focused_Product_Description', 'Brand_Focused_Price', 'Brand_Focused_Sources_Scraped',
        'Brand_Match_Found'
    ]

    # Add new columns to existing dataframe
    for col in brand_focused_columns:
        if col not in df.columns:
            df[col] = ""

    updated_count = 0
    start_time = time.time()

    for idx, (df_idx, row) in enumerate(rescrape_products.iterrows(), 1):
        try:
            oz_number = row['OZ']
            original_query = row['Search Query']
            current_brand = row['Scraped_Brand']

            print(f"\n🔄 Re-scraping {oz_number} ({idx}/{len(rescrape_products)})")
            print(f"  📊 Current brand: {current_brand} → Target: {dominant_brand}")

            # --- START of NEW brand-focused query generation logic ---
            original_description_from_row = row['Description']
            brand_focused_query = original_query

            if current_brand.lower() not in original_description_from_row.lower():
                brand_focused_query = f"{dominant_brand} {original_query}"
                print(f"  ✅ Prepending dominant brand. Brand-focused query: {brand_focused_query}")
            else:
                print(f"  ⚠️ Original description contains '{current_brand}'. Keeping original query: {original_query}")
            # --- END of NEW brand-focused query generation logic ---

            # Search with brand-focused query
            top3 = search_top_3_results(brand_focused_query)

            if not top3:
                print(f"  ❌ No search results found")
                df.loc[df_idx, 'Brand_Focused_Search_Query'] = brand_focused_query
                df.loc[df_idx, 'Brand_Match_Found'] = 'No Search Results'
                continue

            # Scrape results
            print(f"  🎯 Scraping {len(top3)} brand-focused results")

            all_html_content = []
            scraped_sources = []

            for scrape_idx, result in enumerate(top3, start=1):
                print(f"    🕷️ [{scrape_idx}/3] Scraping: {result['title'][:50]}...")

                html_content = scrape_website_html(result["link"])

                if html_content:
                    all_html_content.append(html_content)
                    scraped_sources.append(f"Source {scrape_idx}: {result['title']}")
                    print(f"    ✅ [{scrape_idx}/3] Success")
                else:
                    print(f"    ❌ [{scrape_idx}/3] Failed")

                time.sleep(1)

            # Analyze scraped content
            if all_html_content:
                print(f"  🧠 Analyzing combined content from {len(all_html_content)} websites")

                combined_html = "\n\n--- WEBSITE SEPARATOR ---\n\n".join(all_html_content)
                product_info = extract_combined_product_info(combined_html, original_query, scraped_sources)

                # Check if the dominant brand was found
                found_brand = product_info.get('brand', '').strip()
                brand_match = found_brand.lower() == dominant_brand.lower() if found_brand else False

                # Update dataframe with brand-focused results
                df.loc[df_idx, 'Brand_Focused_Search_Query'] = brand_focused_query
                df.loc[df_idx, 'Brand_Focused_Brand'] = found_brand
                df.loc[df_idx, 'Brand_Focused_Product_Name'] = product_info['product_name']
                df.loc[df_idx, 'Brand_Focused_Product_Description'] = product_info['product_description']
                df.loc[df_idx, 'Brand_Focused_Price'] = product_info['price']
                df.loc[df_idx, 'Brand_Focused_Sources_Scraped'] = f"{len(all_html_content)}/3 websites"

                if brand_match:
                    df.loc[df_idx, 'Brand_Match_Found'] = 'YES - Brand Match!'
                    updated_count += 1
                    print(f"  ✅ SUCCESS: Found {dominant_brand} product!")
                else:
                    df.loc[df_idx, 'Brand_Match_Found'] = f'NO - Found: {found_brand}'
                    print(f"  ⚠️  Different brand found: {found_brand}")

            else:
                print(f"  ❌ All scraping failed")
                df.loc[df_idx, 'Brand_Focused_Search_Query'] = brand_focused_query
                df.loc[df_idx, 'Brand_Match_Found'] = 'Scraping Failed'

            # Progress indicator and save
            if idx % 5 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining_time = avg_time * (len(rescrape_products) - idx)
                print(f"  ⏱️  Progress: {idx}/{len(rescrape_products)} | ETA: {remaining_time/60:.1f} min")

                # Save progress
                df.to_excel(output_file, index=False)
                print(f"  💾 Progress saved")

            time.sleep(2)

        except Exception as e:
            print(f"  ❌ Error re-scraping {oz_number}: {e}")
            df.loc[df_idx, 'Brand_Focused_Search_Query'] = brand_focused_query if 'brand_focused_query' in locals() else 'Error'
            df.loc[df_idx, 'Brand_Match_Found'] = f'Error: {str(e)}'

    # Final save
    df.to_excel(output_file, index=False)

    total_time = time.time() - start_time
    print(f"\n✅ PHASE 2 COMPLETED!")
    print(f"⏱️  Re-scraping time: {total_time/60:.1f} minutes")
    print(f"🎯 Brand matches found: {updated_count}/{len(rescrape_products)}")
    print(f"💾 Results saved to: {output_file}")

    return df

# 🔄 Function: Load existing Excel or create empty DataFrame
def load_existing_results(output_file):
    """Load existing Excel file or return empty DataFrame with correct columns"""
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            # Ensure 'OZ' is treated as string for consistent comparison
            # Check if 'OZ' column exists in existing_df before attempting to use it
            if 'OZ' in existing_df.columns:
                processed_pos = set(existing_df['OZ'].astype(str))
            else:
                # If 'OZ' column is missing, treat all as unprocessed for this run to avoid KeyError
                # This can happen if a previous run failed early and created an empty file
                print(f"⚠️  Existing Excel file '{output_file}' does not contain an 'OZ' column. Treating all entries as unprocessed.")
                processed_pos = set()
            print(f"📊 Found existing file with {len(existing_df)} entries")
            print(f"🔄 Will resume processing from where we left off")
            return existing_df, processed_pos
        except Exception as e:
            print(f"⚠️  Error reading existing file: {e}")
            print(f"🆕 Creating new file instead")

    # Return empty DataFrame with all required columns, using 'OZ'
    empty_df = pd.DataFrame(columns=[
        'OZ', 'Menge', 'Description', 'Search Query',
        'Title 1', 'Link 1', 'Snippet 1',
        'Title 2', 'Link 2', 'Snippet 2',
        'Title 3', 'Link 3', 'Snippet 3',
        'Scraped_Brand', 'Scraped_Product_Name',
        'Scraped_Product_Description', 'Scraped_Price', 'Sources_Scraped',
        # New columns for Phase 2
        'Brand_Focused_Search_Query', 'Brand_Focused_Brand', 'Brand_Focused_Product_Name',
        'Brand_Focused_Product_Description', 'Brand_Focused_Price', 'Brand_Focused_Sources_Scraped',
        'Brand_Match_Found'
    ])
    return empty_df, set()

# 🔄 Function: Save results incrementally
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
            # Add a clear page break marker to help with multi-page parsing
            text += page_text + "\n---PAGE_BREAK---\n"
except FileNotFoundError:
    print(f"❌ Error: PDF file 'philip_case.pdf' not found. Please ensure it's in the same directory.")
    exit(1)
except Exception as e:
    print(f"❌ Error reading PDF: {e}")
    exit(1)

# 🔍 Extracting entries from PDF with refined logic for OZ
print("🔍 Extracting entries from PDF...")

entries = []
lines = text.split('\n')
current_oz = None
current_description_lines = []
# Updated menge_pattern to specifically capture the quantity and common units (including German ones)
# It's made more flexible to capture at the end of a line or block
menge_pattern = re.compile(r'(\d+(?:[.,]\d+)?)\s*(Stk|St|Stück|Stck|pcs|pc|pieces|x|psch|m|Std|Wo)\s*$', re.IGNORECASE)


# Helper function to process an accumulated entry
def process_current_entry():
    global current_oz, current_description_lines, entries, menge_pattern
    if current_oz is not None and current_description_lines:
        full_description_raw = " ".join(current_description_lines).strip()
        
        menge = "Not found"
        description_text = full_description_raw

        # Attempt to extract menge from the last line that matches the pattern, if possible
        last_line_with_menge = None
        for i in reversed(range(len(current_description_lines))):
            if menge_pattern.search(current_description_lines[i]):
                last_line_with_menge = current_description_lines[i]
                break # Found the last line with a quantity, stop searching

        if last_line_with_menge:
            menge_match_in_line = menge_pattern.search(last_line_with_menge)
            if menge_match_in_line:
                menge = menge_match_in_line.group(0).strip()
                # Remove the detected quantity from ONLY that specific line
                temp_line_without_menge = re.sub(menge_pattern, '', last_line_with_menge).strip()
                
                # Reconstruct the description by joining all lines, with the last line adjusted
                reconstructed_lines = current_description_lines[:-1] + [temp_line_without_menge]
                description_text = " ".join(reconstructed_lines).strip()
        
        # If no specific menge found on a line, or if the process above results in empty description,
        # fallback to a general removal from the whole block if needed (less precise but safer)
        if menge == "Not found" or not description_text.strip(): # Check if description is empty or not found
            # If still not found, try to remove from the full block.
            # This is a fallback if the line-by-line removal wasn't effective.
            menge_match_in_full_desc = menge_pattern.search(full_description_raw)
            if menge_match_in_full_desc:
                menge = menge_match_in_full_desc.group(0).strip()
                description_text = re.sub(menge_pattern, '', full_description_raw).strip()
            else:
                description_text = full_description_raw # Keep full description if no menge found
        
        # Final cleanup for description (removes extra newlines and spaces)
        description_text = re.sub(r'\s*\n\s*', ' ', description_text).strip()
        description_text = re.sub(r'\s+', ' ', description_text).strip()
        
        entries.append((current_oz.rstrip('.'), menge, description_text))

    current_oz = None
    current_description_lines = []


for line in lines:
    line_stripped = line.strip()

    # Skip lines that are page breaks, empty, or specific header/footer indicators
    if not line_stripped or line_stripped == "---PAGE_BREAK---" or \
       line_stripped.startswith('LV-Datum:') or line_stripped.startswith('Seite '):
        continue
    
    # Pattern for a new OZ entry: starts with XX.XX.XXXX. followed by optional content
    oz_line_match = re.match(r'^(\d{2}\.\d{2}\.\d{4}\.?)\s*(.*)$', line_stripped)
    
    # Pattern for "Summe" lines, which should NOT be treated as product items.
    summe_line_match = re.match(r'^Summe \d{2}(?:\.\d{2})?(?:.*?)$', line_stripped)

    if oz_line_match and not summe_line_match:
        # If we found a new OZ, first process the previously accumulated entry
        process_current_entry() # Call helper to process the last complete entry

        # Start new entry accumulation
        current_oz = oz_line_match.group(1).strip()
        # The remaining part of the current line after the OZ number is the start of the description
        current_description_lines = [oz_line_match.group(2).strip()]
        
    elif current_oz is not None:
        # Continue accumulating lines for the current description if it's not a summe line
        if not summe_line_match and line_stripped:
            current_description_lines.append(line_stripped)

# Process the very last entry after the loop finishes
process_current_entry()


print(f"📊 Extracted {len(entries)} entries with OZ, Menge, and Description")


# 🔄 Load existing results and determine what to process
output_file = "philip_case_results_with_scraping.xlsx"
existing_df, processed_pos = load_existing_results(output_file)

# --- ALL TESTING LIMITS ARE REMOVED HERE ---
# The logic now directly uses the 'entries' list from PDF parsing.
# The `TESTING_LIMIT` and `target_entries` are removed.
# `PHASE2_TESTING_LIMIT` also removed from the function where it was applied.

# Check if any entries were extracted from PDF or if there's existing data to analyze
if not entries: # No entries were extracted from PDF
    print("❌ No new entries extracted from PDF. Script cannot proceed with initial data processing.")
    print("Please check the PDF file and the parsing logic for 'OZ' numbers in the code.")
    
    if len(existing_df) > 0:
        print("However, existing data found in Excel. Proceeding to brand analysis of existing data.")
        # Perform brand analysis and Phase 2 using existing_df
        most_common_brand, brand_distribution = analyze_brand_distribution(existing_df)
        if most_common_brand:
            existing_df = phase2_brand_focused_scraping(existing_df, most_common_brand, output_file)
        else:
            print("❌ No dominant brand found for Phase 2 in existing data - insufficient data.")
    else:
        print("❌ No data to process. Exiting.")
        exit(0) # Exit cleanly if no data at all
        
# If there are entries from PDF, proceed with initial scraping
else: # `entries` is not empty, so new data needs processing
    # Filter out already processed entries from the full set (`entries` is now the full list)
    remaining_entries = [(oz, menge, desc) for oz, menge, desc in entries
                        if oz not in processed_pos]

    if not remaining_entries:
        print("✅ All entries extracted from PDF have already been processed in previous runs. Proceeding to brand analysis.")
    
    print(f"📊 Processing {len(remaining_entries)} unprocessed entries out of {len(entries)} total.")
    print(f"⏱️  Estimated time: {len(remaining_entries) * 0.3:.1f} - {len(remaining_entries) * 0.6:.1f} minutes")

    # 🧾 Build result rows - DIRECT SCRAPING ONLY
    new_results_buffer = [] 
    save_interval = 10  # Save every 10 entries for production

    start_time = time.time()

    for idx, (oz_number, menge, desc) in enumerate(remaining_entries, 1):
        try:
            print(f"\n🔢 Processing {oz_number} ({idx}/{len(remaining_entries)})")
            
            # Progress indicator
            if idx % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining_time = avg_time * (len(remaining_entries) - idx)
                print(f"⏱️  Progress: {idx}/{len(remaining_entries)} | Avg: {avg_time:.1f}s/entry | ETA: {remaining_time/60:.1f} min")
            
            # Step 1: Generate search query
            query = generate_search_query(desc)
            print(f"  🔍 Search query: {query}")
            
            # Step 2: Get top 3 search results
            top3 = search_top_3_results(query)

            # Step 3: Build basic row
            row = {
                "OZ": oz_number,
                "Menge": menge,
                "Description": desc,
                "Search Query": query
            }

            # Add search results to row
            for idx_result, entry in enumerate(top3, start=1):
                row[f"Title {idx_result}"] = entry["title"]
                row[f"Link {idx_result}"] = entry["link"]
                row[f"Snippet {idx_result}"] = entry["snippet"]

            # Fill empty columns for missing results
            for idx_result in range(len(top3) + 1, 4):
                row[f"Title {idx_result}"] = ""
                row[f"Link {idx_result}"] = ""
                row[f"Snippet {idx_result}"] = ""

            # Direct scrape ALL 3 results and combine info
            if top3:
                print(f"  🎯 Direct scraping all {len(top3)} results for comprehensive analysis")
                
                all_html_content = []
                scraped_sources = []
                
                # Scrape each of the top 3 results with direct scraping only
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
                
                # If we got any HTML content, analyze it
                if all_html_content:
                    print(f"  🧠 Analyzing combined content from {len(all_html_content)} websites")
                    
                    # Combine all HTML content
                    combined_html = "\n\n--- WEBSITE SEPARATOR ---\n\n".join(all_html_content)
                    
                    # Analyze combined HTML with OpenAI
                    product_info = extract_combined_product_info(combined_html, desc, scraped_sources)
                    
                    # Add extracted info to row
                    row["Scraped_Brand"] = product_info["brand"]
                    row["Scraped_Product_Name"] = product_info["product_name"]
                    row["Scraped_Product_Description"] = product_info["product_description"]
                    row["Scraped_Price"] = product_info["price"]
                    row["Sources_Scraped"] = f"{len(all_html_content)}/3 websites"
                    
                    time.sleep(2)
                else:
                    # If all scraping failed
                    row["Scraped_Brand"] = "All Scraping Failed"
                    row["Scraped_Product_Name"] = "All Scraping Failed"
                    row["Scraped_Product_Description"] = "Could not scrape any websites"
                    row["Scraped_Price"] = "All Scraping Failed"
                    row["Sources_Scraped"] = "0/3 websites"
            else:
                # If no search results found
                row["Scraped_Brand"] = "No Results"
                row["Scraped_Product_Name"] = "No Results"
                row["Scraped_Product_Description"] = "No search results found"
                row["Scraped_Price"] = "No Results"
                row["Sources_Scraped"] = "0/0 websites"

            new_results_buffer.append(row)

            # Terminal output for visibility
            print(f"  📋 Found {len(top3)} search results")

            # Save incrementally every few entries
            if len(new_results_buffer) % save_interval == 0:
                existing_df = save_results_incrementally(existing_df, new_results_buffer, output_file)
                new_results_buffer = []  # Clear the buffer
                print(f"🔄 Incremental save completed - {idx}/{len(remaining_entries)} processed")

        except Exception as e:
            print(f"❌ Error processing {oz_number}: {e}")
            # Add error row to maintain data structure
            error_row = {
                "OZ": oz_number,
                "Menge": menge,
                "Description": desc,
                "Search Query": "Error",
                "Scraped_Brand": "Processing Error",
                "Scraped_Product_Name": "Processing Error",
                "Scraped_Product_Description": str(e),
                "Scraped_Price": "Processing Error",
                "Sources_Scraped": "Error"
            }
            new_results_buffer.append(error_row)

    # Final save of any remaining results from initial scrape buffer
    if new_results_buffer:
        existing_df = save_results_incrementally(existing_df, new_results_buffer, output_file)
        print("✅ Final incremental save completed for initial scrape phase.")

    # After initial scraping (if any), perform brand analysis and Phase 2
    print("--- Starting Brand Analysis ---")
    most_common_brand, brand_distribution = analyze_brand_distribution(existing_df)

    if most_common_brand:
        print(f"--- Starting Phase 2: Brand-Focused Re-Scraping with '{most_common_brand}' ---")
        existing_df = phase2_brand_focused_scraping(existing_df, most_common_brand, output_file)
    else:
        print("❌ No dominant brand found for Phase 2. Skipping brand-focused re-scraping.")


# --- START of NEW Code Block for creating 'filtered_data' sheet ---

# Load the final comprehensive DataFrame after all processing is complete
# This ensures we have the most up-to-date data, including Phase 2 results.
final_df, _ = load_existing_results(output_file) # Re-load to get the very final state of the excel file

print(f"\n--- Creating Excel Sheets: raw_data and filtered_data ---")

try:
    # Use ExcelWriter to write to multiple sheets in one file
    # Ensure openpyxl is installed: pip install openpyxl
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 1. Write the full DataFrame to the 'raw_data' sheet
        final_df.to_excel(writer, sheet_name='raw_data', index=False)
        print(f"✅ Full data saved to 'raw_data' sheet.")

        # 2. Define and select columns for the 'filtered_data' sheet
        filtered_columns = [
            'OZ',
            'Description',
            'Scraped_Brand',          # Re-ordered as requested
            'Scraped_Product_Name',   # Re-ordered as requested
            'Menge'
        ]

        # Ensure selected columns exist in the DataFrame. If not, they won't be included.
        # This prevents KeyErrors if a column was not populated due to earlier errors.
        existing_filtered_columns = [col for col in filtered_columns if col in final_df.columns]

        # Create the filtered DataFrame with only the desired columns
        filtered_df = final_df[existing_filtered_columns]

        # 3. Write the filtered DataFrame to the 'filtered_data' sheet
        filtered_df.to_excel(writer, sheet_name='filtered_data', index=False)
        print(f"✅ Filtered data saved to 'filtered_data' sheet with columns: {existing_filtered_columns}.")

except Exception as e:
    print(f"❌ Error creating multiple Excel sheets: {e}")

print(f"--- Excel processing complete. Check '{output_file}' ---")

# --- END of NEW Code Block ---