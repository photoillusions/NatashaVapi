import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
import json
import calendar_service
import crm_service

# Safe import for optional modules
try:
    import sheets_service
    HAS_SHEETS = True
except ImportError:
    HAS_SHEETS = False
    print("sheets_service not available - call logging to Sheets disabled")

app = Flask(__name__)

# --- CONFIGURATION ---
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME")
CLICKSEND_API_KEY = os.environ.get("CLICKSEND_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

# =====================================================
# SYSTEM PROMPT v9.0
# =====================================================
SYSTEM_PROMPT = """
# Jessica — Booking Concierge for Natasha Mae's Enterprises
**Tone:** Warm, elegant, polished, and efficient. "Where we create unforgettable memories."

## VENUES
1. **Frankford Ave** (Philly) — Intimate events, up to 100 guests.
2. **Liberty Palace** (Franklin Mills) — Grand ballroom, 150-250 guests.
3. **The Vault** (Burlington, NJ) — Historic luxury venue with original bank vault doors.

## EARLY BIRD SPECIAL
Available at The Vault and Liberty Palace:
- Events starting between 9 AM and 4 PM: **50% OFF venue rental**
- Events at 5 PM or later: Regular pricing
Mention this proactively when discussing pricing or when a customer seems budget-conscious.

## VOICE RULES — NEVER VIOLATE
- **NEVER read URLs, links, confirmation codes, or event IDs aloud.**
- First mention of the website: spell it as "w w w dot natasha maes dot com"
- After that: say "natashamaes dot com" naturally
- Say email as "info at natasha maes dot com"
- **NEVER read dates in ISO format.** Say "Saturday, June 15th at 6 PM" not "2026-06-15T18:00:00"
- If a tool returns an error, DO NOT read the error. Say: "I'm having a little trouble with our system. Let me take your information and have our team confirm your booking shortly."

## SMS TOOL — send_sms_link
If the caller wants info texted to them, call `send_sms_link` IMMEDIATELY. Do NOT ask for their number — you already have it.
Types: tour, packages, registration, invoice, vault_map, liberty_map, frankford_map

## CALENDAR TOOLS

### How to format times:
- ALL times must be ISO 8601 with Eastern timezone offset
- March through November (EDT): use -04:00
- November through March (EST): use -05:00
- Always assume year 2026 unless stated otherwise

### Event Durations (to calculate end_time from start_time):
- **VIP Tours:** 1 hour. Set is_event=false.
- **Corporate Events:** 4 hours. Set is_event=true.
- **Weddings, Sweet 16s, Repasts, Birthday Parties:** 6 hours. Set is_event=true.
- For events (is_event=true), we automatically add 1-hour setup before and 1-hour cleanup after on the calendar.
- Tell the customer: "Our event packages include setup and cleanup time at no extra cost."

### Step 1 — Check Availability:
Call `check_availability` with start_time, end_time, and is_event.
Example — wedding on June 15 at 6 PM (6 hours = ends at midnight):
→ check_availability(start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)

Example — tour on March 10 at 2 PM (1 hour):
→ check_availability(start_time: "2026-03-10T14:00:00-04:00", end_time: "2026-03-10T15:00:00-04:00", is_event: false)

### Step 2 — Get Customer Name (if not already given)

### Step 3 — Book:
Call `book_appointment` with summary, start_time, end_time, is_event.
→ book_appointment(summary: "Wedding - The Vault - Sarah Johnson", start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)

### Step 4 — Confirm naturally:
"You're all set! Your wedding at The Vault is booked for Saturday, June 15th starting at 6 PM."

## PRICING OVERVIEW
Do NOT quote exact prices unless specifically asked. Offer to text the packages brochure instead.
- The Vault: Saturdays from $3,795 | Fridays/Sundays from $2,500
- Liberty Palace: Weekends from $3,000
- Frankford Ave: Starting at $1,000

## CONVERSATION STYLE
- Be concise — this is a phone call, not an email
- Ask ONE question at a time, not numbered lists
- Don't repeat back everything the customer said like a checklist
- Move the conversation forward naturally
- Always identify which venue they want FIRST before discussing anything else
"""

# =====================================================
# HEALTH CHECK
# =====================================================
@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Enterprise Server v9.0 — Online"

@app.route('/debug', methods=['GET'])
def debug_status():
    def mask(val):
        return f"{val[:4]}...{val[-4:]}" if val and len(val) > 8 else ("SET" if val else "MISSING")
    return jsonify({
        "version": "9.0",
        "email_sender": mask(EMAIL_SENDER),
        "email_receiver": mask(EMAIL_RECEIVER),
        "clicksend_user": mask(CLICKSEND_USERNAME),
        "clicksend_key": mask(CLICKSEND_API_KEY),
        "sheets_id": mask(GOOGLE_SHEET_ID),
        "sheets_module": HAS_SHEETS,
        "calendar_id": mask(os.environ.get("CALENDAR_ID")),
        "service_account": "SET" if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") else "MISSING"
    })

# =====================================================
# MAIN INBOUND ROUTE
# =====================================================
@app.route('/inbound', methods=['POST'])
def inbound_call():
    data = request.json or {}
    message_type = data.get('message', {}).get('type')
    print(f"HIT /inbound - TYPE: {message_type}")

    # --- END OF CALL REPORT ---
    if message_type == 'end-of-call-report':
        try:
            call = data.get('message', data)
            summary = call.get('summary', 'No summary.')
            transcript = call.get('transcript', 'No transcript.')
            print(f"TRANSCRIPT:\n{transcript}")

            if EMAIL_SENDER and EMAIL_PASSWORD:
                msg = MIMEMultipart()
                msg['From'] = f"Natasha AI <{EMAIL_SENDER}>"
                msg['To'] = EMAIL_RECEIVER
                msg['Subject'] = "New Inquiry: Natasha Mae's"
                body = f"Call Summary:\n{summary}\n\n---\n\nTranscript:\n{transcript}"
                msg.attach(MIMEText(body, 'plain'))
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()

            if HAS_SHEETS and GOOGLE_SHEET_ID:
                print(f"Logging call to Google Sheet: {GOOGLE_SHEET_ID}")
                customer = data.get('message', {}).get('call', {}).get('customer', {})
                name = customer.get('name', 'Unknown')
                phone = customer.get('number', 'N/A')
                duration = data.get('message', {}).get('call', {}).get('duration', '0')
                disposition = data.get('message', {}).get('call', {}).get('endedReason', 'N/A')
                sheets_service.log_call_to_sheet(
                    GOOGLE_SHEET_ID,
                    [name, phone, summary, f"{duration}s", disposition]
                )
        except Exception as e:
            print(f"Reporting Failed: {e}")
        return jsonify({"status": "OK"}), 200

    # --- ASSISTANT REQUEST ---
    if message_type == 'assistant-request':
        response = {
            "assistant": {
                "firstMessage": "Thank you for calling Natasha Mae's Enterprises. This is Jessica. Are you inquiring about our Philadelphia locations or The Vault in New Jersey?",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "send_sms_link",
                                "description": "Sends a text message with a clickable link. REQUIRED whenever user asks for text/info.",
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
                                "description": "Checks if a specific date/time slot is available on the calendar.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "start_time": {"type": "string", "description": "ISO 8601 start datetime with timezone, e.g. 2026-06-15T18:00:00-04:00"},
                                        "end_time": {"type": "string", "description": "ISO 8601 end datetime with timezone, e.g. 2026-06-16T00:00:00-04:00"},
                                        "is_event": {"type": "boolean", "description": "true for events/weddings (adds setup+cleanup buffers), false for tours"}
                                    },
                                    "required": ["start_time", "end_time", "is_event"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "book_appointment",
                                "description": "Books a tour or event on the calendar after availability is confirmed.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "summary": {"type": "string", "description": "Event title: 'EventType - Venue - CustomerName'"},
                                        "start_time": {"type": "string", "description": "ISO 8601 start datetime with timezone"},
                                        "end_time": {"type": "string", "description": "ISO 8601 end datetime with timezone"},
                                        "is_event": {"type": "boolean", "description": "true for events (adds buffers), false for tours"},
                                        "attendee_email": {"type": "string", "description": "Optional: customer email for calendar invite"},
                                        "description": {"type": "string", "description": "Optional: notes about the booking"}
                                    },
                                    "required": ["summary", "start_time", "end_time", "is_event"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        }
                    ]
                },
                "serverMessages": ["conversation-update", "end-of-call-report", "speech-update", "status-update", "tool-calls"],
                "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "en-US"},
                "voice": {"provider": "11labs", "voiceId": "EXAVITQu4vr4xnSDxMaL"}
            }
        }

        # CRM History Injection
        try:
            phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
            if not phone:
                phone = data.get('message', {}).get('customer', {}).get('number')
            if phone:
                print(f"CRM lookup for: {phone}")
                customer_data = crm_service.get_customer(phone)
                if customer_data:
                    history_text = crm_service.format_history_for_prompt(customer_data)
                    response["assistant"]["model"]["messages"][0]["content"] += history_text
                    print(f"CRM history injected for {phone}")
        except Exception as e:
            print(f"CRM Lookup Failed (non-fatal): {e}")

        return jsonify(response), 200

    # --- TOOL CALLS (fallback for SMS) ---
    if message_type == 'tool-calls':
        return handle_tool_call(data)

    return jsonify({"status": "acknowledged"}), 200

