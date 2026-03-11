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
    {"name": "Inc42 Funding", "url": "https://inc42.com/category/funding/", "type": "news"},
    {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/", "type": "news"},
    {"name": "Tech in Asia Funding", "url": "https://www.techinasia.com/tag/funding", "type": "news"},
    {"name": "Sifted Europe", "url": "https://sifted.eu/funding", "type": "news"},
    {"name": "Y Combinator", "url": "https://www.ycombinator.com/apply", "type": "portal"},
    {"name": "Techstars Global", "url": "https://www.techstars.com/accelerators", "type": "portal"},
    {"name": "Startup India", "url": "https://seedfund.startupindia.gov.in/", "type": "portal"},
    {"name": "F6S Programs", "url": "https://www.f6s.com/programs", "type": "portal"},
    {"name": "Pioneer.app", "url": "https://pioneer.app/", "type": "portal"},
    {"name": "AngelList Global", "url": "https://www.angellist.com/blog", "type": "news"},
    {"name": "BIRAC BIG", "url": "https://birac.nic.in/desc_new.php?id=77", "type": "portal"},
    {"name": "Antler Global", "url": "https://www.antler.co/", "type": "portal"},
    {"name": "Google for Startups", "url": "https://startup.google.com/accelerator/", "type": "portal"},
    {"name": "MeitY Hub", "url": "https://meitystartuphub.in/schemes", "type": "portal"},
    {"name": "Invest India", "url": "https://www.investindia.gov.in/social-impact-funding", "type": "portal"},
    {"name": "CSR Box", "url": "https://csrbox.org/list-NGO-grants-India", "type": "portal"},
    {"name": "MIT Innovation", "url": "https://innovation.mit.edu/opportunities/", "type": "portal"},
    {"name": "Stanford Startup Garage", "url": "https://www.gsb.stanford.edu/programs/startup-garage", "type": "portal"},
    {"name": "Oxford Seed Fund", "url": "https://www.sbs.ox.ac.uk/oxford-seed-fund", "type": "portal"},
    {"name": "Harvard Innovation Labs", "url": "https://innovationlabs.harvard.edu/", "type": "portal"},
    {"name": "UN Innovation Hub", "url": "https://innovation.un.org/", "type": "portal"},
    {"name": "World Bank SIEF", "url": "https://www.worldbank.org/en/programs/sief-trust-fund", "type": "portal"},
    {"name": "Horizon Europe", "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home", "type": "portal"},
    {"name": "Crunchbase Funding News", "url": "https://news.crunchbase.com/category/funding/", "type": "news"}
]

SEARCH_QUERIES = [
    "latest startup grants global March 2025 news",
    "worldwide innovation challenges 2025 open to all",
    "equity free funding global startups 2025",
    "UN innovation grants 2025 worldwide",
    "EU Horizon Europe grants global participation 2025",
    "USAID innovation challenges worldwide 2025",
    "Bill & Melinda Gates Foundation grants 2025",
    "Google for Startups global programs 2025 news",
    "Microsoft for Startups global benefits 2025",
    "AWS Activate credits and grants global 2025",
    "Founders Institute global intake 2025",
    "Pioneer.app global winners news 2025",
    "Antler global residency intake 2025",
    "Entrepreneur First global application 2025",
    "Techstars global accelerators deadline 2025",
    "Y Combinator global applications 2025 news",
    "Fintech grants worldwide 2025 news",
    "Climate tech grants global 2025",
    "Healthcare innovation challenges global 2025",
    "Social impact grants worldwide 2025",
    "site:f6s.com 'open for applications' 2025",
    "site:pioneer.app 'apply' 2025",
    "site:angel.co 'funding' 2025 global",
    "site:techcrunch.com 'grant' 2025 worldwide",
    "site:sifted.eu 'funding' 2025 global"
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
    CRITICAL: Verify if the program is "Global/Worldwide" or "Open to Indian Founders". 
    If it is restricted to a specific non-India country (e.g. "US Residents Only"), EXCLUDE it unless it's a major global program.
    Source: {source_name} ({source_url})
    
    JSON Fields:
    - company_name: Name of the startup, fund, or Challenge Program.
    - funding_stage: Idea Stage, Seed, Grant, Series A, Series B & C, or Bridge/Pre-IPO.
    - amount_offered: Amount (e.g. ₹50 Lakhs, $100k, Undisclosed).
    - investor: Government Ministry, VC, or Organization providing funds.
    - eligibility: 1-2 sentence description. MUST EXPLICITLY mention "Open to Indian Founders" or "Worldwide" if confirmed.
    - challenge_info: If this is a 'Challenge' or 'Hackathon', describe the specific problem statement.
    - category: Government Funds, Private Seed Funds, Series A, Series B & C, Bridge/Pre-IPO, Idea Stage, or Others.
    - apply_link: Official apply URL. Default to {source_url}.
    - release_date: YYYY-MM-DD (Announcement date) or null.
    - deadline: YYYY-MM-DD HH:MM:SS or null. (Use the end of the day if time not specified).
    
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
                logging.warning(f"Rate limited (429). Retrying in 10s (Attempt {attempt+1})...")
                time.sleep(10)
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
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Cleaning up expired funds before {now_ts}...")
    try:
        # Using Supabase delete with filter for expired deadlines
        requests.delete(f"{SUPABASE_URL}/rest/v1/funds?deadline=lt.{now_ts}", headers=SUPABASE_HEADERS, timeout=10)
    except Exception as e:
        logging.error(f"Cleanup Error: {e}")

def push_to_supabase(funds):
    if not funds: return
    insert_url = f"{SUPABASE_URL}/rest/v1/funds"
    for fund in funds:
        try:
            # Check for existing
            res = requests.post(insert_url, json=fund, headers=SUPABASE_HEADERS, timeout=10)
            if res.status_code in [200, 201]:
                logging.info(f"Sync Successful: {fund.get('company_name')[:25]}")
            else:
                logging.debug(f"Sync Skip/Fail ({res.status_code}): {fund.get('company_name')}")
        except Exception as e:
            logging.error(f"Network Error: {e}")

def run_task():
    logging.info("--- STARTING SCHEDULED SCRAPE TASK ---")
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
        logging.info(f"Searching for: {query}")
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=nws"
        text = fetch_page_text(search_url)
        if text:
            extracted = process_text_with_gemini(text, "Web Search", search_url)
            if extracted:
                push_to_supabase(extracted)
        time.sleep(5)
    
    logging.info("--- SCHEDULED TASK FINISHED ---")

def main():
    # If running manually, it runs once. 
    # To run every 12 hours on a server, use:
    # while True:
    #     run_task()
    #     time.sleep(12 * 3600)
    run_task()

if __name__ == "__main__":
    main()
