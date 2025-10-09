#!/usr/bin/env python3
"""
Quick test script to verify database connection works correctly.
This script tests both the development and production database connection logic.
"""

import psycopg2
from database import get_database_url, get_connection_params

def test_connection():
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    
    try:
        db_url = get_database_url()
        print(f"\n✓ Successfully retrieved database URL")
        print(f"  Connection string format: postgresql://...")
        
        params = get_connection_params()
        print(f"\n✓ Successfully retrieved connection parameters")
        print(f"  Host: {params['host']}")
        print(f"  Port: {params['port']}")
        print(f"  Database: {params['database']}")
        print(f"  User: {params['user']}")
        
        print(f"\n→ Testing actual database connection...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]
        print(f"\n✓ Successfully connected to database!")
        print(f"  PostgreSQL version: {db_version[:50]}...")
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n✓ Found {len(tables)} existing table(s):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print(f"\n✓ Database is empty (no tables yet)")
            print(f"  This is normal for a fresh database.")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Database is ready to use!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        print("\n" + "=" * 60)
        print("✗ TEST FAILED")
        print("=" * 60)
        raise

if __name__ == "__main__":
    test_connection()
