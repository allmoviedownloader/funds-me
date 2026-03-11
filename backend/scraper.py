import os
import re
import json
import logging
import requests
from datetime import datetime
import socket
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

load_dotenv()

# --- PATCH FOR FORCING IPv4 ---
orig_getaddrinfo = socket.getaddrinfo
def patched_getaddrinfo(*args, **kwargs):
    res = orig_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET]
socket.getaddrinfo = patched_getaddrinfo

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    {"name": "100X.VC", "url": "https://www.100x.vc/", "type": "portal"},
    {"name": "Antler", "url": "https://www.antler.co/india", "type": "portal"},
    {"name": "Google for Startups", "url": "https://startup.google.com/accelerator/", "type": "portal"},
    {"name": "LetsVenture", "url": "https://letsventure.com/", "type": "portal"},
    {"name": "AngelList India", "url": "https://www.angellistindia.com/", "type": "portal"},
    {"name": "Venture Catalysts", "url": "https://venturecatalysts.in/", "type": "portal"},
    {"name": "ah! Ventures", "url": "https://www.ahventures.in/", "type": "portal"},
    {"name": "Ketto", "url": "https://www.ketto.org/", "type": "portal"},
    {"name": "ImpactGuru", "url": "https://www.impactguru.com/", "type": "portal"},
    {"name": "Pepcorns", "url": "https://www.pepcorns.com/", "type": "portal"},
    {"name": "Invest India", "url": "https://www.investindia.gov.in/social-impact-funding", "type": "portal"},
    {"name": "CSR Box", "url": "https://csrbox.org/list-NGO-grants-India", "type": "portal"},
    {"name": "StartupHub Bengal", "url": "https://startuphub.wb.gov.in/", "type": "portal"},
    {"name": "Kerala Startup Mission", "url": "https://startupmission.kerala.gov.in/schemes", "type": "portal"},
    {"name": "Karnataka Startup", "url": "https://startup.karnataka.gov.in/", "type": "portal"},
    {"name": "NITI Aayog AIM", "url": "https://aim.gov.in/challenges.php", "type": "portal"},
    {"name": "MSME Idea Hackathon", "url": "https://my.msme.gov.in/incubation/", "type": "portal"},
    {"name": "T-Hub Hyderabad", "url": "https://t-hub.co/programs/", "type": "portal"},
    {"name": "iCreate Gujarat", "url": "https://icreate.org.in/", "type": "portal"},
    {"name": "HDFC SmartUp", "url": "https://www.hdfcbank.com/personal/useful-links/smartup-for-startups", "type": "portal"},
    {"name": "YES Bank ScaleUp", "url": "https://www.yesbank.in/business-banking/startup-banking", "type": "portal"}
]

SEARCH_QUERIES = [
    "latest startup grants India March 2025 news",
    "government innovation challenges India 2025",
    "startup accelerators accepting global applications 2025",
    "CSR funding announcements for startups India 2025",
    "fresh equity free funding for AI startups 2025",
    "Ministry of Electronics seed fund schemes 2025",
    "Agriculture startup funding India 2025 fresh",
    "Healthcare innovation grants India 2025",
    "Clean energy startup funds 2025 global",
    "EdTech startup grants India 2025 announced",
    "site:linkedin.com 'startup competition' 2025 India",
    "site:twitter.com 'startup grant' 2025 India",
    "Latest incubator intake 2025 India news",
    "Fintech grants Africa 2025",
    "EU innovation grants for AI startups 2025",
    "Singapore startup funding news 2025",
    "UAE tech startup grants 2025",
    "Global climate tech funding announcements March 2025",
    "Female founder grants 2025 global",
    "Deep tech research grants 2025",
    "Social entrepreneurship funding India 2025",
    "Biotech startup seed rounds 2025 news",
    "Web3 and blockchain startup grants 2025",
    "Robotics innovation challenge 2025",
    "SpaceTech startup funding rounds 2025"
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
    - company_name: Name of the startup, fund, or Challenge Program.
    - funding_stage: Idea Stage, Seed, Grant, Series A, Series B & C, or Bridge/Pre-IPO.
    - amount_offered: Amount (e.g. ₹50 Lakhs, $100k, Undisclosed).
    - investor: Government Ministry, VC, or Organization providing funds.
    - eligibility: 1 sentence description of who can apply.
    - challenge_info: If this is a 'Challenge' or 'Hackathon', describe the specific problem statement or goal (e.g., 'Solving waste management in smart cities').
    - category: Government Funds, Private Seed Funds, Series A, Series B & C, Bridge/Pre-IPO, Idea Stage, or Others.
    - apply_link: Official apply URL. Default to {source_url}.
    - release_date: YYYY-MM-DD (Date when the fund was announced or posted) or null.
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
            # Check for existing
            res = requests.post(insert_url, json=fund, headers=SUPABASE_HEADERS, timeout=10)
            if res.status_code in [200, 201]:
                logging.info(f"✅ Sync Successful: {fund.get('company_name')[:25]}")
            else:
                # Often fails due to duplicate name if unique constraint is on, which is fine
                logging.debug(f"Sync Skip/Fail ({res.status_code}): {fund.get('company_name')}")
        except Exception as e:
            logging.error(f"❌ Network Error: {e}")

def main():
    logging.info("\U0001f680 STARTING MASSIVE SCALE SCRAPE...")
    cleanup_expired_funds()
    
    # 1. Scrape standard targets
    for target in TARGETS:
        text = fetch_page_text(target["url"])
        if text:
            extracted = process_text_with_gemini(text, target["name"], target["url"])
            if extracted:
                push_to_supabase(extracted)
        time.sleep(2)

    # 2. Scrape Search Queries for massive volume
    for query in SEARCH_QUERIES:
        logging.info(f"\U0001f50d Searching for: {query}")
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=nws"
        text = fetch_page_text(search_url)
        if text:
            extracted = process_text_with_gemini(text, "Web Search", search_url)
            if extracted:
                push_to_supabase(extracted)
        time.sleep(5)
    
    logging.info("\u2728 MASSIVE SCALE JOB FINISHED")

if __name__ == "__main__":
    main()
