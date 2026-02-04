import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
# 🔴 CRITICAL: These MUST be set in Render Environment Variables
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")     # Your Gmail Address
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Your Gmail App Password
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER") # Where call reports go

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
- 'tour' (Scheduling Calendar)
- 'packages' (Brochures)
- 'registration' (Forms)
- 'invoice' (Payment)
- 'vault_map' (GPS)
- 'liberty_map' (GPS)
- 'frankford_map' (GPS)
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (Email Gateway Edition)"

@app.route('/inbound', methods=['POST'])
def inbound_call():
    data = request.json
    message_type = data.get('message', {}).get('type')
    print(f"📞 HIT /inbound - TYPE: {message_type}")

    # 1. REPORTING (Emails you the summary)
    if message_type == 'end-of-call-report':
        try:
            call = data.get('message', data)
            summary = call.get('summary', 'No summary.')
            transcript = call.get('transcript', 'No transcript.')
            
            msg = MIMEMultipart()
            msg['From'] = f"Natasha AI <{EMAIL_SENDER}>"
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"🥂 New Inquiry: Natasha Mae's"
            body = f"Call Summary:\n{summary}\n\n---\n\nTranscript:\n{transcript}"
            msg.attach(MIMEText(body, 'plain'))
            
            if EMAIL_SENDER and EMAIL_PASSWORD:
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
        except Exception as e:
            print(f"❌ Report Email Failed: {e}")
        return jsonify({"status": "OK"}), 200

    # 2. VAPI CONFIGURATION
    if message_type == 'assistant-request':
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
                                "description": "Sends a text message with a clickable link.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"]
                                        }
                                    },
                                    "required": ["type"]
                                }
                            },
                            # 🔴 UPDATE THIS URL TO YOUR RENDER URL
                            "server": {"url": "https://natashavapi.onrender.com/send-sms"} 
                        }
                    ]
                },
                "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "en-US"},
                "voice": {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM"}
            }
        }
        return jsonify(response), 200

    if message_type == 'tool-calls':
        return handle_tool_call(data)

    return jsonify({"status": "acknowledged"}), 200

# =====================================================
# 🔫 THE SHOTGUN EMAIL GATEWAY HANDLER
# =====================================================
def handle_tool_call(data):
    print("🔫 TRIGGERING SHOTGUN EMAIL-TEXT...")
    
    # 1. EXTRACT ARGS
    args = {}
    tool_call_id = None
    try:
        tool_call_list = data.get('message', {}).get('toolCallList', [])
        if tool_call_list:
            tool_call_id = tool_call_list[0].get('id')
            args = tool_call_list[0].get('arguments', {})
        else:
            # Fallback for direct tool calls
            tool_calls = data.get('message', {}).get('toolCalls', [])
            if tool_calls:
                tool_call_id = tool_calls[0].get('id')
                args = tool_calls[0].get('function', {}).get('arguments', {})
            else:
                args = data
    except: args = data

    # 2. GET & CLEAN PHONE NUMBER
    phone_raw = None
    try:
        phone_raw = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
        if not phone_raw:
             phone_raw = data.get('message', {}).get('customer', {}).get('number')
    except: pass

    if not phone_raw: phone_raw = args.get('phone')

    # Clean to 10 digits
    phone = str(phone_raw).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
    if len(phone) == 11 and phone.startswith("1"):
        phone = phone[1:] # Strip leading 1

    # 3. DEFINE THE LINKS (REAL HTTPS LINKS!)
    req_type = args.get('type', 'default').lower()
    
    # Since email gateways don't block links, we use the real ones:
    message_map = {
        "tour": "Schedule your VIP tour here: https://www.natashamaes.com/contact-us",
        "packages": "View our full packages: https://www.natashamaes.com/packages",
        "registration": "Register here: https://www.natashamaes.com/register",
        "invoice": "View your invoice: https://www.natashamaes.com/payment",
        "vault_map": "The Vault GPS: https://goo.gl/maps/placeholder",
        "liberty_map": "Liberty Palace GPS: https://goo.gl/maps/placeholder",
        "frankford_map": "Frankford Ave GPS: https://goo.gl/maps/placeholder",
        "default": "Visit us at https://www.natashamaes.com"
    }
    
    message_body = message_map.get(req_type, message_map["default"])

    # 4. DEFINE GATEWAYS (The "Shotgun")
    # This list covers Verizon, T-Mobile, AT&T, Sprint, Metro, Cricket, Virgin, etc.
    gateways = [
        f"{phone}@vtext.com",       # Verizon
        f"{phone}@tmomail.net",     # T-Mobile
        f"{phone}@txt.att.net",     # AT&T
        f"{phone}@mms.att.net",     # AT&T MMS (Better for links)
        f"{phone}@messaging.sprintpcs.com", # Sprint
        f"{phone}@mymetropcs.com",  # MetroPCS
        f"{phone}@sms.cricketwireless.net", # Cricket
        f"{phone}@vmobl.com"        # Virgin Mobile
    ]

    result_message = ""

    # 5. FIRE THE EMAILS
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        result_message = "Error: Missing Email Credentials on Server"
        print("❌ MISSING CREDENTIALS")
    elif not phone:
        result_message = "Error: No Phone Number Found"
    else:
        try:
            print(f"🔥 Firing at {len(gateways)} gateways for {phone}...")
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)

            success_count = 0
            for gateway in gateways:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = "Natasha"
                    msg['To'] = gateway
                    msg['Subject'] = "Link" # Required by some carriers
                    msg.attach(MIMEText(message_body, 'plain'))
                    server.send_message(msg)
                    success_count += 1
                except: pass # Ignore failures (most will fail, one will hit)
            
            server.quit()
            result_message = f"Blast sent to {success_count} gateways."
            print(f"✅ {result_message}")

        except Exception as e:
            result_message = f"SMTP Error: {e}"
            print(f"❌ {result_message}")

    # 6. RETURN TO VAPI
    return jsonify({
        "results": [{
            "toolCallId": tool_call_id,
            "result": result_message
        }]
    }), 200

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    """Direct endpoint"""
    return handle_tool_call(request.json)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
