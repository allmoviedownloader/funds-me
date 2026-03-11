import os, requests
from dotenv import load_dotenv
load_dotenv()
url = f"{os.getenv('SUPABASE_URL')}/rest/v1/funds?select=count"
headers = {
    'apikey': os.getenv('SUPABASE_KEY'),
    'Authorization': f"Bearer {os.getenv('SUPABASE_KEY')}",
    'Prefer': 'count=exact'
}
r = requests.get(url, headers=headers)
count = r.headers.get('Content-Range', '').split('/')[-1]
print(f"Total Funds in DB: {count}")

# Check for release_date presence
url_check = f"{os.getenv('SUPABASE_URL')}/rest/v1/funds?select=company_name,deadline,category&limit=5&order=created_at.desc"
r_check = requests.get(url_check, headers=headers)
print("\nRecent Entries Sample:")
data = r_check.json()
if isinstance(data, list):
    for item in data:
        print(f"- {item.get('company_name')}: Category={item.get('category')}, Deadline={item.get('deadline')}")
else:
    print(f"Error fetching sample: {data}")