# =====================================================
# CLICKSEND SMS HANDLER
# =====================================================
def handle_tool_call(data):
    print("TRIGGERING CLICKSEND SMS...")

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

    phone_raw = None
    try:
        phone_raw = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
        if not phone_raw:
            phone_raw = data.get('message', {}).get('customer', {}).get('number')
    except:
        pass
    if not phone_raw:
        phone_raw = args.get('phone')

    phone = str(phone_raw).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
    if len(phone) == 10:
        phone = "1" + phone
    if not phone.startswith("+"):
        phone = "+" + phone

    req_type = args.get('type', 'default').lower()
    message_map = {
        "tour": "Natasha Mae's: Schedule your VIP tour here: https://www.natashamaes.com/contact-us",
        "packages": "Natasha Mae's: View our full packages: https://www.natashamaes.com/packages",
        "registration": "Natasha Mae's: Register here: https://www.natashamaes.com/register",
        "invoice": "Natasha Mae's: View your invoice: https://www.natashamaes.com/payment",
        "vault_map": "The Vault: 120 High St, Burlington NJ - GPS: https://maps.app.goo.gl/vaultburlington",
        "liberty_map": "Liberty Palace: Franklin Mills - GPS: https://maps.app.goo.gl/libertypalace",
        "frankford_map": "Frankford Ave: 4500 Frankford Ave, Philly - GPS: https://maps.app.goo.gl/frankfordave",
        "default": "Natasha Mae's: Visit us at https://www.natashamaes.com"
    }
    message_body = message_map.get(req_type, message_map["default"])

    result_message = ""

    if not CLICKSEND_USERNAME or not CLICKSEND_API_KEY:
        result_message = "Error: Missing ClickSend credentials"
        print("MISSING CLICKSEND CREDENTIALS")
    else:
        try:
            payload = {
                "messages": [{
                    "body": message_body,
                    "to": phone,
                    "from": "",
                    "source": "sdk"
                }]
            }
            resp = requests.post(
                "https://rest.clicksend.com/v3/sms/send",
                auth=(CLICKSEND_USERNAME, CLICKSEND_API_KEY),
                json=payload,
                timeout=15
            )
            print(f"ClickSend Response: {resp.status_code}")
            if resp.status_code == 200:
                result_message = f"SMS sent successfully to {phone}"
            else:
                result_message = f"SMS send failed: {resp.status_code}"
                print(f"ClickSend Error: {resp.text}")
        except Exception as e:
            result_message = f"SMS error: {str(e)}"
            print(f"ClickSend Exception: {e}")

    return jsonify({
        "results": [{
            "toolCallId": tool_call_id,
            "result": result_message
        }]
    }), 200

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    """Direct endpoint for SMS tool calls from VAPI"""
    return handle_tool_call(request.json or {})

