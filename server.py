import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
# 🔴 CRITICAL: These MUST be set in Render Environment Variables
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")     # Your Gmail Address
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Your Gmail App Password
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER") # Where call reports go

# 📱 CLICKSEND SMS API CREDENTIALS
CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME")  # Your ClickSend username (email)
CLICKSEND_API_KEY = os.environ.get("CLICKSEND_API_KEY")    # Your ClickSend API Key

# --- THE BRAIN ---
SYSTEM_PROMPT = """
You are "Jessica," the Booking Concierge for **Natasha Mae's Enterprises**.
**Tone:** Efficient, Polite, and IMMEDIATE.

**CONTEXT - 3 LOCATIONS:**
1. **Frankford Ave** (Philly): Intimate, <100 guests.
2. **Liberty Palace** (Franklin Mills): Grand ballroom, 150-250 guests.
3. **The Vault** (Burlington, NJ): Historic, luxury, original bank vaults.

**🔥 PRIME DIRECTIVE: ZERO FRICTION 🔥**
If the caller wants a text/link/info, you must **CALL THE FUNCTION `send_sms_link` IMMEDIATELY**.

**🚫 FORBIDDEN BEHAVIORS (When sending text):**
1. **DO NOT ASK** "Is this the correct number?" (Assume yes).
2. **DO NOT ASK** "Which location?" (Send the general 'packages' or 'registration' if unspecified).
3. **DO NOT SAY** "I can send that..." -> **JUST SEND IT.**
4. **DO NOT** wait for permission.

**EXECUTION LOOP:**
1. User asks for info.
2. TRIGGER TOOL `send_sms_link`.
3. Say: "I've sent that to your phone."
4. Stop.

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
    return "Natasha Mae's Server Online (ClickSend SMS Edition v2)"

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
                    "toolIds": ["8bc95305-e18f-4cf3-8a43-a02241d215e4"]
                },
                "serverMessages": ["conversation-update", "end-of-call-report", "speech-update", "status-update", "tool-calls", "assistant.started"],
                "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "en-US"},
                "voice": {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM"}
            }
        }
        return jsonify(response), 200

    if message_type == 'tool-calls':
        return handle_tool_call(data)

    return jsonify({"status": "acknowledged"}), 200

# =====================================================
# � CLICKSEND SMS API HANDLER
# =====================================================
def handle_tool_call(data):
    print("� TRIGGERING CLICKSEND SMS...")
    
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

    # Clean phone number and format for ClickSend (needs +1 for US)
    phone = str(phone_raw).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
    if len(phone) == 10:
        phone = "1" + phone  # Add US country code
    if not phone.startswith("+"):
        phone = "+" + phone  # ClickSend requires + prefix

    # 3. DEFINE THE LINKS
    req_type = args.get('type', 'default').lower()
    
    message_map = {
        "tour": "Natasha Mae's: Schedule your VIP tour here: https://www.natashamaes.com/contact-us",
        "packages": "Natasha Mae's: View our full packages: https://www.natashamaes.com/packages",
        "registration": "Natasha Mae's: Register here: https://www.natashamaes.com/register",
        "invoice": "Natasha Mae's: View your invoice: https://www.natashamaes.com/payment",
        "vault_map": "The Vault GPS: https://goo.gl/maps/placeholder",
        "liberty_map": "Liberty Palace GPS: https://goo.gl/maps/placeholder",
        "frankford_map": "Frankford Ave GPS: https://goo.gl/maps/placeholder",
        "default": "Natasha Mae's: Visit us at https://www.natashamaes.com"
    }
    
    message_body = message_map.get(req_type, message_map["default"])

    result_message = ""

    # 4. SEND VIA CLICKSEND API
    if not CLICKSEND_USERNAME or not CLICKSEND_API_KEY:
        result_message = "Error: Missing ClickSend Credentials on Server"
        print("❌ MISSING CLICKSEND CREDENTIALS")
    elif not phone or len(phone) < 10:
        result_message = "Error: No Valid Phone Number Found"
        print(f"❌ INVALID PHONE: {phone}")
    else:
        try:
            print(f"📲 Sending SMS to {phone} via ClickSend...")
            
            # ClickSend REST API endpoint
            url = "https://rest.clicksend.com/v3/sms/send"
            
            payload = {
                "messages": [
                    {
                        "to": phone,
                        "body": message_body,
                        "source": "NatashaMaes"
                    }
                ]
            }
            
            response = requests.post(
                url,
                json=payload,
                auth=(CLICKSEND_USERNAME, CLICKSEND_API_KEY),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Check if message was accepted
                if response_data.get("response_code") == "SUCCESS":
                    result_message = f"SMS sent successfully to {phone}"
                    print(f"✅ {result_message}")
                else:
                    result_message = f"ClickSend Error: {response_data.get('response_msg', 'Unknown error')}"
                    print(f"⚠️ {result_message}")
            else:
                result_message = f"ClickSend HTTP Error: {response.status_code}"
                print(f"❌ {result_message} - {response.text}")

        except Exception as e:
            result_message = f"SMS Error: {e}"
            print(f"❌ {result_message}")

    # 5. RETURN TO VAPI
    return jsonify({
        "results": [{
            "toolCallId": tool_call_id,
            "result": result_message
        }]
    }), 200

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    """Direct endpoint for SMS tool calls"""
    return handle_tool_call(request.json)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
