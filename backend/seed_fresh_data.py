import os, requests, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def generate_funds():
    funds = []
    # Mix of Govt, Seed, and Big Corps
    categories = ["Government Funds", "Private Seed Funds", "Big Companies"]
    investors = ["Startup India", "BIRAC", "NITI Aayog", "Google for Startups", "Microsoft Imagine", "Tata Trusts", "Reliance JioGenNext", "Sequoia Surge", "Y Combinator", "Antler India"]
    
    today = datetime.now()
    
    for i in range(50):
        stage = "Series B" if i % 3 == 0 else "Seed" if i % 2 == 0 else "Series A"
        cat = categories[i % 3]
        inv = investors[(i+5) % len(investors)]
        
        rel_date = (today - timedelta(days=i%10)).strftime("%Y-%m-%d")
        deadline = (today + timedelta(days=20 + i%30)).strftime("%Y-%m-%d")
        
        funds.append({
            "company_name": f"Strategic Growth Fund #{200+i} - {inv}",
            "funding_stage": stage,
            "amount_offered": f"₹{20 + i%80} Lakhs" if "India" in inv or "Tata" in inv else f"${100 + i%400}k",
            "investor": inv,
            "eligibility": "Tech-enabled startups with a minimum viable product and early traction.",
            "challenge_info": "Focusing on sustainability, fintech, or deep-tech solutions for Indian markets." if i % 4 == 0 else None,
            "category": cat,
            "apply_link": "https://example.com/apply",
            "release_date": rel_date,
            "deadline": deadline
        })
    return funds

def seed():
    data = generate_funds()
    print(f"Seeding {len(data)} entries...")
    res = requests.post(f"{SUPABASE_URL}/rest/v1/funds", json=data, headers=SUPABASE_HEADERS)
    print(f"Status: {res.status_code}")
    if res.status_code >= 400:
        print(f"Error: {res.text}")

if __name__ == "__main__":
    seed()
