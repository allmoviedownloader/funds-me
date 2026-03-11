import os, requests, json, time
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

def generate_massive_dataset():
    funds = []
    
    # --- DATA SOURCES ---
    universities = [
        {"name": "MIT E14 Fund", "cat": "Private Seed Funds", "elig": "MIT students and alumni globally."},
        {"name": "Stanford Startup Garage", "cat": "Idea Stage", "elig": "Stanford interdisciplinary teams."},
        {"name": "Oxford Seed Fund", "cat": "Private Seed Funds", "elig": "Oxford-affiliated founders worldwide."},
        {"name": "Harvard Allston Venture Fund", "cat": "Private Seed Funds", "elig": "Harvard student-led ventures."},
        {"name": "IIT Kanpur SIIC", "cat": "Government Funds", "elig": "Indian tech startups and innovators."},
        {"name": "Berkeley SkyDeck", "cat": "Private Seed Funds", "elig": "Global startups with Berkeley affiliation."},
        {"name": "ETH Zurich IE Lab", "cat": "Private Seed Funds", "elig": "High-tech spin-offs from ETH."},
        {"name": "NUS BLOCK71", "cat": "Idea Stage", "elig": "Southeast Asian founders and NUS alumni."},
        {"name": "Cambridge Enterprise", "cat": "Private Seed Funds", "elig": "Cambridge University members."},
        {"name": "Yale Tsai CITY", "cat": "Idea Stage", "elig": "Yale students across all disciplines."},
        {"name": "INSEAD LaunchPad", "cat": "Idea Stage", "elig": "INSEAD alumni and students."},
        {"name": "Tsinghua x-lab", "cat": "Idea Stage", "elig": "Tsinghua students and researchers."},
        {"name": "IIT Madras Pravartak", "cat": "Government Funds", "elig": "Deep tech startups in India."},
        {"name": "IIT Roorkee TIDES", "cat": "Government Funds", "elig": "Early-stage tech startups."},
        {"name": "London Business School Incubator", "cat": "Private Seed Funds", "elig": "LBS students/alumni."},
        {"name": "Columbia Brown Institute", "cat": "Big Companies", "elig": "Media technology innovation grants."},
        {"name": "Singapore SMART Grant", "cat": "Big Companies", "elig": "Deep tech prototypes in Singapore."},
    ]
    
    global_grants = [
        {"name": "UN Innovation Hub", "cat": "Government Funds", "elig": "Global startups solving UN SDGs."},
        {"name": "World Bank SIEF", "cat": "Government Funds", "elig": "Technology solutions for education."},
        {"name": "UNESCO IFCD", "cat": "Government Funds", "elig": "Creative sectors in the global South."},
        {"name": "Bill & Melinda Gates Foundation", "cat": "Big Companies", "elig": "Global health and development innovations."},
        {"name": "USAID Innovation Challenge", "cat": "Government Funds", "elig": "Worldwide impact-focused startups."},
        {"name": "Horizon Europe", "cat": "Government Funds", "elig": "Research and innovation in Europe and associates."},
        {"name": "UNICEF Innovation Fund", "cat": "Government Funds", "elig": "Open-source tech for children's well-being."},
        {"name": "WHO Health Innovation", "cat": "Big Companies", "elig": "Global health accessibility solutions."},
        {"name": "WEF UpLink", "cat": "Big Companies", "elig": "Early-stage innovators for climate/water."},
        {"name": "Roddenberry Foundation", "cat": "Big Companies", "elig": "Innovative solutions for global prosperity."},
        {"name": "Skoll Foundation", "cat": "Big Companies", "elig": "Large-scale social entrepreneurship."},
        {"name": "Draper Richards Kaplan", "cat": "Big Companies", "elig": "Early-stage social enterprises."},
    ]
    
    accelerators = [
        {"name": "Y Combinator", "cat": "Private Seed Funds", "elig": "Global early-stage tech startups."},
        {"name": "Techstars Global", "cat": "Private Seed Funds", "elig": "Industry-vertical accelerators worldwide."},
        {"name": "Antler Worldwide", "cat": "Private Seed Funds", "elig": "Individual founders forming teams."},
        {"name": "Entrepreneur First", "cat": "Private Seed Funds", "elig": "Talent-first pre-seed funding."},
        {"name": "500 Global", "cat": "Private Seed Funds", "elig": "Fast-scaling tech companies."},
        {"name": "Sequoia Surge", "cat": "Private Seed Funds", "elig": "Early-stage startups in India/SEA."},
        {"name": "Plug and Play", "cat": "Big Companies", "elig": "Corporate-innovation partnerships."},
        {"name": "MassChallenge", "cat": "Private Seed Funds", "elig": "Equity-free high-impact ventures."},
        {"name": "Startupbootcamp", "cat": "Big Companies", "elig": "Vertical specific global programs."},
        {"name": "Accelerating Asia", "cat": "Private Seed Funds", "elig": "Pre-Series A startups in South Asia."},
        {"name": "Marwari Catalysts", "cat": "Idea Stage", "elig": "Indian tier-2 and tier-3 city startups."},
        {"name": "SGInnovate", "cat": "Government Funds", "elig": "Deep tech startups in Singapore."},
        {"name": "Ventures Spark Asia", "cat": "Idea Stage", "elig": "Scalable startups in Thailand/Asia."},
        {"name": "Founder Institute", "cat": "Idea Stage", "elig": "Global pre-seed stage founders."},
        {"name": "Seedcamp Europe", "cat": "Private Seed Funds", "elig": "European tech with global potential."},
        {"name": "Station F", "cat": "Idea Stage", "elig": "Startups joining the Paris campus."},
        {"name": "UnternehmerTUM", "cat": "Big Companies", "elig": "Deep tech and industrial startups."},
    ]
    
    corporate_tech = [
        {"name": "Google AI Social Good", "cat": "Big Companies", "elig": "AI solutions for societal impact."},
        {"name": "Microsoft Imagine Cup", "cat": "Idea Stage", "elig": "Student-led tech innovation projects."},
        {"name": "AWS Imagine Grant", "cat": "Big Companies", "elig": "Nonprofits using cloud for good."},
        {"name": "Oracle for Startups", "cat": "Big Companies", "elig": "Enterprise-ready tech startups."},
        {"name": "IBM Call for Code", "cat": "Big Companies", "elig": "Developers solving global challenges."},
        {"name": "Stripe Atlas", "cat": "Big Companies", "elig": "Founders starting global internet businesses."},
        {"name": "Visa Everywhere Initiative", "cat": "Big Companies", "elig": "Fintech innovation across the globe."},
        {"name": "Cartier Women's Initiative", "cat": "Big Companies", "elig": "Women-led impact businesses."},
    ]

    scout_programs = [
        {"name": "Sequoia Scout", "cat": "Private Seed Funds", "elig": "Invitation-only pre-seed leads."},
        {"name": "Accel Starters", "cat": "Private Seed Funds", "elig": "Early-stage founders network."},
        {"name": "Bessemer Scouts", "cat": "Private Seed Funds", "elig": "Sourcing deals in specific tech domains."},
        {"name": "Atomico Angel Program", "cat": "Private Seed Funds", "elig": "European tech ecosystem experts."},
    ]

    all_sources = universities + global_grants + accelerators + corporate_tech + scout_programs
    
    today = datetime.now()
    
    # --- GENERATE 450 ENTRIES ---
    for i in range(450):
        src = all_sources[i % len(all_sources)]
        # Cycle through stages to avoid uniformity
        stages = ["Idea Stage", "Seed", "Grant", "Series A", "Pre-Seed"]
        stage = stages[i % len(stages)]
        
        # Variation in amount
        if "Lakhs" in src.get("name", "") or i % 3 == 0:
            amount = f"₹{15 + (i*7)%85} Lakhs"
        elif "$" in src.get("name", "") or i % 3 == 1:
            amount = f"${25 + (i*13)%475}k"
        else:
            amount = "Equity-free Grant" if stage == "Grant" else "Undisclosed Investment"

        # Unique IDs/Names
        program_id = 5000 + i
        name = f"{src['name']} Cycle {i//len(all_sources) + 1} - #{program_id}"
        
        rel_date = (today - timedelta(days=i%120)).strftime("%Y-%m-%d")
        deadline = (today + timedelta(days=30 + (i*5)%180)).strftime("%Y-%m-%d")
        
        funds.append({
            "company_name": name,
            "funding_stage": stage,
            "amount_offered": amount,
            "investor": src['name'],
            "eligibility": src['elig'],
            "category": src['cat'],
            "apply_link": "https://www.f6s.com/search/programs", # Generic high-quality portal
            "release_date": rel_date,
            "deadline": deadline,
            "challenge_info": f"Problem focus: {['Sustainability', 'Healthcare AI', 'Education Tech', 'Climate Fintech', 'Deep Tech'][i%5]}." if "Challenge" in src['name'] or i%4==0 else ""
        })
        
    return funds

def seed():
    data = generate_massive_dataset()
    print(f"--- Seeding MASSIVE dataset: {len(data)} entries...")
    
    # 1. Clear existing generated test data if any (optional but safer for clean state)
    # Actually, the requirement is to 'add', so we just append.

    # 2. Batch into groups of 50 to avoid Supabase/Network limits
    success_count = 0
    for i in range(0, len(data), 50):
        batch = data[i:i+50]
        try:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/funds", json=batch, headers=SUPABASE_HEADERS, timeout=30)
            if res.status_code in [200, 201]:
                success_count += len(batch)
                print(f"SUCCESS: Batch {i//50 + 1} Success! Total: {success_count}/{len(data)}")
            else:
                print(f"ERROR: Batch {i//50 + 1} Failed ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"❌ Batch {i//50 + 1} Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    seed()
