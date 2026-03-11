import os, requests
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

def clean_demo():
    url = f"{SUPABASE_URL}/rest/v1/funds?company_name=ilike.Strategic%20Growth%20Fund*"
    res = requests.delete(url, headers=SUPABASE_HEADERS)
    print(f"Strategic Growth Cleanup: {res.status_code}")
    
    url2 = f"{SUPABASE_URL}/rest/v1/funds?company_name=ilike.Fresh%20Opportunity*"
    res2 = requests.delete(url2, headers=SUPABASE_HEADERS)
    print(f"Fresh Opportunity Cleanup: {res2.status_code}")

if __name__ == "__main__":
    clean_demo()
