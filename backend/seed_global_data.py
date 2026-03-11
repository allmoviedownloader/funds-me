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

def generate_global_funds():
    funds = []
    # Mix of established global accelerators and news patterns
    investors = [
        "F6S Global", "Y Combinator", "Techstars Worldwide", "Pioneer.app", "Antler Global", 
        "Founder Institute", "Entrepreneur First", "500 Global", "Sequoia Surge Global", 
        "Google for Startups", "Microsoft Imagine Cup", "AWS Global Fintech Accelerator",
        "UN Innovation Hub", "USAID Global Grants", "Bill & Melinda Gates Foundation"
    ]
    categories = ["Government Funds", "Private Seed Funds", "Big Companies", "Idea Stage"]
    
    today = datetime.now()
    
    for i in range(180):
        inv = investors[i % len(investors)]
        cat = categories[i % 4]
        stage = "Idea Stage" if i % 3 == 0 else "Seed" if i % 2 == 0 else "Grant"
        
        rel_date = (today - timedelta(days=i%30)).strftime("%Y-%m-%d")
        deadline = (today + timedelta(days=60 + i%90)).strftime("%Y-%m-%d")
        
        funds.append({
            "company_name": f"Global Innovation Award #{300+i} - {inv}",
            "funding_stage": stage,
            "amount_offered": f"${50 + i%500}k" if "Global" in inv else f"₹{10 + i%50} Lakhs",
            "investor": inv,
            "eligibility": "Worldwide founders. Tech-focused startups solving scalable global problems.",
            "category": cat,
            "apply_link": "https://www.f6s.com/search/programs",
            "release_date": rel_date,
            "deadline": deadline
        })
    return funds

def seed():
    data = generate_global_funds()
    print(f"Seeding {len(data)} global entries...")
    # Batch into groups of 50 to avoid any size limits
    for i in range(0, len(data), 50):
        batch = data[i:i+50]
        res = requests.post(f"{SUPABASE_URL}/rest/v1/funds", json=batch, headers=SUPABASE_HEADERS)
        print(f"Batch {i//50 + 1} Status: {res.status_code}")

if __name__ == "__main__":
    seed()
