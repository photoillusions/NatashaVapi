import os
import json
from datetime import datetime
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"❌ Supabase Connection Error: {e}")

def get_customer(phone):
    """Retrieve customer details from Supabase by phone number."""
    if not phone or not supabase:
        return None
    
    # Clean phone number
    clean_phone = str(phone).replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if len(clean_phone) == 10:
        clean_phone = "1" + clean_phone
    
    try:
        response = supabase.table("customers").select("*").eq("phone", clean_phone).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"❌ Supabase Select Error: {e}")
    
    return None

def upsert_customer(phone, data):
    """Create or update a customer record in Supabase."""
    if not phone or not supabase:
        return False
    
    clean_phone = str(phone).replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if len(clean_phone) == 10:
        clean_phone = "1" + clean_phone
        
    now = datetime.now().isoformat()
    
    # Prepare payload
    payload = {
        "phone": clean_phone,
        "updated_at": now
    }
    
    # Add optional fields from data
    for key, value in data.items():
        if value is not None:
            payload[key] = str(value)

    if "created_at" not in payload:
        # We don't want to overwrite created_at if it's an update, 
        # but Supabase handles this via DEFAULT if we use upsert correctly
        pass

    try:
        # Upsert: if phone matches, it updates; otherwise, it inserts
        supabase.table("customers").upsert(payload, on_conflict="phone").execute()
        return True
    except Exception as e:
        print(f"❌ Supabase Upsert Error: {e}")
        return False

def format_history_for_prompt(customer):
    """Format customer data into a string for the AI's system prompt."""
    if not customer:
        return ""
    
    history = f"\n## 👤 CUSTOMER HISTORY ##\n"
    history += f"- **Name:** {customer.get('name', 'N/A')}\n"
    history += f"- **Email:** {customer.get('email', 'N/A')}\n"
    
    if customer.get('last_payment_amount'):
        history += f"- **Last Payment:** ${customer.get('last_payment_amount')} on {customer.get('last_payment_date', 'N/A')}\n"
    
    if customer.get('event_type') and customer.get('venue'):
        history += f"- **Previous Interest:** {customer.get('event_type')} at {customer.get('venue')} on {customer.get('event_date', 'N/A')}\n"
    
    if customer.get('notes'):
        history += f"- **Notes:** {customer.get('notes')}\n"
        
    history += "**Jessica:** Greet them as a returning customer and reference their previous details naturally.\n"
    return history
