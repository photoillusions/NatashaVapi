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

# --- THE BRAIN (VERSION 3.1: OBEDIENCE + OPTIONAL PHONE) ---
SYSTEM_PROMPT = """
You are "Jessica," the Booking Concierge for **Natasha Mae's Enterprises**.
**Tone:** Efficient, Polite, and IMMEDIATE.

**CONTEXT - 3 LOCATIONS:**
1. **Frankford Ave** (Philly): Intimate, <100 guests.
2. **Liberty Palace** (Franklin Mills): Grand ballroom, 150-250 guests.
3. **The Vault** (Burlington, NJ): Historic, luxury, original bank vaults.

**🔥 PRIME DIRECTIVE: IMMEDIATE ACTION 🔥**
If the caller asks for a text, brochure, map, or link, you must **STOP EVERYTHING** and trigger the `send_sms_link` tool immediately.

**RULES OF ENGAGEMENT:**
1. **YOU ALREADY HAVE THE PHONE NUMBER:** Do not ask for it. Do not worry about it. Just trigger the tool.
2. **DO NOT** ask qualifying questions if they just want a text.
3. **JUST SEND IT.**

**Tool Parameters (Type):**
- 'tour' (Scheduling Calendar)
- 'packages' (Brochures)
- 'registration' (Forms)
- 'invoice' (Payment)
- 'vault_map' (GPS)
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (V3.1 - Mini Fixed)"

@app.route('/inbound', methods=['POST'])
def inbound_call():
    data = request.json
    print(f"📞 HIT /inbound")

    # --- 1. HANDLE END OF CALL REPORT (SEND EMAIL) ---
    message_type = data.get('message', {}).get('type')
    
    if message_type == 'end-of-call-report':
        print("📝 REPORT RECEIVED. Attempting Email...")
        try:
            call = data.get('message', data)
            summary = call.get('summary', 'No summary provided.')
            transcript = call.get('transcript', 'No transcript provided.')
            recording_url = call.get('recordingUrl', 'No recording available.')
            
            msg = MIMEMultipart()
            msg['From'] = f"Natasha Booking Concierge <{EMAIL_SENDER}>"
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"🥂 New Inquiry: Natasha Mae's"
            
            body = f"Call Summary:\n{summary}\n\n🎧 Audio Recording:\n{recording_url}\n\n---\n\nTranscript:\n{transcript}"
            msg.attach(MIMEText(body, 'plain'))
            
            if not EMAIL_SENDER or not EMAIL_PASSWORD:
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
    print("🤖 STARTING AI LOGIC (GPT-4o-mini)...")
    response = {
        "assistant": {
            "firstMessage": "Thank you for calling Natasha Mae's Enterprises. This is Jessica. Are you inquiring about our Philadelphia locations or The Vault in New Jersey?",
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",  # 🟢 Staying Cheap
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
                                    # 🟢 NOTE: We describe this, but we don't MAKE it required anymore.
                                    "phone": {"type": "string", "description": "Optional: Customer phone number (System will detect automatically)"},
                                    "type": {"type": "string", "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"]}
                                },
                                # 🟢 CRITICAL FIX: Only 'type' is required now.
                                "required": ["type"] 
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

    # 1. SMART NUMBER DETECTION (This does the heavy lifting so AI doesn't have to)
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

    # Use the system number if the AI didn't provide one
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
        if not TEXTBELT_KEY:
             return jsonify({"result": "Error: Missing TEXTBELT_KEY"}), 200

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
