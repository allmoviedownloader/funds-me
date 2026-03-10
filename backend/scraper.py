import os
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from datetime import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyC5RqzNZGAAXzlmcYNxEl98fI_5p7hLCY4"
SUPABASE_URL = "https://ukeeqgbsvjsazoqqpmxu.supabase.co"
# We use the anon key. If RLS is enabled on Supabase, the user might need to disable it or use service_role key.
# For this script we assume the Anon key has insert/delete privileges or RLS is disabled.
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrZWVxZ2JzdmpzYXpvcXFwbXh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwODIyNjYsImV4cCI6MjA4ODY1ODI2Nn0.tNPM0LQ2JSkHpBh-Gj-_8Q8StIsxSDXXdjca1b6cbbc"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Target URLs to scrape
TARGETS = [
    {
        "name": "Inc42 Funding News",
        "url": "https://inc42.com/category/funding/",
        "type": "news"
    },
    {
        "name": "YourStory Funding",
        "url": "https://yourstory.com/funding",
        "type": "news"
    },
    {
        "name": "Startup India Seed Fund",
        "url": "https://seedfund.startupindia.gov.in/",
        "type": "portal"
    }
]

# --- PHASE 1: THE CRAWLER ---
def fetch_page_text(url):
    """Fetches the HTML of a page and extracts clean text."""
    logging.info(f"Crawling {url}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts, styles, headers, footers to reduce noise
        for elm in soup(["script", "style", "nav", "footer", "header"]):
            elm.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        # Condense whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # We only return the first 15000 characters to avoid overflowing Gemini token limits
        return text[:15000]
    except Exception as e:
        logging.error(f"Failed to crawl {url}: {e}")
        return None

# --- PHASE 2: THE LOGIC GATE (AI) ---
def process_text_with_gemini(raw_text, source_name, source_url):
    """Passes raw text to Gemini and asks it to return a clean JSON array."""
    logging.info(f"Processing data from {source_name} with Gemini AI...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    You are an expert AI extraction tool. Your job is to read the following raw scraped text from '{source_name}' ({source_url}) and extract startup funding opportunities, grants, or seed funds.
    
    CRITICAL INSTRUCTIONS:
    - Output ONLY a valid Google JSON Array of objects. Do not include markdown formatting like ```json.
    - If no funding opportunities are found in the text, output an empty array [].
    - Standardize the data into this EXACT schema:
      - company_name: Name of the fund, program, or startup being funded (string)
      - funding_stage: E.g., "Idea Stage", "Seed", "Series A", "Grant", "Pre-Seed" (string)
      - amount_offered: E.g., "$100k", "Up to ₹50 Lakhs", "Grant-based" (string)
      - investor: Name of the investing body or government (string)
      - eligibility: Short 1-2 sentence description of who can apply (string)
      - category: MUST BE EXACTLY ONE OF: "Government Funds", "Private Seed Funds", "Series A", "Series B & C", "Bridge/Pre-IPO", "Idea Stage", or "Others".
      - apply_link: The official URL to apply. If not explicitly found, use the source URL: {source_url}
      - deadline: The application deadline in "YYYY-MM-DD" format. If unknown or ongoing, output null.
      
    RAW TEXT TO PROCESS:
    {raw_text}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        
        data = response.json()
        result_text = data['candidates'][0]['content']['parts'][0]['text']
        
        # Parse JSON
        funds = json.loads(result_text)
        if isinstance(funds, list):
             return funds
        else:
             logging.warning("Gemini did not return a list.")
             return []
    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        return []

# --- PHASE 3: DATABASE SYNC & CLEANUP ---
def cleanup_expired_funds():
    """Deletes entries from Supabase where the deadline has passed."""
    logging.info("Cleaning up expired funds from Supabase...")
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Delete where deadline is less than today
        # Supabase Python client syntax for delete:
        res = supabase.table("funds").delete().lt("deadline", today).execute()
        logging.info(f"Cleanup complete. Deleted {len(res.data)} expired entries.")
    except Exception as e:
         logging.error(f"Failed to cleanup old funds: {e}")

def push_to_supabase(funds):
    """Pushes extracted funds into Supabase."""
    if not funds:
         return
         
    logging.info(f"Pushing {len(funds)} records to Supabase...")
    for fund in funds:
        # Prepare payload
        payload = {
            "company_name": fund.get("company_name"),
            "funding_stage": fund.get("funding_stage"),
            "amount_offered": fund.get("amount_offered"),
            "investor": fund.get("investor"),
            "eligibility": fund.get("eligibility"),
            "category": fund.get("category"),
            "apply_link": fund.get("apply_link"),
            "deadline": fund.get("deadline")
        }
        
        try:
             # Basic duplicate check strategy could be upserting based on apply_link, 
             # but here we just insert. A unique constraint on Supabase is recommended.
             supabase.table("funds").insert(payload).execute()
             logging.info(f"✅ Inserted: {payload['company_name']}")
        except Exception as e:
             logging.error(f"❌ Failed to insert {payload.get('company_name')}: {e}")

# --- MAIN EXECUTION ---
def main():
    logging.info("🚀 Starting Automated Funding Scraper...")
    
    # Run Cleanup first
    cleanup_expired_funds()
    
    total_funds_extracted = []
    
    for target in TARGETS:
        raw_text = fetch_page_text(target["url"])
        if raw_text:
             funds = process_text_with_gemini(raw_text, target["name"], target["url"])
             total_funds_extracted.extend(funds)
             
    logging.info(f"🎯 Total funds extracted across all sources: {len(total_funds_extracted)}")
    
    # Push to Database
    push_to_supabase(total_funds_extracted)
    
    logging.info("✅ Scraper cycle finished successfully!")

if __name__ == "__main__":
    main()
