import sqlite3
from datetime import datetime
from database_setup import create_description_hash
from difflib import SequenceMatcher

class ProductMatcher:
    def __init__(self, db_path='product_cache.db'):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def check_cache(self, oz_number, description, menge=""):
        """
        Check if we've already processed this exact PDF extraction
        """
        desc_hash = create_description_hash(oz_number, description, menge)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM extraction_cache 
            WHERE description_hash = ?
        ''', (desc_hash,))
        
        result = cursor.fetchone()
        
        if result:
            # Update last accessed
            cursor.execute('''
                UPDATE extraction_cache 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE description_hash = ?
            ''', (desc_hash,))
            conn.commit()
            
            print(f"✅ Found in cache: {result[5]} - {result[6]}")  # brand - product_name
            conn.close()
            
            return {
                'found': True,
                'scraped_brand': result[5],
                'scraped_product_name': result[6], 
                'scraped_product_description': result[7],
                'scraped_price': result[8],
                'standard_category': result[9] if len(result) > 9 else 'Other',
                'method': 'cache'
            }
        
        conn.close()
        return {'found': False}
    
    def fuzzy_search_similar(self, description):
        """
        Find similar descriptions we've processed before
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT original_description, scraped_brand, scraped_product_name, 
                   scraped_product_description, scraped_price, standard_category
            FROM extraction_cache
            WHERE scraped_brand != 'No Results' 
            AND scraped_brand != 'Processing Error'
            AND scraped_brand != 'All Scraping Failed'
        ''')
        
        cached_items = cursor.fetchall()
        matches = []
        
        for item in cached_items:
            cached_desc, brand, name, desc, price, category = item
            similarity = SequenceMatcher(None, description.lower(), cached_desc.lower()).ratio()
            
            if similarity > 0.7:  # 70% similarity threshold
                matches.append({
                    'similarity': similarity,
                    'scraped_brand': brand,
                    'scraped_product_name': name,
                    'scraped_product_description': desc,
                    'scraped_price': price,
                    'standard_category': category or 'Other',
                    'original_description': cached_desc
                })
        
        conn.close()
        
        if matches:
            # Return best match
            best_match = max(matches, key=lambda x: x['similarity'])
            print(f"📊 Found similar item: {best_match['similarity']:.1%} match")
            print(f"   Original: {best_match['original_description'][:50]}...")
            print(f"   Product: {best_match['scraped_brand']} - {best_match['scraped_product_name']}")
            
            return {
                'found': True,
                'method': 'fuzzy_match',
                'confidence': best_match['similarity'],
                **{k: v for k, v in best_match.items() if k != 'similarity'}
            }
        
        return {'found': False}
    
    def save_to_cache(self, oz_number, description, menge, scraped_data):
        """
        Save your processing results to cache
        """
        desc_hash = create_description_hash(oz_number, description, menge)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO extraction_cache 
            (oz_number, description_hash, original_description, menge,
             scraped_brand, scraped_product_name, scraped_product_description, scraped_price, standard_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            oz_number, desc_hash, description, menge,
            scraped_data.get('scraped_brand', ''),
            scraped_data.get('scraped_product_name', ''),
            scraped_data.get('scraped_product_description', ''),
            scraped_data.get('scraped_price', ''),
            scraped_data.get('standard_category', 'Other')
        ))
        
        conn.commit()
        conn.close()
        print("💾 Saved to cache for future use")
    
    def check_before_processing(self, oz_number, description, menge=""):
        """
        MAIN FUNCTION: Check cache before running your expensive processing
        """
        print(f"\n🔎 Checking: {oz_number}")
        print(f"   Description: {description[:60]}...")
        print(f"   Menge: {menge}")
        
        # Step 1: Exact cache check
        cache_result = self.check_cache(oz_number, description, menge)
        if cache_result['found']:
            return cache_result
        
        # Step 2: Similar description check  
        fuzzy_result = self.fuzzy_search_similar(description)
        if fuzzy_result['found'] and fuzzy_result['confidence'] > 0.8:
            print("🎯 High confidence match - using cached result")
            # Save this as exact match for future
            self.save_to_cache(oz_number, description, menge, fuzzy_result)
            return fuzzy_result
        
        # Step 3: Not found - need to process
        print("❌ Not found in cache - need to process with your script")
        return {'found': False, 'message': 'Process with your existing logic'}

# Test with your data format
if __name__ == "__main__":
    matcher = ProductMatcher()
    
    # Test with sample data matching your format
    test_result = matcher.check_before_processing(
        oz_number="01.02.2024",
        description="Wireless Bluetooth headphones with noise cancellation", 
        menge="5 Stk"
    )
    
    print(f"Result: {test_result}")