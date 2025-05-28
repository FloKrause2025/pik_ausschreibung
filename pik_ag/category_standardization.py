from openai import OpenAI

# Standard categories - THESE NEVER CHANGE!
STANDARD_CATEGORIES = [
    "Electronics - Audio",
    "Electronics - Microphones",
    "Electronics - Speakers",
    "Electronics - Amplifiers & DSP",
    "Electronics - Video Equipment",
    "Electronics - Displays & Screens",
    "Electronics - Projectors & Projection Screens",
    "Electronics - Cameras",
    "Electronics - Video Conferencing",
    "Electronics - Media Control Systems",
    "Electronics - Control Panels & Touchpanels",
    "Electronics - Signal Management & Switchers",
    "Electronics - AV Networking",
    "Electronics - Cables & Connectors",
    "Electronics - Power Distribution",
    "Electronics - Racks & Mounts",
    "Electronics - Media Furniture",
    "Electronics - Lighting",
    "Electronics - Recording Devices",
    "Electronics - Translation & Interpreter Systems",
    "Electronics - Assistive Listening",
    "Office Supplies",
    "Furniture",
    "Tools & Hardware",
    "Construction Materials",
    "Lighting",
    "Security Equipment",
    "Network Equipment",
    "Storage & Organization",
    "Other"
]

def standardize_category(product_description, product_name, brand, client):
    """
    Use AI to assign ONE standard category from our fixed list
    """
    categories_list = "\n".join([f"- {cat}" for cat in STANDARD_CATEGORIES])
    
    prompt = f"""
You must classify this product into EXACTLY ONE category from the provided list. Do not create new categories.

Product Information:
- Brand: {brand}
- Product Name: {product_name}  
- Description: {product_description}

Available Categories (choose EXACTLY ONE):
{categories_list}

Rules:
1. Choose the MOST SPECIFIC category that fits
2. Use EXACT category name from the list
3. If unsure, choose "Other"
4. Return ONLY the category name, nothing else

Category:
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a product categorization expert. Always choose exactly one category from the provided list. Never create new categories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        suggested_category = response.choices[0].message.content.strip()
        
        # Validate the category is in our standard list
        if suggested_category in STANDARD_CATEGORIES:
            return suggested_category
        else:
            # If AI returned something not in our list, find closest match or default to "Other"
            for standard_cat in STANDARD_CATEGORIES:
                if suggested_category.lower() in standard_cat.lower() or standard_cat.lower() in suggested_category.lower():
                    print(f"    🔧 Corrected '{suggested_category}' → '{standard_cat}'")
                    return standard_cat
            
            print(f"    ⚠️  Unknown category '{suggested_category}' → using 'Other'")
            return "Other"
            
    except Exception as e:
        print(f"    ❌ Category error: {e}")
        return "Other"