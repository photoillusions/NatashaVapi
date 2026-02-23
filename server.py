import os
import smtplib
import requests
import json
import traceback
import tempfile
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import Flask, request, jsonify

# ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("reportlab not available - PDF generation disabled")

import calendar_service
import crm_service

try:
    import sheets_service
    HAS_SHEETS = True
except ImportError:
    HAS_SHEETS = False
    print("sheets_service not available - Sheets logging disabled")

app = Flask(__name__)

# --- CONFIGURATION ---
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME")
CLICKSEND_API_KEY = os.environ.get("CLICKSEND_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")

VENUE_ADDRESSES = {
    'the vault': '120 High Street, Burlington, NJ 08016',
    'vault': '120 High Street, Burlington, NJ 08016',
    'liberty palace': '1 Franklin Mills Blvd, Philadelphia, PA 19154',
    'liberty': '1 Franklin Mills Blvd, Philadelphia, PA 19154',
    'frankford ave': '4500 Frankford Ave, Philadelphia, PA 19124',
    'frankford': '4500 Frankford Ave, Philadelphia, PA 19124',
    'banquet': '4500 Frankford Ave, Philadelphia, PA 19124',
}

# =====================================================
# SYSTEM PROMPT v10.0 — Full Feature
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
- **NEVER read card numbers back.** Just confirm last 4 digits.
- If a tool returns an error, DO NOT read the error. Say: "I'm having a little trouble with our system. Let me take your information and have our team confirm shortly."

## SMS TOOL — send_sms_link
If the caller wants info texted to them, call `send_sms_link` IMMEDIATELY. Do NOT ask for their number — you already have it.
Types: tour, packages, registration, invoice, vault_map, liberty_map, frankford_map

## CALENDAR TOOLS

### Time Formatting:
- ALL times: ISO 8601 with Eastern timezone
- March-November (EDT): -04:00
- November-March (EST): -05:00
- Assume year 2026 unless stated otherwise

### Event Durations (calculate end_time):
- **VIP Tours:** 1 hour. is_event=false.
- **Corporate Events:** 4 hours. is_event=true.
- **Weddings, Sweet 16s, Repasts, Birthday Parties:** 6 hours. is_event=true.
- For events, we add 1-hour setup + 1-hour cleanup automatically.

### Booking Flow:
1. Call `check_availability(start_time, end_time, is_event)`
2. If available, get customer name
3. Call `book_appointment(summary, start_time, end_time, is_event)`
4. Confirm naturally: "You're all set for Saturday, June 15th at 6 PM!"

Example — Wedding June 15 at 6 PM:
→ check_availability(start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)
→ book_appointment(summary: "Wedding - The Vault - Sarah Johnson", start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)

## PAYMENT — process_payment
When a customer is ready to secure their date with a deposit:
1. Confirm the amount (e.g. 50% deposit)
2. Collect card info ONE field at a time conversationally:
   - "May I have the card number?"
   - "Expiration date?"
   - "The three-digit security code on the back?"
   - "And the billing zip code?"
3. Call `process_payment` with all fields
4. If successful, call `send_booking_email` to send confirmation
5. Then call `book_appointment` to add to calendar

## BOOKING EMAIL — send_booking_email
After successful payment, call this to send a confirmation email with PDF receipt to customer AND management.

## CONTRACT PDF — get_contract_pdf
If a customer asks for a contract, call `get_contract_pdf` with the venue name. This generates a PDF and texts the link.

## PRICING OVERVIEW
Offer to text the packages brochure rather than quoting exact prices.
- The Vault: Saturdays from $3,795 | Fridays/Sundays from $2,500 | 50% deposit required
- Liberty Palace: Weekends from $3,000
- Frankford Ave: Starting at $1,000
- Security guard mandatory for all events ($35/hr)
- Balance due 10 days before event

