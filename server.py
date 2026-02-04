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
    return "Natasha Mae's Server Online (V3.2 - VAPI Fixed)"

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
                "model": "gpt-4o-mini",
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
                                    "phone": {"type": "string", "description": "Optional: Customer phone number (System will detect automatically)"},
                                    "type": {"type": "string", "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"]}
                                },
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


# =====================================================
# FIXED SMS ENDPOINT - CORRECT VAPI RESPONSE FORMAT
# =====================================================
@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    print(f"📩 SMS TOOL ACCESSED!") 
    data = request.json
    print(f"📦 RAW DATA: {data}")

    # ============================================
    # 1. EXTRACT THE TOOL CALL ID (CRITICAL!)
    # ============================================
    tool_call_id = None
    args = {}
    try:
        # VAPI sends toolCallList with the ID
        tool_call_list = data.get('message', {}).get('toolCallList', [])
        if tool_call_list:
            tool_call_id = tool_call_list[0].get('id')
            args = tool_call_list[0].get('arguments', {})
        else:
            # Fallback to older format
            tool_calls = data.get('message', {}).get('toolCalls', [])
            if tool_calls:
                tool_call_id = tool_calls[0].get('id')
                args = tool_calls[0].get('function', {}).get('arguments', {})
            else:
                args = data
    except Exception as e:
        print(f"❌ Error parsing tool call: {e}")
        args = data
        
    print(f"🔑 TOOL CALL ID: {tool_call_id}")
    print(f"📋 ARGUMENTS: {args}")

    # ============================================
    # 2. GET PHONE NUMBER FROM CALL DATA
    # ============================================
    phone = None
    try:
        call_data = data.get('message', {}).get('call', {})
        customer = call_data.get('customer', {})
        phone = customer.get('number')
        
        if not phone:
            phone = data.get('message', {}).get('customer', {}).get('number')
    except Exception as e:
        print(f"⚠️ Could not get phone from call data: {e}")
    
    if not phone:
        phone = args.get('phone')
    
    print(f"📱 DETECTED PHONE: {phone}")

    # ============================================
    # 3. CLEAN UP PHONE NUMBER
    # ============================================
    if phone:
        phone = str(phone).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
        if len(phone) == 10:
            phone = f"+1{phone}"
        elif len(phone) == 11 and phone.startswith("1"):
            phone = f"+{phone}"
        elif not phone.startswith("+"):
            phone = f"+{phone}"

    # ============================================
    # 4. BUILD THE MESSAGE
    # ============================================
    req_type = args.get('type', 'default').lower()
    
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

    # ============================================
    # 5. SEND THE TEXT
    # ============================================
    print(f"🕵️ Attempting Textbelt to: {phone}")
    
    result_message = ""
    
    if not phone:
        result_message = "Error: Could not detect phone number"
        print(f"❌ {result_message}")
    elif not TEXTBELT_KEY:
        result_message = "Error: Missing TEXTBELT_KEY"
        print(f"❌ {result_message}")
    else:
        try:
            resp = requests.post('https://textbelt.com/text', {
                'phone': phone,
                'message': message_body, 
                'key': TEXTBELT_KEY, 
            })
            print(f"📬 Textbelt Response: {resp.text}")
            
            resp_json = resp.json()
            if resp_json.get('success'):
                result_message = f"SMS sent successfully to {phone}"
                print(f"✅ {result_message}")
            else:
                result_message = f"SMS failed: {resp_json.get('error', 'Unknown error')}"
                print(f"❌ {result_message}")

        except Exception as e:
            result_message = f"SMS failed with exception: {str(e)}"
            print(f"❌ {result_message}")

    # ============================================
    # 6. RETURN IN VAPI'S REQUIRED FORMAT!!!
    # ============================================
    response = {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": result_message
            }
        ]
    }
    
    print(f"📤 RETURNING TO VAPI: {response}")
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
