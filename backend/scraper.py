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
    {"name": "Startup India Official", "url": "https://www.startupindia.gov.in/content/sih/en/search.html?type=scheme", "type": "portal"},
    {"name": "MeitY Startup Hub", "url": "https://meitystartuphub.in/schemes", "type": "portal"},
    {"name": "BIRAC Projects", "url": "https://birac.nic.in/desc_new.php?id=77", "type": "portal"},
    {"name": "Ministry of MSME", "url": "https://msme.gov.in/all-schemes", "type": "portal"},
    {"name": "Invest India Social", "url": "https://www.investindia.gov.in/social-impact-funding", "type": "portal"},
    {"name": "DST NIDHI PRAYAS", "url": "https://nidhi-prayas.org/", "type": "portal"},
    {"name": "AGNIi India", "url": "https://www.agnii.gov.in/innovation-challenges", "type": "portal"},
    {"name": "TDB India", "url": "http://tdb.gov.in/grants/", "type": "portal"},
    {"name": "Atal Innovation Mission", "url": "https://aim.gov.in/anic.php", "type": "portal"},
    {"name": "India Science Tech", "url": "https://www.indiascienceandtechnology.gov.in/startup-grants", "type": "portal"},
    {"name": "UN Innovation Hub", "url": "https://innovation.un.org/", "type": "portal"},
    {"name": "UNICEF Innovation", "url": "https://www.unicef.org/innovation/apply-funding", "type": "portal"},
    {"name": "UNESCO IFCD", "url": "https://en.unesco.org/creativity/ifcd/apply", "type": "portal"},
    {"name": "World Bank Grants", "url": "https://www.worldbank.org/en/about/working-with-us/grants", "type": "portal"},
    {"name": "Horizon Europe", "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home", "type": "portal"},
    {"name": "USAID Challenges", "url": "https://www.usaid.gov/innovation-technology-research-hub/challenges", "type": "portal"},
    {"name": "Grand Challenges", "url": "https://grandchallenges.org/grant-opportunities", "type": "portal"},
    {"name": "MassChallenge Global", "url": "https://masschallenge.org/apply/", "type": "portal"},
    {"name": "Thiel Fellowship", "url": "https://thielfellowship.org/", "type": "portal"},
    {"name": "Y Combinator", "url": "https://www.ycombinator.com/apply", "type": "portal"},
    {"name": "Techstars Accelerators", "url": "https://www.techstars.com/accelerators", "type": "portal"},
    {"name": "MIT Water Prize", "url": "https://www.mitwaterprize.org/", "type": "portal"},
    {"name": "Stanford Startup Garage", "url": "https://www.gsb.stanford.edu/programs/startup-garage", "type": "portal"},
    {"name": "Oxford Seed Fund", "url": "https://www.sbs.ox.ac.uk/oxford-seed-fund", "type": "portal"},
    {"name": "Harvard Allston fund", "url": "https://innovationlabs.harvard.edu/allston-venture-fund", "type": "portal"},
    {"name": "Berkeley SkyDeck", "url": "https://skydeck.berkeley.edu/apply/", "type": "portal"},
    {"name": "Accelerating Asia", "url": "https://www.acceleratingasia.com/apply", "type": "portal"},
    {"name": "Antler Global", "url": "https://www.antler.co/apply", "type": "portal"},
    {"name": "500 Global", "url": "https://500.co/accelerators", "type": "portal"},
    {"name": "Founders Institute", "url": "https://fi.co/apply", "type": "portal"},
    {"name": "Crunchbase Funding", "url": "https://news.crunchbase.com/category/funding/", "type": "news"},
    {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/", "type": "news"},
    {"name": "Sifted Europe", "url": "https://sifted.eu/funding", "type": "news"}
]

SEARCH_QUERIES = [
    "official government startup grants India 2025 news",
    "latest worldwide innovation challenges 2025 open for applications",
    "equity free funding global startups 2025 official portals",
    "UN innovation hub grants 2025 announcement",
    "EU Horizon Europe open calls March 2025",
    "USAID innovation challenges worldwide 2025 deadline",
    "Bill & Melinda Gates Foundation grants 2025 sectors",
    "Google for Startups AI grants global 2025",
    "Microsoft for Startups founders hub benefits 2025",
    "AWS Activate credits and grants global 2025 official",
    "Pioneer.app global winners news 2025 March",
    "Antler global residency next intake 2025",
    "Techstars global accelerators upcoming deadlines 2025",
    "Y Combinator Summer 2025 application status",
    "India DPIIT recognized startup benefits 2025",
    "Startup India Seed Fund approved incubators list 2025",
    "MeitY SAMRIDH scheme intake 2025",
    "BIRAC BIG grant 25th call 2025",
    "Climate tech grants global 2025 official lists",
    "Healthcare innovation challenges worldwide 2025 March",
    "Social impact grants global founders 2025",
    "site:f6s.com 'open for applications' 2025 global",
    "site:startupindia.gov.in 'grant' 2025",
    "site:innovation.gov 'funding' 2025",
    "site:sciencedirect.com 'funding opportunity' 2025"
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
    CRITICAL: 
    1. Verify if the program is "Global/Worldwide" or "Open to Indian Founders".
    2. FIND THE DIRECT APPLICATION LINK. If the text mentions a link like 'apply here' or 'portal', extract that.
    3. If you CANNOT find a direct official application URL, set 'apply_link' to null. 
    4. DO NOT use news article links (e.g. techcrunch.com/article...) as 'apply_link'.
    5. If a program is restricted to a specific non-India country (e.g. "US Residents Only"), EXCLUDE it.
    
    Source: {source_name}
    
    JSON Fields:
    - company_name: Name of the startup, fund, or Challenge Program.
    - funding_stage: Idea Stage, Seed, Grant, Series A, Series B & C, or Bridge/Pre-IPO.
    - amount_offered: Amount (e.g. ₹50 Lakhs, $100k, Undisclosed).
    - investor: Government Ministry, VC, or Organization providing funds.
    - eligibility: 1-2 sentence description. MUST EXPLICITLY mention "Open to Indian Founders" or "Worldwide" if confirmed.
    - challenge_info: Describe the specific problem statement.
    - category: Government Funds, Private Seed Funds, Series A, Series B & C, Bridge/Pre-IPO, Idea Stage, or Others.
    - apply_link: DIRECT OFFICIAL APPLY URL or null.
    - release_date: YYYY-MM-DD or null.
    - deadline: YYYY-MM-DD HH:MM:SS or null.
    
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
            # Final Validation: Skip if no direct link
            if not fund.get('apply_link') or "http" not in fund.get('apply_link'):
                continue
                
            # Quick 404 Check
            try:
                check = requests.head(fund['apply_link'], timeout=5, allow_redirects=True)
                if check.status_code >= 400:
                    logging.warning(f"Skipping Broken Link ({check.status_code}): {fund['apply_link']}")
                    continue
            except:
                pass # Proceed if head request fails for non-critical reasons
                
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
    # To run as a persistent background service, set AUTO_SCRAPE=true
    auto_mode = os.getenv("AUTO_SCRAPE", "false").lower() == "true"
    
    if auto_mode:
        logging.info("=== AUTOMATED 12H MODE ACTIVATED ===")
        while True:
            try:
                run_task()
            except Exception as e:
                logging.error(f"Loop Error: {e}")
            logging.info("Sleeping for 12 hours...")
            time.sleep(12 * 3600)
    else:
        run_task()

if __name__ == "__main__":
    main()