# =====================================================
# CALENDAR TOOL HANDLER
# =====================================================
@app.route('/calendar-tool', methods=['POST'])
def calendar_tool_route():
    """Endpoint for check_availability and book_appointment"""
    data = request.json or {}
    print("CALENDAR TOOL REQUEST")

    tool_call_id = None
    function_name = None
    args = {}

    try:
        tool_calls = data.get('message', {}).get('toolCalls', [])
        if not tool_calls:
            tool_calls = data.get('message', {}).get('toolCallList', [])
        if tool_calls:
            tool_call_id = tool_calls[0].get('id')
            function = tool_calls[0].get('function', {})
            function_name = function.get('name')
            args = function.get('arguments', {})
            if not function_name:
                function_name = tool_calls[0].get('name')
                args = tool_calls[0].get('arguments', {})
    except Exception as e:
        print(f"Error parsing tool data: {e}")

    print(f"Function: {function_name} | Args: {json.dumps(args)}")
    result = "Error: Unknown calendar tool."

    try:
        if function_name == 'check_availability':
            start_iso = args.get('start_time')
            end_iso = args.get('end_time')
            is_event = args.get('is_event', False)

            if is_event:
                try:
                    from datetime import datetime, timedelta
                    start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
                    start_iso = (start_dt - timedelta(hours=1)).isoformat()
                    end_iso = (end_dt + timedelta(hours=1)).isoformat()
                    print(f"Event buffer applied: checking {start_iso} to {end_iso}")
                except:
                    pass

            result = calendar_service.check_availability(start_iso, end_iso)
            print(f"Availability result: {result}")

        elif function_name == 'book_appointment':
            start_iso = args.get('start_time') or args.get('start_time_iso')
            end_iso = args.get('end_time') or args.get('end_time_iso')
            is_event = args.get('is_event', False)

            if is_event:
                try:
                    from datetime import datetime, timedelta
                    start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
                    start_iso = (start_dt - timedelta(hours=1)).isoformat()
                    end_iso = (end_dt + timedelta(hours=1)).isoformat()
                    print(f"Event booking: blocking {start_iso} to {end_iso} (with buffers)")
                except Exception as e:
                    print(f"Buffer calc failed: {e}")

            result = calendar_service.book_appointment(
                args.get('summary'),
                start_iso,
                end_iso,
                args.get('attendee_email'),
                args.get('description', '')
            )
            print(f"Booking result: {result}")

    except Exception as e:
        result = f"Error: {str(e)}"
        print(f"Calendar Tool Error: {e}")

    return jsonify({
        "results": [{
            "toolCallId": tool_call_id,
            "result": result
        }]
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