## CONVERSATION STYLE
- Be concise — this is a phone call, not an email
- Ask ONE question at a time
- Don't repeat everything back like a checklist
- Move the conversation forward naturally
- Identify which venue FIRST before discussing anything else
"""

# =====================================================
# HEALTH CHECK
# =====================================================
@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Enterprise Server v10.0 — Online"

@app.route('/debug', methods=['GET'])
def debug_status():
    def mask(val):
        return f"{val[:4]}...{val[-4:]}" if val and len(val) > 8 else ("SET" if val else "MISSING")
    return jsonify({
        "version": "10.0",
        "email_sender": mask(EMAIL_SENDER),
        "email_receiver": mask(EMAIL_RECEIVER),
        "clicksend_user": mask(CLICKSEND_USERNAME),
        "clicksend_key": mask(CLICKSEND_API_KEY),
        "sheets_id": mask(GOOGLE_SHEET_ID),
        "sheets_module": HAS_SHEETS,
        "calendar_id": mask(os.environ.get("CALENDAR_ID")),
        "service_account": "SET" if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") else "MISSING",
        "stripe_key": mask(STRIPE_SECRET_KEY),
        "supabase_url": mask(os.environ.get("SUPABASE_URL")),
        "supabase_key": mask(os.environ.get("SUPABASE_KEY")),
        "reportlab": HAS_REPORTLAB
    })

# =====================================================
# PDF GENERATION
# =====================================================
def generate_pdf_receipt(data, filename):
    """Generate a PDF receipt/contract using ReportLab."""
    if not HAS_REPORTLAB:
        return False

    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Natasha Mae's Enterprises", styles['Title']))
    elements.append(Paragraph("Booking Confirmation & Receipt", styles['Heading2']))
    elements.append(Spacer(1, 12))

    details = [
        ["Customer Name", data.get('customer_name', 'N/A')],
        ["Email", data.get('customer_email', 'N/A')],
        ["Phone", data.get('customer_phone', 'N/A')],
        ["Event Type", data.get('event_type', 'N/A')],
        ["Venue", data.get('venue', 'N/A')],
        ["Venue Address", data.get('venue_address', 'N/A')],
        ["Date", data.get('event_date', 'N/A')],
        ["Time", data.get('event_time', 'N/A')],
        ["Guests", str(data.get('guest_count', 'N/A'))],
        ["Confirmation #", data.get('confirmation_number', 'N/A')],
        ["", ""],
        ["Total Rental", f"${data.get('total_price', '0')}"],
        ["Deposit Paid", f"${data.get('deposit_paid', '0')}"],
        ["Balance Due", f"${data.get('balance_due', '0')}"],
    ]

    if data.get('early_bird'):
        details.insert(-3, ["Early Bird Discount", "50% OFF Applied"])

    t = Table(details, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("Terms & Conditions:", styles['Heading3']))
    terms = [
        "Deposits are non-refundable.",
        "Balance due 10 days before event.",
        "Security guard mandatory for all events ($35/hr).",
        "Event includes 1-hour setup and 1-hour cleanup at no extra cost.",
        "Cancellations must be made 30 days in advance for date transfer.",
    ]
    for term in terms:
        elements.append(Paragraph(f"• {term}", styles['Normal']))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Thank you for choosing Natasha Mae's Enterprises!", styles['Normal']))
    elements.append(Paragraph("www.natashamaes.com | info@natashamaes.com", styles['Normal']))

    doc.build(elements)
    return True

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
                customer = data.get('message', {}).get('call', {}).get('customer', {})
                sheets_service.log_call_to_sheet(GOOGLE_SHEET_ID, [
                    customer.get('name', 'Unknown'),
                    customer.get('number', 'N/A'),
                    summary,
                    f"{data.get('message', {}).get('call', {}).get('duration', '0')}s",
                    data.get('message', {}).get('call', {}).get('endedReason', 'N/A')
                ])
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
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "send_sms_link",
                                "description": "Sends a text message with a clickable link. REQUIRED whenever user asks for text/info.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string", "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"]}
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
                                        "attendee_email": {"type": "string", "description": "Optional: customer email"},
                                        "description": {"type": "string", "description": "Optional: booking notes"}
                                    },
                                    "required": ["summary", "start_time", "end_time", "is_event"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "process_payment",
                                "description": "Process a credit card payment via Stripe. Collect card number, expiration month (MM), year (YY), CVV, and billing zip.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "amount": {"type": "string", "description": "Amount in dollars, e.g. '1897.50'"},
                                        "card_number": {"type": "string", "description": "Full card number"},
                                        "exp_month": {"type": "string", "description": "Expiration month MM"},
                                        "exp_year": {"type": "string", "description": "Expiration year YY"},
                                        "cvc": {"type": "string", "description": "3 or 4 digit security code"},
                                        "zip": {"type": "string", "description": "Billing zip code"},
                                        "customer_name": {"type": "string", "description": "Customer full name"},
                                        "customer_email": {"type": "string", "description": "Customer email"},
                                        "event_type": {"type": "string", "description": "Wedding, Sweet 16, Corporate, etc."},
                                        "venue": {"type": "string", "description": "The Vault, Liberty Palace, or Frankford Ave"},
                                        "event_date": {"type": "string", "description": "Event date"},
                                        "event_time": {"type": "string", "description": "Event start time"},
                                        "guest_count": {"type": "string", "description": "Estimated guest count"},
                                        "description": {"type": "string", "description": "Optional notes"}
                                    },
                                    "required": ["amount", "card_number", "exp_month", "exp_year", "cvc", "zip", "customer_name", "customer_email"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/payment-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "send_booking_email",
                                "description": "Send booking confirmation and receipt emails to customer and management after successful payment.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_name": {"type": "string"},
                                        "customer_email": {"type": "string"},
                                        "customer_phone": {"type": "string"},
                                        "event_type": {"type": "string"},
                                        "venue": {"type": "string"},
                                        "venue_address": {"type": "string"},
                                        "event_date": {"type": "string"},
                                        "event_time": {"type": "string"},
                                        "guest_count": {"type": "string"},
                                        "total_price": {"type": "string"},
                                        "deposit_paid": {"type": "string"},
                                        "balance_due": {"type": "string"},
                                        "early_bird": {"type": "boolean"},
                                        "confirmation_number": {"type": "string"}
                                    },
                                    "required": ["customer_name", "customer_email", "event_type", "venue", "event_date", "deposit_paid"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/booking-email-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "get_contract_pdf",
                                "description": "Generates a downloadable PDF contract for a specific venue and texts the link to the caller.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "venue": {"type": "string", "description": "vault, liberty, or banquet"}
                                    },
                                    "required": ["venue"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/contract-tool"}
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
                customer_data = crm_service.get_customer(phone)
                if customer_data:
                    history_text = crm_service.format_history_for_prompt(customer_data)
                    response["assistant"]["model"]["messages"][0]["content"] += history_text
                    print(f"CRM history injected for {phone}")
        except Exception as e:
            print(f"CRM Lookup Failed (non-fatal): {e}")

        return jsonify(response), 200

    # --- TOOL CALLS (fallback) ---
    if message_type == 'tool-calls':
        return handle_tool_call(data)

    return jsonify({"status": "acknowledged"}), 200

# =====================================================
# SMS HANDLER
# =====================================================
def handle_tool_call(data):
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
        "confirmation": args.get('message', "Natasha Mae's: Your booking is confirmed! Check your email for details."),
        "default": "Natasha Mae's: Visit us at https://www.natashamaes.com"
    }
    message_body = message_map.get(req_type, message_map["default"])
    result_message = send_clicksend_sms(phone, message_body)

    return jsonify({
        "results": [{"toolCallId": tool_call_id, "result": result_message}]
    }), 200

def send_clicksend_sms(phone, message_body):
    """Send SMS via ClickSend API"""
    if not CLICKSEND_USERNAME or not CLICKSEND_API_KEY:
        print("MISSING CLICKSEND CREDENTIALS")
        return "Error: SMS service unavailable"
    try:
        resp = requests.post(
            "https://rest.clicksend.com/v3/sms/send",
            auth=(CLICKSEND_USERNAME, CLICKSEND_API_KEY),
            json={"messages": [{"body": message_body, "to": phone, "from": "", "source": "sdk"}]},
            timeout=15
        )
        if resp.status_code == 200:
            return f"SMS sent successfully to {phone}"
        else:
            print(f"ClickSend Error: {resp.text}")
            return f"SMS send failed: {resp.status_code}"
    except Exception as e:
        print(f"ClickSend Exception: {e}")
        return f"SMS error: {str(e)}"

@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    return handle_tool_call(request.json or {})

# =====================================================
# CALENDAR TOOL HANDLER
# =====================================================
@app.route('/calendar-tool', methods=['POST'])
def calendar_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    print(f"CALENDAR: {function_name} | {json.dumps(args)}")
    result = "Error: Unknown calendar tool."

    try:
        if function_name == 'check_availability':
            start_iso = args.get('start_time')
            end_iso = args.get('end_time')
            is_event = args.get('is_event', False)

            if is_event:
                try:
                    s = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                    e = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
                    start_iso = (s - timedelta(hours=1)).isoformat()
                    end_iso = (e + timedelta(hours=1)).isoformat()
                except: pass

            result = calendar_service.check_availability(start_iso, end_iso)

        elif function_name == 'book_appointment':
            start_iso = args.get('start_time')
            end_iso = args.get('end_time')
            is_event = args.get('is_event', False)

            if is_event:
                try:
                    s = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                    e = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
                    start_iso = (s - timedelta(hours=1)).isoformat()
                    end_iso = (e + timedelta(hours=1)).isoformat()
                except: pass

            result = calendar_service.book_appointment(
                args.get('summary'), start_iso, end_iso,
                args.get('attendee_email'), args.get('description', '')
            )
    except Exception as e:
        result = f"Error: {str(e)}"
        print(f"Calendar Error: {e}")

    print(f"Calendar result: {result}")
    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# PAYMENT TOOL (Stripe)
# =====================================================
@app.route('/payment-tool', methods=['POST'])
def payment_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    print(f"PAYMENT: {json.dumps({k: v[:4]+'...' if k in ('card_number','cvc') and v else v for k,v in args.items()})}")
    result = "Error: Payment processing failed."

    if not STRIPE_SECRET_KEY:
        return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Payment system not configured"}]}), 200

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        amount_cents = int(float(args.get('amount', '0')) * 100)
        if amount_cents <= 0:
            return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Invalid amount"}]}), 200

        # Create payment method
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": args.get('card_number', '').replace(' ', '').replace('-', ''),
                "exp_month": int(args.get('exp_month', '1')),
                "exp_year": int(f"20{args.get('exp_year', '26')}" if len(args.get('exp_year', '')) == 2 else args.get('exp_year', '2026')),
                "cvc": args.get('cvc', ''),
            },
            billing_details={
                "name": args.get('customer_name', ''),
                "email": args.get('customer_email', ''),
                "address": {"postal_code": args.get('zip', '')}
            }
        )

        # Create and confirm payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method=pm.id,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            description=f"{args.get('event_type', 'Event')} at {args.get('venue', 'Natasha Maes')} - {args.get('customer_name', '')}",
            receipt_email=args.get('customer_email'),
            metadata={
                "customer_name": args.get('customer_name', ''),
                "event_type": args.get('event_type', ''),
                "venue": args.get('venue', ''),
                "event_date": args.get('event_date', ''),
            }
        )

        if intent.status == 'succeeded':
            conf_number = f"NME-{intent.id[-8:].upper()}"

            # Update CRM
            phone = None
            try:
                phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
            except: pass
            if phone:
                crm_service.upsert_customer(phone, {
                    "name": args.get('customer_name'),
                    "email": args.get('customer_email'),
                    "last_payment_amount": args.get('amount'),
                    "last_payment_date": datetime.now().strftime("%Y-%m-%d"),
                    "venue": args.get('venue'),
                    "event_type": args.get('event_type'),
                    "event_date": args.get('event_date'),
                    "confirmation_number": conf_number,
                })

            result = f"Payment of ${args.get('amount')} processed successfully. Confirmation number: {conf_number}"
        else:
            result = f"Payment requires additional action: {intent.status}"

    except stripe.error.CardError as e:
        result = f"Card declined: {e.user_message}"
        print(f"Stripe CardError: {e}")
    except Exception as e:
        result = f"Payment error: {str(e)}"
        print(f"Stripe Error: {traceback.format_exc()}")

    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# BOOKING EMAIL TOOL
# =====================================================
@app.route('/booking-email-tool', methods=['POST'])
def booking_email_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    print(f"BOOKING EMAIL for: {args.get('customer_name')}")
    result = "Error: Email send failed."

    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Email not configured"}]}), 200

    try:
        # Resolve venue address
        venue_lower = args.get('venue', '').lower()
        venue_address = args.get('venue_address') or VENUE_ADDRESSES.get(venue_lower, 'See website for details')

        # Generate PDF receipt
        pdf_path = None
        if HAS_REPORTLAB:
            pdf_data = {**args, "venue_address": venue_address}
            pdf_path = tempfile.mktemp(suffix='.pdf')
            generate_pdf_receipt(pdf_data, pdf_path)

        # Build email body
        body = f"""Booking Confirmation — Natasha Mae's Enterprises

