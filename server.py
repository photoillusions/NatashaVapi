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

# --- THE BRAIN ---
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
1. **YOU ALREADY HAVE THE PHONE NUMBER:** Do not ask for it. Just trigger the tool.
2. **DO NOT** ask qualifying questions if they just want a text.
3. **JUST SEND IT.**

**Tool Parameters (Type):**
- 'tour' (Scheduling Info)
- 'packages' (Brochure Info)
- 'registration' (Forms)
- 'invoice' (Payment Info)
- 'vault_map' (GPS Address)
- 'liberty_map' (GPS Address)
- 'frankford_map' (GPS Address)
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (Ultra-Safe Mode)"

@app.route('/inbound', methods=['POST'])
def inbound_call():
    data = request.json
    message_type = data.get('message', {}).get('type')
    
    print(f"📞 HIT /inbound - TYPE: {message_type}")

    # 1. END OF CALL REPORT - Send email
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
            
            if EMAIL_SENDER and EMAIL_PASSWORD:
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
                print("✅ EMAIL SENT SUCCESSFULLY!")
            else:
                print("⚠️ Missing email credentials")
        except Exception as e:
            print(f"❌ EMAIL FAILED: {e}")
        
        return jsonify({"status": "Report Received"}), 200

    # 2. ASSISTANT REQUEST - Return the assistant config
    if message_type == 'assistant-request':
        print("🤖 ASSISTANT REQUEST - Sending config...")
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
                                "description": "Sends a text message with info/address to the caller.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string", 
                                            "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"],
                                            "description": "The type of information to send"
                                        }
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

    # 3. TOOL CALLS - Route to send-sms handler
    if message_type == 'tool-calls':
        print("🔧 TOOL CALL received at /inbound - routing to handler...")
        return handle_tool_call(data)

    return jsonify({"status": "acknowledged"}), 200


# =====================================================
# SMS TOOL HANDLER
# =====================================================
def handle_tool_call(data):
    """Handle the actual SMS sending logic"""
    print(f"📩 SMS TOOL PROCESSING!") 

    # 1. EXTRACT ARGUMENTS
    args = {}
    tool_call_id = None
    try:
        tool_call_list = data.get('message', {}).get('toolCallList', [])
        if tool_call_list:
            tool_call_id = tool_call_list[0].get('id')
            args = tool_call_list[0].get('arguments', {})
        else:
            tool_calls = data.get('message', {}).get('toolCalls', [])
            if tool_calls:
                tool_call_id = tool_calls[0].get('id')
                args = tool_calls[0].get('function', {}).get('arguments', {})
            else:
                args = data
    except:
        args = data
        
    # 2. GET PHONE NUMBER
    phone = None
    try:
        system_phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
        if not system_phone:
             system_phone = data.get('message', {}).get('customer', {}).get('number')
        phone = system_phone
    except: pass
    
    if not phone:
        phone = args.get('phone')
    
    # 3. CLEAN PHONE NUMBER
    if phone:
        phone = str(phone).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
        if len(phone) == 10:
            phone = f"+1{phone}"
        elif len(phone) == 11 and phone.startswith("1"):
            phone = f"+{phone}"
        elif not phone.startswith("+"):
            phone = f"+{phone}"

    # 4. BUILD THE MESSAGE (NO URLS HERE)
    req_type = args.get('type', 'default').lower()
    
    # 🟢 ULTRA SAFE MODE: NO .COM OR HTTP
    message_map = {
        "tour": "We would love to show you around! Please search for Natasha Mae's Enterprises on Google to schedule your VIP tour online.",
        "packages": "Our full event packages are available on our main website. Search for Natasha Mae's Enterprises to view them.",
        "registration": "To complete your event registration, please check your email for the forms or visit our main office.",
        "invoice": "You can view and pay your invoice securely by contacting our billing department or via our main website.",
        "vault_map": "The Vault is located at 322 High St, Burlington NJ. See you soon!",
        "liberty_map": "Liberty Palace is at 1 Franklin Mills Blvd, Philadelphia. See you soon!",
        "frankford_map": "Our Frankford location is at 4446 Frankford Ave, Philadelphia.",
        "default": "Thank you for calling Natasha Mae's! We look forward to hosting your event."
    }
    
    message_body = message_map.get(req_type, message_map["default"])

    # 5. SEND THE TEXT
    print(f"🕵️ Attempting Textbelt to: {phone}")
    result_message = ""
    
    if not phone or not TEXTBELT_KEY:
        result_message = "Error: Missing phone or key"
    else:
        try:
            resp = requests.post('https://textbelt.com/text', {
                'phone': phone,
                'message': message_body, 
                'key': TEXTBELT_KEY, 
            })
            print(f"📬 Textbelt Response: {resp.text}")
            if resp.json().get('success'):
                result_message = "SMS sent successfully"
            else:
                result_message = f"SMS failed: {resp.json().get('error')}"
        except Exception as e:
            result_message = f"SMS failed: {str(e)}"

    # 6. RETURN TO VAPI
    response = {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": result_message
            }
        ]
    }
    return jsonify(response), 200

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    """Direct endpoint for tool calls"""
    return handle_tool_call(request.json)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
