import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER") 

# 🟢 NATASHA MAE'S PAID KEY (Hardcoded)
TEXTBELT_KEY = "197e09116b0676f9d2e961ce721a186a762e51fbZQSTpdUxPRTdr7H3wsT7A6yWf"

# --- THE BRAIN (Approved Logic) ---
SYSTEM_PROMPT = """
You are "Jessica," the Booking Concierge for **Natasha Mae's Enterprises**.
**Tone:** Elegant, warm, polished, and patient. You are the "First Impression" of a luxury experience.

**CONTEXT - 3 LOCATIONS:**
1. **Natasha Mae's Banquet Facility:** 4446 Frankford Ave, Philadelphia. (Intimate, classic, <100 guests).
2. **Mae's Liberty Palace:** 1 Franklin Mills Blvd, Philadelphia. (Grand ballroom, 150-250 guests).
3. **The Vault Ballroom:** 322 High Street, Burlington, NJ. (Historic, original bank vaults, unique luxury).

**CRITICAL RULES:**
1. **Identify the Venue:** Early in the call, ask if they are looking for the **Frankford**, **Franklin Mills**, or **Burlington (The Vault)** location.
2. **The Goal = TOUR:** Your primary goal is to schedule a VIP Tour. Do not quote final prices over the phone; say "Packages are customizable, come see the room."
3. **Guest Count:** Always ask for guest count to ensure they fit the room.
4. **Caller ID:** You HAVE their number. NEVER ask for it.
5. **SMS Tool:** If they want a brochure, menu, or tour link, say: "I've sent that to your mobile phone just now." and use the tool.
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (Jessica)"

@app.route('/inbound', methods=['POST'])
def inbound_call():
    print("📞 Incoming Call (Natasha Mae's)")
    response = {
        "assistant": {
            # 🟢 UPDATED GREETING:
            "firstMessage": "Thank you for calling Natasha Mae's Enterprises. I'm Jessica, Natasha Mae's AI Assistant, I answer questions and take messages; how can I be of service today?",
            
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "send_sms_link",
                            "description": "Sends a text message with a link.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "phone": {"type": "string", "description": "Customer phone number"},
                                    "type": {"type": "string", "enum": ["tour", "menu", "brochure", "vault_map", "liberty_map", "frankford_map"]}
                                },
                                "required": ["phone", "type"]
                            }
                        },
                        # 🟢 UPDATED TO YOUR LIVE RENDER URL
                        "server": {"url": "https://natashavapi.onrender.com/send-sms"} 
                    }
                ]
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en-US",
                "endpointing": 1500
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM" # Rachel Voice
            }
        }
    }
    return jsonify(response), 200

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    data = request.json
    print(f"📩 SMS Triggered")

    # 1. SMART NUMBER DETECTION
    system_phone = None
    try:
        system_phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
        if not system_phone:
             system_phone = data.get('message', {}).get('customer', {}).get('number')
    except: pass
    
    args = {}
    try:
        if 'message' in data and 'toolCalls' in data['message']:
            args = data['message']['toolCalls'][0]['function']['arguments']
        else:
            args = data
    except: args = data

    phone = system_phone if system_phone else args.get('phone')
    
    # 2. FIX US PHONE NUMBERS
    if phone:
        phone = str(phone).replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        if len(phone) == 10:
            phone = f"+1{phone}"
        elif len(phone) == 11 and phone.startswith("1"):
            phone = f"+{phone}"

    req_type = args.get('type', 'brochure').lower()
    
    # 🟢 🟢 🟢 CLEAN MESSAGES - NO PHOTO ILLUSIONS 🟢 🟢 🟢
    message_map = {
        "tour": "Please visit natashamaes.com/contact to schedule your VIP tour with Natasha Mae's.",
        "menu": "Our packages are available at natashamaes.com/packages.",
        "brochure": "View our full event brochure at natashamaes.com/packages.",
        "vault_map": "The Vault is located at 322 High St, Burlington NJ. See you soon!",
        "liberty_map": "Liberty Palace is at 1 Franklin Mills Blvd, Philadelphia. See you soon!",
        "frankford_map": "Our Frankford location is at 4446 Frankford Ave, Philadelphia.",
        "default": "Thank you for calling Natasha Mae's! Visit natashamaes.com for info."
    }
    
    message_body = message_map.get(req_type, message_map["default"])

    print(f"🕵️ Sending for Natasha Mae's to: {phone}")

    try:
        if not TEXTBELT_KEY:
             return jsonify({"result": "Error: Missing TEXTBELT_KEY"}), 200

        resp = requests.post('https://textbelt.com/text', {
            'phone': phone,
            'message': message_body, 
            'key': TEXTBELT_KEY, 
        })
        print(f"Textbelt Result: {resp.text}")
        
        # Check success
        if resp.json().get('success'):
            return jsonify({"result": "SMS Sent Successfully"}), 200
        else:
            return jsonify({"result": f"Failed: {resp.json().get('error')}"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"result": "Failed"}), 200

@app.route('/webhook', methods=['POST'])
def vapi_email_webhook():
    # EMAIL REPORTING
    data = request.json
    if data.get('message', {}).get('type') == 'end-of-call-report':
        try:
            call = data.get('message', data)
            summary = call.get('summary', 'No summary.')
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"🥂 New Inquiry: Natasha Mae's"
            msg.attach(MIMEText(f"Call Summary:\n{summary}", 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
        except: pass
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
