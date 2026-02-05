import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
import json
import calendar_service  # Import our helper module

app = Flask(__name__)

# --- CONFIGURATION ---
# 🔴 CRITICAL: These MUST be set in Render Environment Variables
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")     # Your Gmail Address
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Your Gmail App Password
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER") # Where call reports go

# 📱 CLICKSEND SMS API CREDENTIALS
CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME")  # Your ClickSend username (email)
CLICKSEND_API_KEY = os.environ.get("CLICKSEND_API_KEY")    # Your ClickSend API Key

# --- THE BRAIN (Updated for Stricter Booking Logic) ---
SYSTEM_PROMPT = """
You are "Jessica," the Booking Concierge for **Natasha Mae's Enterprises**.
**Tone:** Efficient, Polite, and IMMEDIATE.

**CONTEXT - 3 LOCATIONS:**
1. **Frankford Ave** (Philly): Intimate, <100 guests.
2. **Liberty Palace** (Franklin Mills): Grand ballroom, 150-250 guests.
3. **The Vault** (Burlington, NJ): Historic, luxury, original bank vaults.

**🔥 CRITICAL INSTRUCTIONS - READ CAREFULLY 🔥**

**1. HANDLING INFORMATION REQUESTS (Brochures, Maps, Links):**
   - If the user asks for info, pricing, or locations, you **MUST** call the `send_sms_link` function.
   - Example: "Send me the brochure" -> Call `send_sms_link(type='packages')`.
   - **DO NOT** read long URLs out loud. Say "I am texting that to you now."

**2. HANDLING BOOKING REQUESTS (Specific Date & Time):**
   - If the user provides a **Date and Time** (e.g., "October 17th at 5 PM"), you **MUST** use the Calendar tools.
   - **Step 1:** Call `check_availability` for that time slot.
   - **Step 2:** If available, call `book_appointment`.
   - **DO NOT** just say "I booked it" without actually calling the `book_appointment` tool.
   - **DO NOT** use the SMS tool for bookings unless the booking tool fails.

**📆 CALENDAR RULES:**
- Assume the year is 2026 unless the user says otherwise.
- Convert verbal times to ISO 8601 format (e.g., "5 PM" -> "17:00:00").
- If you need a name or email to finish the booking, **ASK FOR IT**.

**Tool Parameters (Type):**
- 'tour' (Scheduling Calendar Link)
- 'packages' (Brochures)
- 'registration' (Forms)
- 'invoice' (Payment)
- 'vault_map', 'liberty_map', 'frankford_map' (GPS)
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (Calendar & SMS Edition v3)"

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
            print(f"📝 TRANSCRIPT:\n{transcript}")
            
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
                                "description": "Sends a text message with a clickable link. Use for info requests (brochures, maps, pricing).",
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
                            "server": {"url": "https://natashavapi.onrender.com/send-sms"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "check_availability",
                                "description": "Checks if a specific time slot is available on the calendar.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "start_time": {"type": "string", "description": "ISO 8601 start time (e.g. 2026-10-17T17:00:00-05:00)"},
                                        "end_time": {"type": "string", "description": "ISO 8601 end time (e.g. 2026-10-17T18:00:00-05:00)"}
                                    },
                                    "required": ["start_time", "end_time"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "book_appointment",
                                "description": "Books a confirmed appointment/tour on the calendar. Only use after checking availability.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "summary": {"type": "string", "description": "Title of event (e.g. 'Tour for Tony George')"},
                                        "start_time": {"type": "string", "description": "ISO 8601 start time"},
                                        "end_time": {"type": "string", "description": "ISO 8601 end time"},
                                        "attendee_email": {"type": "string", "description": "Guest email for invite"},
                                        "description": {"type": "string", "description": "Notes (phone number, location preference)"}
                                    },
                                    "required": ["summary", "start_time", "end_time"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        }
                    ]
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
# 📨 CLICKSEND SMS API HANDLER
# =====================================================
def handle_tool_call(data):
    print("🔔 TOOL CALL RECEIVED")
    
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

@app.route('/calendar-tool', methods=['POST'])
def calendar_tool_route():
    """Endpoint for Calendar tool calls"""
    data = request.json
    print(f"🗓️ CALENDAR TOOL REQUEST: {data}")
    
    # Extract tool call info
    tool_call_id = None
    function_name = None
    args = {}
    
    try:
        # Standard VAPI tool call structure
        tool_calls = data.get('message', {}).get('toolCalls', [])
        if tool_calls:
            tool_call_id = tool_calls[0].get('id')
            function = tool_calls[0].get('function', {})
            function_name = function.get('name')
            args = function.get('arguments', {})
    except Exception as e:
        print(f"Error parsing tool data: {e}")

    result = "Error: Unknown tool."
    
    if function_name == 'check_availability':
        result = calendar_service.check_availability(
            args.get('start_time'), 
            args.get('end_time')
        )
    elif function_name == 'book_appointment':
        result = calendar_service.book_appointment(
            summary=args.get('summary'),
            start_time=args.get('start_time'),
            end_time=args.get('end_time'),
            attendee_email=args.get('attendee_email'),
            description=args.get('description', '')
        )
        
    print(f"🗓️ CALENDAR RESULT: {result}")

    return jsonify({
        "results": [{
            "toolCallId": tool_call_id,
            "result": result
        }]
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
