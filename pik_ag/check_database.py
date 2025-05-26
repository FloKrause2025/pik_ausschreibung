import sqlite3
import pandas as pd
from datetime import datetime

def check_database_contents():
    """
    Check what's stored in your product cache database
    """
    try:
        conn = sqlite3.connect('product_cache.db')
        
        print("🔍 CHECKING DATABASE CONTENTS")
        print("=" * 50)
        
        # Check extraction_cache table
        print("\n📋 EXTRACTION CACHE TABLE:")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM extraction_cache")
        cache_count = cursor.fetchone()[0]
        
        if cache_count == 0:
            print("❌ No entries found in extraction_cache table")
        else:
            print(f"✅ Found {cache_count} cached entries")
            
            print("\n📊 Recent cache entries:")
            cursor.execute("""
                SELECT oz_number, original_description, scraped_brand, 
                       scraped_product_name, standard_category, created_at 
                FROM extraction_cache 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            recent_entries = cursor.fetchall()
            for i, entry in enumerate(recent_entries, 1):
                oz, desc, brand, product, category, created = entry
                print(f"  {i}. OZ: {oz}")
                print(f"     Description: {desc[:60]}...")
                print(f"     Brand: {brand}")
                print(f"     Product: {product}")
                print(f"     Category: {category}")
                print(f"     Cached: {created}")
                print()
        
        # Check products table
        print("\n🏷️  PRODUCTS TABLE:")
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        if products_count == 0:
            print("❌ No entries found in products table")
        else:
            print(f"✅ Found {products_count} unique products")
            
            cursor.execute("""
                SELECT product_name, brand, created_at 
                FROM products 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            recent_products = cursor.fetchall()
            print("\n📊 Recent products:")
            for i, product in enumerate(recent_products, 1):
                name, brand, created = product
                print(f"  {i}. {brand} - {name} (Added: {created})")
        
        # Check categories distribution
        print("\n🏷️  CATEGORIES IN CACHE:")
        cursor.execute("""
            SELECT standard_category, COUNT(*) as count 
            FROM extraction_cache 
            WHERE standard_category IS NOT NULL
            GROUP BY standard_category 
            ORDER BY count DESC
        """)
        
        categories = cursor.fetchall()
        if categories:
            for category, count in categories:
                print(f"  • {category}: {count} entries")
        else:
            print("  No categories found")
        
        # Check brands distribution
        print("\n🏢 BRANDS IN CACHE:")
        cursor.execute("""
            SELECT scraped_brand, COUNT(*) as count 
            FROM extraction_cache 
            WHERE scraped_brand NOT IN ('Not found', 'Analysis Error', 'All Scraping Failed', 'No Results', 'Processing Error')
            GROUP BY scraped_brand 
            ORDER BY count DESC
        """)
        
        brands = cursor.fetchall()
        if brands:
            for brand, count in brands:
                print(f"  • {brand}: {count} entries")
        else:
            print("  No valid brands found")
        
        conn.close()
        
        # Summary
        print("\n" + "=" * 50)
        print("📈 SUMMARY:")
        print(f"  Total cached extractions: {cache_count}")
        print(f"  Unique products: {products_count}")
        print(f"  Database file: product_cache.db")
        
        if cache_count > 0:
            print("\n✅ Database is working! Your data has been cached.")
        else:
            print("\n⚠️  Database is empty. Check if your script ran successfully.")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def search_in_cache(search_term):
    """
    Search for specific items in your cache
    """
    try:
        conn = sqlite3.connect('product_cache.db')
        cursor = conn.cursor()
        
        print(f"\n🔍 SEARCHING FOR: '{search_term}'")
        print("-" * 30)
        
        cursor.execute("""
            SELECT oz_number, original_description, scraped_brand, 
                   scraped_product_name, scraped_price
            FROM extraction_cache 
            WHERE original_description LIKE ? 
               OR scraped_brand LIKE ?
               OR scraped_product_name LIKE ?
        """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        
        results = cursor.fetchall()
        
        if results:
            print(f"Found {len(results)} matches:")
            for i, result in enumerate(results, 1):
                oz, desc, brand, product, price = result
                print(f"\n  {i}. OZ: {oz}")
                print(f"     Description: {desc}")
                print(f"     Found: {brand} - {product}")
                print(f"     Price: {price}")
        else:
            print("No matches found")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error searching: {e}")

if __name__ == "__main__":
    # Check overall database contents
    check_database_contents()
    
    # Example searches - you can modify these
    example_searches = ["headphones", "sony", "apple"]
    
    for search_term in example_searches:
        search_in_cache(search_term)
    
    print("\n" + "=" * 50)
    print("💡 TIP: Modify the search terms at the bottom of this script")
    print("    to search for specific products in your cache!")