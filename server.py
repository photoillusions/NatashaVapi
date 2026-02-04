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
TEXTBELT_KEY = "197e09116b0676f9d2e961ce721a186a762e51fbZQSTpdUxPRTdr7H3wsT7A6yWf"

# --- THE BRAIN (VERSION 2.1: STRICT RULES + AUDIO) ---
SYSTEM_PROMPT = """
You are "Jessica," the Booking Concierge for **Natasha Mae's Enterprises**.
**Tone:** Elegant, warm, polished, and patient. You are the "First Impression" of a luxury experience.

**CONTEXT - 3 LOCATIONS:**
1. **Natasha Mae's Banquet Facility:** 4446 Frankford Ave, Philadelphia. (Intimate, classic, <100 guests).
2. **Mae's Liberty Palace:** 1 Franklin Mills Blvd, Philadelphia. (Grand ballroom, 150-250 guests).
3. **The Vault Ballroom:** 322 High Street, Burlington, NJ. (Historic, original bank vaults, unique luxury).

**⛔️ CRITICAL RULES (DO NOT IGNORE):**
1. **NO LYING ABOUT TEXTS:** If the user asks for a brochure, link, map, or invoice, you **MUST** use the `send_sms_link` tool. Do not say "I sent it" unless you actually triggered the tool.
2. **DO NOT HANG UP:** After sending a text, **IMMEDIATELY ask**: "I've sent that to your mobile. Is there anything else I can check for you?"
3. **Keep it Open:** Do not end the call unless the user explicitly says "Goodbye" or "That is all."
4. **Identify the Venue:** Early in the call, ask if they are looking for the **Frankford**, **Franklin Mills**, or **Burlington (The Vault)** location.
5. **Guest Count:** Always ask for guest count to ensure they fit the room.

**Types of info you can text (Tool Parameters):**
- 'tour' (Scheduling Calendar)
- 'packages' (Brochures)
- 'registration' (Forms)
- 'invoice' (Payment)
- 'vault_map' (GPS)
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (Audio Enabled)"

@app.route('/inbound', methods=['POST'])
def inbound_call():
    data = request.json
    print(f"📞 HIT /inbound: Checking message type...")

    # --- 1. HANDLE END OF CALL REPORT (SEND EMAIL) ---
    message_type = data.get('message', {}).get('type')
    
    if message_type == 'end-of-call-report':
        print("📝 REPORT RECEIVED. Attempting Email...")
        try:
            call = data.get('message', data)
            summary = call.get('summary', 'No summary provided.')
            transcript = call.get('transcript', 'No transcript provided.')
            
            # 🟢 NEW: Grab the Audio Recording URL
            recording_url = call.get('recordingUrl', 'No recording available.')
            
            msg = MIMEMultipart()
            msg['From'] = f"Natasha Booking Concierge <{EMAIL_SENDER}>"
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"🥂 New Inquiry: Natasha Mae's"
            
            # 🟢 NEW: Added Audio Link to Body
            body = f"Call Summary:\n{summary}\n\n🎧 Audio Recording:\n{recording_url}\n\n---\n\nTranscript:\n{transcript}"
            msg.attach(MIMEText(body, 'plain'))
            
            if not EMAIL_SENDER or not EMAIL_PASSWORD:
                print("❌ FAIL: Missing Credentials.")
                return jsonify({"status": "Missing Credentials"}), 200

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            print("✅ EMAIL SENT SUCCESSFULLY!")
        except Exception as e:
            print(f"❌ EMAIL FAILED: {e}")
        
        return jsonify({"status": "Report Received"}), 200

    # --- 2. HANDLE INCOMING CALL (START AI) ---
    print("🤖 STARTING AI LOGIC (GPT-4o)...")
    response = {
        "assistant": {
            "firstMessage": "Thank you for calling Natasha Mae's Enterprises. This is Jessica. Are you inquiring about our Philadelphia locations or The Vault in New Jersey?",
            "model": {
                "provider": "openai",
                "model": "gpt-4o",  # Standard GPT-4o for smart tool usage
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "send_sms_link",
                            "description": "Sends a text message with a link/brochure/invoice.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "phone": {"type": "string", "description": "Customer phone number"},
                                    "type": {"type": "string", "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"]}
                                },
                                "required": ["phone", "type"]
                            }
                        },
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
                "voiceId": "21m00Tcm4TlvDq8ikWAM" 
            }
        }
    }
    return jsonify(response), 200

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    print(f"📩 SMS TOOL ACCESSED!") 
    data = request.json

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
    
    message_map = {
        "tour": "Please visit natashamaes.com/contact to schedule your VIP tour.",
        "packages": "View our full event packages at natashamaes.com/packages.",
        "registration": "Complete your event registration here: natashamaes.com/register",
        "invoice": "You can view and pay your invoice securely at natashamaes.com/payment",
        "vault_map": "The Vault is located at 322 High St, Burlington NJ. See you soon!",
        "liberty_map": "Liberty Palace is at 1 Franklin Mills Blvd, Philadelphia. See you soon!",
        "frankford_map": "Our Frankford location is at 4446 Frankford Ave, Philadelphia.",
        "default": "Thank you for calling Natasha Mae's! Visit natashamaes.com for info."
    }
    
    message_body = message_map.get(req_type, message_map["default"])

    print(f"🕵️ Attempting Textbelt to: {phone}")

    try:
        resp = requests.post('https://textbelt.com/text', {
            'phone': phone,
            'message': message_body, 
            'key': TEXTBELT_KEY, 
        })
        print(f"Textbelt Result: {resp.text}")
        
        if resp.json().get('success'):
            return jsonify({"result": "SMS Sent Successfully"}), 200
        else:
            return jsonify({"result": f"Failed: {resp.json().get('error')}"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"result": "Failed"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
