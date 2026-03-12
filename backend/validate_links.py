import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def get_all_funds():
    url = f"{SUPABASE_URL}/rest/v1/funds?select=id,apply_link"
    res = requests.get(url, headers=SUPABASE_HEADERS)
    return res.json() if res.status_code == 200 else []

def validate_links():
    logging.basicConfig(level=logging.INFO)
    funds = get_all_funds()
    logging.info(f"Checking {len(funds)} links...")
    
    to_delete = []
    for f in funds:
        link = f.get('apply_link')
        if not link:
            to_delete.append(f['id'])
            continue
            
        try:
            res = requests.head(link, timeout=10, allow_redirects=True)
            if res.status_code >= 404:
                logging.warning(f"Broken: {link} (Status: {res.status_code})")
                to_delete.append(f['id'])
        except Exception as e:
            logging.error(f"Error checking {link}: {e}")
            
    if to_delete:
        logging.info(f"Deleting {len(to_delete)} broken entries...")
        for fid in to_delete:
            requests.delete(f"{SUPABASE_URL}/rest/v1/funds?id=eq.{fid}", headers=SUPABASE_HEADERS)
    else:
        logging.info("All links are healthy!")

if __name__ == "__main__":
    validate_links()
