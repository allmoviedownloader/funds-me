import os, requests, json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

# --- BOT LOGIC ---

def get_funds_by_query(query):
    # Search Supabase for the specified category or stage
    url = f"{SUPABASE_URL}/rest/v1/funds?or=(category.ilike.%{query}%,funding_stage.ilike.%{query}%)&limit=3&order=created_at.desc"
    res = requests.get(url, headers=SUPABASE_HEADERS)
    if res.status_code == 200:
        return res.json()
    return []

def format_whatsapp_reply(funds, category):
    if not funds:
        return f"Sorry! Mujhe abhi {category} ke liye koi active funds nahi mile. Check again tomorrow!"
    
    reply = f"🚀 *Lateast {category} Opportunities:*\n\n"
    for f in funds:
        reply += f"🏢 *{f.get('company_name')}*\n"
        reply += f"💰 {f.get('amount_offered')}\n"
        reply += f"🔗 Link: {f.get('apply_link')}\n\n"
    
    reply += "Aura jaanne ke liye 'MENU' likhen."
    return reply

# --- WEBHOOK ENDPOINT ---
# This is where WhatsApp (via Twilio/WATI) will send messages

@app.route("/whatsapp/webhook", methods=["POST"])
def webhook():
    # Extract message and sender from request (Assumed Twilio format)
    incoming_msg = request.values.get('Body', '').lower()
    sender = request.values.get('From')
    
    print(f"Message from {sender}: {incoming_msg}")
    
    response_msg = ""
    
    if "menu" in incoming_msg or "hi" in incoming_msg or "hello" in incoming_msg:
        response_msg = "Swagat hai! 🙏 Kis type ki funding chahiye?\n\n1. *Govt* - Government Challenges\n2. *Seed* - Private Seed Funds\n3. *Idea* - Idea Stage Funds\n\nBass keyword reply karein (e.g. 'Govt')."
    
    elif "govt" in incoming_msg:
        funds = get_funds_by_query("Government")
        response_msg = format_whatsapp_reply(funds, "Government")
        
    elif "seed" in incoming_msg:
        funds = get_funds_by_query("Seed")
        response_msg = format_whatsapp_reply(funds, "Seed")
        
    elif "idea" in incoming_msg:
        funds = get_funds_by_query("Idea")
        response_msg = format_whatsapp_reply(funds, "Idea Stage")
    
    else:
        response_msg = "Mujhe samajh nahi aaya. 😅 'MENU' likhkar options dekhein."

    # In a real setup, you'd use the WhatsApp API to SEND this response back.
    # For now, we return it for testing/demonstration.
    return jsonify({
        "status": "success",
        "reply": response_msg
    })

if __name__ == "__main__":
    # Note: Live bot requires a public URL (ngrok or hosted server)
    app.run(port=5000, debug=True)