Customer: {args.get('customer_name', 'N/A')}
Email: {args.get('customer_email', 'N/A')}
Phone: {args.get('customer_phone', 'N/A')}

Event: {args.get('event_type', 'N/A')}
Venue: {args.get('venue', 'N/A')}
Address: {venue_address}
Date: {args.get('event_date', 'N/A')}
Time: {args.get('event_time', 'N/A')}
Guests: {args.get('guest_count', 'N/A')}

Total: ${args.get('total_price', '0')}
Deposit Paid: ${args.get('deposit_paid', '0')}
Balance Due: ${args.get('balance_due', '0')}
{"Early Bird 50% OFF Applied!" if args.get('early_bird') else ""}

Confirmation: {args.get('confirmation_number', 'N/A')}

Thank you for choosing Natasha Mae's Enterprises!
www.natashamaes.com
"""

        # Send to customer
        for recipient, subject in [
            (args.get('customer_email'), f"Booking Confirmed! {args.get('event_type', 'Event')} at {args.get('venue', 'Natasha Maes')}"),
            (EMAIL_RECEIVER, f"NEW BOOKING: {args.get('customer_name')} - {args.get('event_type')} at {args.get('venue')}")
        ]:
            if not recipient:
                continue
            msg = MIMEMultipart()
            msg['From'] = f"Natasha Mae's <{EMAIL_SENDER}>"
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_attach = MIMEApplication(f.read(), _subtype='pdf')
                    pdf_attach.add_header('Content-Disposition', 'attachment', filename='NatashaMaes_Confirmation.pdf')
                    msg.attach(pdf_attach)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

        # Clean up temp PDF
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)

        result = f"Confirmation email sent to {args.get('customer_email')} and management."

    except Exception as e:
        result = f"Email error: {str(e)}"
        print(f"Booking Email Error: {traceback.format_exc()}")

    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# CONTRACT PDF TOOL
# =====================================================
@app.route('/contract-tool', methods=['POST'])
def contract_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    venue = args.get('venue', 'vault').lower()
    print(f"CONTRACT PDF for venue: {venue}")

    # For now, text them the packages link (PDF hosting TBD)
    phone_raw = None
    try:
        phone_raw = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
    except: pass

    if phone_raw:
        phone = str(phone_raw).replace("-","").replace(" ","").replace("(","").replace(")","").replace("+","")
        if len(phone) == 10: phone = "1" + phone
        if not phone.startswith("+"): phone = "+" + phone
        sms_result = send_clicksend_sms(phone, f"Natasha Mae's: View contracts and pricing: https://www.natashamaes.com/pricing")
        result = f"Contract info texted to caller. {sms_result}"
    else:
        result = "Contract info available at natashamaes.com/pricing"

    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# UTILITY: Extract tool call from VAPI payload
# =====================================================
def extract_tool_call(data):
    """Extract tool_call_id, function_name, and args from VAPI payload."""
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
    return tool_call_id, function_name, args

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
