import os
import re
import json
import logging
import requests
from datetime import datetime
import socket
from bs4 import BeautifulSoup
import time

# --- PATCH FOR FORCING IPv4 ---
orig_getaddrinfo = socket.getaddrinfo
def patched_getaddrinfo(*args, **kwargs):
    res = orig_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET]
socket.getaddrinfo = patched_getaddrinfo

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyD1eCR-MKcWPrhFg4gOLf0tCyMOLVV2E1w"
SUPABASE_URL = "https://ukeeqgbsvjsazoqqpmxu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrZWVxZ2JzdmpzYXpvcXFwbXh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwODIyNjYsImV4cCI6MjA4ODY1ODI2Nn0.tNPM0LQ2JSkHpBh-Gj-_8Q8StIsxSDXXdjca1b6cbbc"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

TARGETS = [
    {"name": "Inc42", "url": "https://inc42.com/category/funding/", "type": "news"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/category/startups/", "type": "news"},
    {"name": "Y Combinator", "url": "https://www.ycombinator.com/apply", "type": "portal"},
    {"name": "Techstars", "url": "https://www.techstars.com/accelerators", "type": "portal"},
    {"name": "Startup India", "url": "https://seedfund.startupindia.gov.in/", "type": "portal"},
    {"name": "BIRAC BIG", "url": "https://birac.nic.in/desc_new.php?id=77", "type": "portal"},
    {"name": "MeitY Hub", "url": "https://meitystartuphub.in/schemes", "type": "portal"},
    {"name": "100X.VC", "url": "https://www.100x.vc/", "type": "portal"}
]

def fetch_page_text(url):
    logging.info(f"Crawling {url}...")
    try:
        # Better User-Agent to avoid 403s
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for elm in soup(["script", "style", "nav", "footer", "header", "aside"]): elm.extract()
        return re.sub(r'\s+', ' ', soup.get_text(strip=True))[:12000]
    except Exception as e:
        logging.error(f"Crawl Fail {url}: {e}")
        return None

def process_text_with_gemini(raw_text, source_name, source_url):
    logging.info(f"AI Analysing content from {source_name}...")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Extract startup funding, grants, or seed fund programs from the text below.
    Source: {source_name} ({source_url})
    
    JSON Fields:
    - company_name: Name of the startup or fund.
    - funding_stage: Idea Stage, Seed, Grant, Series A, Series B & C, or Bridge/Pre-IPO.
    - amount_offered: Amount (e.g. $100k, Undisclosed).
    - investor: Provided by.
    - eligibility: 1 sentence description.
    - category: Government Funds, Private Seed Funds, Series A, Series B & C, Bridge/Pre-IPO, Idea Stage, or Others.
    - apply_link: Official apply URL. Default to {source_url}.
    - deadline: YYYY-MM-DD or null.
    
    RETURN ONLY A CLEAN JSON ARRAY. NO MARKDOWN.
    ---
    TEXT:
    {raw_text}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
    }
    
    for attempt in range(3):
        try:
            res = requests.post(api_url, json=payload, timeout=30)
            res_json = res.json()
            
            if res.status_code == 429:
                logging.warning(f"Rate limited (429). Retrying in 5s (Attempt {attempt+1})...")
                time.sleep(5)
                continue

            if 'candidates' in res_json:
                result_text = res_json['candidates'][0]['content']['parts'][0]['text']
                return json.loads(result_text)
            else:
                logging.error(f"Gemini AI Response Invalid: {res_json}")
                return []
        except Exception as e:
            logging.error(f"AI Logic Fail: {e}")
            time.sleep(2)
    return []

def cleanup_expired_funds():
    today = datetime.now().strftime("%Y-%m-%d")
    logging.info(f"Cleaning up expired funds before {today}...")
    try:
        requests.delete(f"{SUPABASE_URL}/rest/v1/funds?deadline=lt.{today}", headers=SUPABASE_HEADERS, timeout=10)
    except: pass

def push_to_supabase(funds):
    if not funds: return
    insert_url = f"{SUPABASE_URL}/rest/v1/funds"
    for fund in funds:
        try:
            res = requests.post(insert_url, json=fund, headers=SUPABASE_HEADERS, timeout=10)
            if res.status_code in [200, 201]:
                logging.info(f"✅ Sync Successful: {fund.get('company_name')[:25]}")
            else:
                logging.error(f"❌ Sync Failed ({res.status_code}): {res.text}")
        except Exception as e:
            logging.error(f"❌ Network Error: {e}")

def main():
    logging.info("🚀 STARTING AUTOMATED SCRAPE...")
    cleanup_expired_funds()
    
    for target in TARGETS:
        text = fetch_page_text(target["url"])
        if text:
            extracted = process_text_with_gemini(text, target["name"], target["url"])
            if extracted:
                push_to_supabase(extracted)
            time.sleep(2) # Respectful delay
            
    logging.info("✨ JOB FINISHED")

if __name__ == "__main__":
    main()
