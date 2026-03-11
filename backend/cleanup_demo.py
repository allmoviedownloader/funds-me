import os, requests
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

def clean_all_demos():
    print("Clearing all demo patterns...")
    patterns = ["Strategic Growth%", "Fresh Opportunity%", "Premium Strategic%", "Fresh Opportunity%"]
    
    for pattern in patterns:
        url = f"{SUPABASE_URL}/rest/v1/funds?company_name=ilike.{pattern}"
        res = requests.delete(url, headers=SUPABASE_HEADERS)
        print(f"Pattern '{pattern}' Cleanup: {res.status_code}")

if __name__ == "__main__":
    clean_all_demos()
