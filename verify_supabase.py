import os
from supabase import create_client, Client

# Set these temporarily for testing or use your .env/Render vars
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

def test_connection():
    if not URL or not KEY:
        print("❌ Error: SUPABASE_URL or SUPABASE_KEY missing from environment.")
        return

    print(f"Connecting to {URL}...")
    try:
        supabase: Client = create_client(URL, KEY)
        # Try to fetch count from customers table
        response = supabase.table("customers").select("count", count="exact").limit(0).execute()
        print("✅ Success! Successfully connected and found 'customers' table.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nMake sure you have:")
        print("1. Run the SQL script in the Supabase SQL Editor.")
        print("2. Provided the correct Project URL (NOT the dashboard URL).")

if __name__ == "__main__":
    test_connection()
