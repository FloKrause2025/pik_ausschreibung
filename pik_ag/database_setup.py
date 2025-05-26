import sqlite3
import hashlib
from datetime import datetime

def create_database():
    """
    Creates SQLite database structure matching your PDF extraction data
    Also updates existing databases to add missing columns
    """
    conn = sqlite3.connect('product_cache.db')
    cursor = conn.cursor()
    
    print("Creating/updating database for your PDF extraction data...")
    
    # Table 1: Cache your PDF extractions to avoid re-processing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extraction_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oz_number TEXT,
            description_hash TEXT UNIQUE,
            original_description TEXT NOT NULL,
            menge TEXT,
            scraped_brand TEXT,
            scraped_product_name TEXT,
            scraped_product_description TEXT,
            scraped_price TEXT,
            standard_category TEXT DEFAULT 'Other',
            confidence_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 🆕 CHECK AND ADD MISSING COLUMNS TO EXISTING TABLES
    # Get current columns in extraction_cache table
    cursor.execute("PRAGMA table_info(extraction_cache)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    # Add standard_category column if it doesn't exist
    if 'standard_category' not in existing_columns:
        print("  ➕ Adding standard_category column to existing table...")
        cursor.execute('''
            ALTER TABLE extraction_cache 
            ADD COLUMN standard_category TEXT DEFAULT 'Other'
        ''')
        print("  ✅ standard_category column added")
    else:
        print("  ✅ standard_category column already exists")
    
    # Table 2: Store unique products found
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            brand TEXT,
            description TEXT,
            price TEXT,
            specifications TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Indexes for fast searching (CREATE IF NOT EXISTS handles duplicates)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_description_hash ON extraction_cache (description_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_brand ON extraction_cache (scraped_brand)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON extraction_cache (standard_category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON products (product_name)')
    
    # 🆕 VERIFY DATABASE STRUCTURE
    print("\n📊 Final database structure:")
    cursor.execute("PRAGMA table_info(extraction_cache)")
    columns = cursor.fetchall()
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        col_default = col[4] if col[4] else "None"
        print(f"  • {col_name} ({col_type}) - Default: {col_default}")
    
    # Count existing entries
    cursor.execute("SELECT COUNT(*) FROM extraction_cache")
    cache_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products")
    products_count = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Database setup completed!")
    print(f"📁 Database file: product_cache.db")
    print(f"📊 Cached extractions: {cache_count}")
    print(f"📦 Unique products: {products_count}")

def create_description_hash(oz_number, description, menge=""):
    """
    Create unique hash for your PDF extraction data
    """
    normalized = f"{oz_number}_{description.lower().strip()}_{menge.lower().strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

def check_database_health():
    """
    Check if database is properly set up with all required columns
    """
    try:
        conn = sqlite3.connect('product_cache.db')
        cursor = conn.cursor()
        
        print("🔍 Checking database health...")
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = ['extraction_cache', 'products']
        for table in required_tables:
            if table in tables:
                print(f"  ✅ Table '{table}' exists")
            else:
                print(f"  ❌ Table '{table}' missing")
                return False
        
        # Check if required columns exist in extraction_cache
        cursor.execute("PRAGMA table_info(extraction_cache)")
        columns = [column[1] for column in cursor.fetchall()]
        
        required_columns = [
            'id', 'oz_number', 'description_hash', 'original_description',
            'menge', 'scraped_brand', 'scraped_product_name', 
            'scraped_product_description', 'scraped_price', 'standard_category'
        ]
        
        missing_columns = []
        for col in required_columns:
            if col in columns:
                print(f"  ✅ Column '{col}' exists")
            else:
                print(f"  ❌ Column '{col}' missing")
                missing_columns.append(col)
        
        conn.close()
        
        if missing_columns:
            print(f"\n⚠️  Missing columns: {missing_columns}")
            print("📝 Run database_setup.py again to fix missing columns")
            return False
        else:
            print("\n✅ Database is healthy!")
            return True
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

if __name__ == "__main__":
    # First create/update the database
    create_database()
    
    print("\n" + "="*50)
    
    # Then check if everything is properly set up
    check_database_health()
    
    print("\n" + "="*50)
    
    # Test hash function
    test_hash = create_description_hash("01.02.2024", "Wireless headphones Sony", "5 Stk")
    print(f"🧪 Test hash: {test_hash}")
    
    print("\n💡 You can now run your main script!")