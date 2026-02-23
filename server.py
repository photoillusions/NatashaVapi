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

try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

import calendar_service
import crm_service

try:
    import sheets_service
    HAS_SHEETS = True
except ImportError:
    HAS_SHEETS = False

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
# SYSTEM PROMPT v11.0
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
Mention this when discussing pricing or when a customer seems budget-conscious.

## VOICE RULES — NEVER VIOLATE
- **NEVER offer to text or SMS the customer. We do NOT text. Email only.**
- **NEVER read URLs, links, confirmation codes, or event IDs aloud.**
- First mention of the website: spell it as "w w w dot natasha maes dot com"
- After that: say "natashamaes dot com" naturally
- Say email as "info at natasha maes dot com"
- **NEVER read dates in ISO format.** Say "Saturday, June 15th at 6 PM" not "2026-06-15T18:00:00"
- **NEVER read card numbers back.** Just confirm last 4 digits.
- If a tool returns an error, DO NOT read the error. Say: "I'm having a little trouble with our system. Let me take your information and have our team follow up shortly."

## PACKAGES — EXPLAIN ON THE CALL
When a customer asks about packages or pricing, give them a quick overview:

**The Vault (Burlington, NJ):**
- Saturdays from $3,795 | Fridays & Sundays from $2,500
- Early Bird (before 4 PM): 50% off venue rental
- Includes tables, chairs, linens, setup and cleanup time

**Liberty Palace (Franklin Mills):**
- Weekends from $3,000
- Early Bird available
- Open floor plan, outdoor patio, free parking

**Frankford Ave (Philly):**
- Starting at $1,000
- Perfect for intimate gatherings under 100 guests

**All Venues Include:**
- 1-hour setup before and 1-hour cleanup after at no extra cost
- Security guard required for all events ($35/hr)
- 50% deposit required to lock your date
- Balance due 10 days before event

If the customer wants MORE detailed information (full brochure, menu options, add-ons), collect their info and email it:
1. Ask for their **name**
2. Ask for their **email address**
3. Ask for their **phone number**
4. Call `send_info_email` to email them the full package details

## CALENDAR — PENCIL IN vs LOCK

**IMPORTANT DISTINCTION:**
- **Pencil in** = We hold the date temporarily. No payment required. This is NOT a guaranteed reservation.
- **Lock the date** = Customer pays 50% deposit. Date is officially secured and guaranteed.

### Flow when customer wants a date:
1. Call `check_availability(start_time, end_time, is_event)` to see if the date is free
2. If available and customer wants to proceed:
   - Ask: "Would you like to go ahead and secure this date with a deposit, or would you like me to pencil you in while you finalize your plans?"
   - **If they want to pencil in:** Get their name, call `book_appointment` with summary starting with "PENCILED - ". Tell them: "I've penciled you in for [date]. Just keep in mind, the date isn't officially locked until we receive the 50% deposit."
   - **If they want to lock/secure it:** Collect payment via `process_payment`, THEN call `book_appointment` with summary starting with "CONFIRMED - ". Then call `send_booking_email`.

### Time Formatting:
- ALL times: ISO 8601 with Eastern timezone
- March-November (EDT): -04:00
- November-March (EST): -05:00
- Assume year 2026 unless stated otherwise

### Event Durations (calculate end_time):
- **VIP Tours:** 1 hour. is_event=false.
- **Corporate Events:** 4 hours. is_event=true.
- **Weddings, Sweet 16s, Repasts, Birthday Parties:** 6 hours. is_event=true.

### Examples:
Pencil in a wedding June 15 at 6 PM:
→ check_availability(start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)
→ book_appointment(summary: "PENCILED - Wedding - The Vault - Sarah Johnson", start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)

Lock a wedding after payment:
→ book_appointment(summary: "CONFIRMED - Wedding - The Vault - Sarah Johnson", start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-16T00:00:00-04:00", is_event: true)

## PAYMENT — process_payment
Only when customer wants to LOCK their date with a deposit:
1. Confirm the deposit amount (50% of venue rental)
2. Collect card info ONE field at a time:
   - "May I have the card number?"
   - "Expiration date?"
   - "The three-digit security code on the back?"
   - "And the billing zip code?"
3. Call `process_payment`
4. If successful, call `book_appointment` with "CONFIRMED" prefix
5. Call `send_booking_email` to send confirmation

## CONVERSATION STYLE
- Be concise — this is a phone call, not an email
- Ask ONE question at a time
- Don't repeat everything back like a checklist
- Move the conversation forward naturally
- Identify which venue FIRST before discussing anything else
- NEVER mention texting or SMS — we only communicate via email and phone
"""

# =====================================================
# HEALTH CHECK
# =====================================================
@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Enterprise Server v11.0 — Online"

@app.route('/debug', methods=['GET'])
def debug_status():
    def mask(val):
        return f"{val[:4]}...{val[-4:]}" if val and len(val) > 8 else ("SET" if val else "MISSING")
    return jsonify({
        "version": "11.0",
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
        ["Address", data.get('venue_address', 'N/A')],
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
    for term in [
        "Deposits are non-refundable.",
        "Balance due 10 days before event.",
        "Security guard mandatory ($35/hr).",
        "Includes 1-hour setup and 1-hour cleanup at no extra cost.",
        "Cancellations must be made 30 days in advance for date transfer.",
    ]:
        elements.append(Paragraph(f"* {term}", styles['Normal']))
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
                    "model": "gpt-5-mini",
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                    "tools": [
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
                                        "is_event": {"type": "boolean", "description": "true for events/weddings, false for tours"}
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
                                "description": "Books or pencils in a date on the calendar. Use 'PENCILED - ' prefix for holds, 'CONFIRMED - ' prefix for paid bookings.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "summary": {"type": "string", "description": "Event title: 'PENCILED - EventType - Venue - Name' or 'CONFIRMED - EventType - Venue - Name'"},
                                        "start_time": {"type": "string", "description": "ISO 8601 start datetime with timezone"},
                                        "end_time": {"type": "string", "description": "ISO 8601 end datetime with timezone"},
                                        "is_event": {"type": "boolean", "description": "true for events, false for tours"},
                                        "attendee_email": {"type": "string", "description": "Optional: customer email"},
                                        "description": {"type": "string", "description": "Optional: booking notes, phone number, guest count"}
                                    },
                                    "required": ["summary", "start_time", "end_time", "is_event"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "send_info_email",
                                "description": "Emails the customer detailed package and pricing information for their venue of interest.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_name": {"type": "string", "description": "Customer full name"},
                                        "customer_email": {"type": "string", "description": "Customer email address"},
                                        "customer_phone": {"type": "string", "description": "Customer phone number"},
                                        "venue": {"type": "string", "description": "The Vault, Liberty Palace, or Frankford Ave"},
                                        "event_type": {"type": "string", "description": "Wedding, Sweet 16, Corporate, Birthday, etc."},
                                        "notes": {"type": "string", "description": "Any additional details from the conversation"}
                                    },
                                    "required": ["customer_name", "customer_email", "venue"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/info-email-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "process_payment",
                                "description": "Process a credit card deposit payment via Stripe to LOCK a date. Only use when customer is ready to pay 50% deposit.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "amount": {"type": "string", "description": "Deposit amount in dollars, e.g. '1897.50'"},
                                        "card_number": {"type": "string", "description": "Full card number"},
                                        "exp_month": {"type": "string", "description": "Expiration month MM"},
                                        "exp_year": {"type": "string", "description": "Expiration year YY"},
                                        "cvc": {"type": "string", "description": "3 or 4 digit security code"},
                                        "zip": {"type": "string", "description": "Billing zip code"},
                                        "customer_name": {"type": "string", "description": "Customer full name"},
                                        "customer_email": {"type": "string", "description": "Customer email"},
                                        "event_type": {"type": "string", "description": "Wedding, Sweet 16, etc."},
                                        "venue": {"type": "string", "description": "Venue name"},
                                        "event_date": {"type": "string", "description": "Event date"},
                                        "event_time": {"type": "string", "description": "Event start time"},
                                        "guest_count": {"type": "string", "description": "Estimated guests"}
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
                                "description": "Send booking confirmation email with PDF receipt after successful payment. ONLY use after process_payment succeeds.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_name": {"type": "string"},
                                        "customer_email": {"type": "string"},
                                        "customer_phone": {"type": "string"},
                                        "event_type": {"type": "string"},
                                        "venue": {"type": "string"},
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
        except Exception as e:
            print(f"CRM Lookup Failed: {e}")

        return jsonify(response), 200

    # --- TOOL CALLS (fallback) ---
    if message_type == 'tool-calls':
        return jsonify({"status": "acknowledged"}), 200

    return jsonify({"status": "acknowledged"}), 200

# =====================================================
# UTILITY: Extract tool call from VAPI payload
# =====================================================
def extract_tool_call(data):
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

# =====================================================
# CALENDAR TOOL
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
# INFO EMAIL TOOL (replaces SMS — sends package info)
# =====================================================
@app.route('/info-email-tool', methods=['POST'])
def info_email_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    print(f"INFO EMAIL for: {args.get('customer_name')} -> {args.get('customer_email')}")
    result = "Error: Email failed."

    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Email not configured"}]}), 200

    try:
        venue = args.get('venue', 'our venues')
        venue_lower = venue.lower()
        venue_address = VENUE_ADDRESSES.get(venue_lower, 'See website')
        event_type = args.get('event_type', 'your event')
        notes = args.get('notes', '')

        body = f"""Hi {args.get('customer_name', '')},

Thank you for your interest in hosting your {event_type} at {venue}! Here are our package details:

{'=' * 50}
VENUE: {venue}
ADDRESS: {venue_address}
{'=' * 50}

"""
        if 'vault' in venue_lower:
            body += """THE VAULT — Burlington, NJ
Historic luxury venue with original bank vault doors.

PRICING:
  Saturday Events: Starting at $3,795
  Friday & Sunday Events: Starting at $2,500
  Early Bird Special (9 AM - 4 PM): 50% OFF venue rental!

INCLUDED:
  - Tables, chairs, and linens
  - 1-hour setup before your event
  - 1-hour cleanup after your event
  - Access to historic bank vault room (perfect for photos!)
  - Manicured gardens with six-pillar runway

CAPACITY: Main Ballroom up to 250 guests | Vault Room II up to 100 guests
UNIQUE: Rare 5:00 AM alcohol license

"""
        elif 'liberty' in venue_lower:
            body += """LIBERTY PALACE — Franklin Mills, Philadelphia
Sophisticated open-concept grand ballroom.

PRICING:
  Weekend Events: Starting at $3,000
  Early Bird Special (9 AM - 4 PM): 50% OFF venue rental!

INCLUDED:
  - Open floor plan for versatile layouts
  - Outdoor patio for cocktail hours
  - Abundant natural light
  - FREE on-site parking (rare in Philly area!)
  - 1-hour setup and 1-hour cleanup included

CAPACITY: Up to 210 guests

"""
        elif 'frankford' in venue_lower or 'banquet' in venue_lower:
            body += """FRANKFORD AVE BANQUET FACILITY — Philadelphia
Cozy and elegant urban space.

PRICING:
  Starting at $1,000
  Affordable community rates

INCLUDED:
  - Intimate, warm atmosphere
  - Transit-friendly (0.2 miles from SEPTA Church Station)
  - Setup and cleanup included

CAPACITY: 50-110 guests

"""
        else:
            body += """We have three stunning venues to choose from. Visit our website for full details on each location.

"""

        body += f"""REQUIREMENTS FOR ALL VENUES:
  - 50% deposit required to lock your date
  - Balance due 10 days before your event
  - Security guard mandatory ($35/hr)
  - Deposits are non-refundable

NEXT STEPS:
  1. Schedule a VIP tour to see the venue in person
  2. Choose your date and secure it with a 50% deposit
  3. We'll work with you on every detail!

Ready to tour? Call us back or visit www.natashamaes.com/contact-us

Looking forward to creating something unforgettable with you!

Warm regards,
Natasha Mae's Enterprises
www.natashamaes.com | info@natashamaes.com
"""

        # Send to customer
        msg = MIMEMultipart()
        msg['From'] = f"Natasha Mae's <{EMAIL_SENDER}>"
        msg['To'] = args.get('customer_email')
        msg['Subject'] = f"Package Info: {venue} — Natasha Mae's Enterprises"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        # Notify management
        mgmt_body = f"New lead from phone call:\nName: {args.get('customer_name')}\nEmail: {args.get('customer_email')}\nPhone: {args.get('customer_phone', 'N/A')}\nVenue: {venue}\nEvent: {event_type}\nNotes: {notes}"
        mgmt_msg = MIMEMultipart()
        mgmt_msg['From'] = f"Natasha AI <{EMAIL_SENDER}>"
        mgmt_msg['To'] = EMAIL_RECEIVER
        mgmt_msg['Subject'] = f"New Lead: {args.get('customer_name')} - {venue}"
        mgmt_msg.attach(MIMEText(mgmt_body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(mgmt_msg)
        server.quit()

        # Upsert to CRM
        phone = args.get('customer_phone')
        if not phone:
            try:
                phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
            except: pass
        if phone:
            crm_service.upsert_customer(phone, {
                "name": args.get('customer_name'),
                "email": args.get('customer_email'),
                "venue": venue,
                "event_type": event_type,
                "notes": f"Package info emailed. {notes}",
            })

        result = f"Package info emailed to {args.get('customer_email')} successfully."

    except Exception as e:
        result = f"Email error: {str(e)}"
        print(f"Info Email Error: {traceback.format_exc()}")

    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# PAYMENT TOOL (Stripe)
# =====================================================
@app.route('/payment-tool', methods=['POST'])
def payment_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    result = "Error: Payment processing failed."

    if not STRIPE_SECRET_KEY:
        return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Payment system not configured"}]}), 200

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        amount_cents = int(float(args.get('amount', '0')) * 100)
        if amount_cents <= 0:
            return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Invalid amount"}]}), 200

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

    except Exception as e:
        err_msg = getattr(e, 'user_message', str(e))
        result = f"Card declined: {err_msg}" if 'CardError' in type(e).__name__ else f"Payment error: {str(e)}"
        print(f"Stripe Error: {traceback.format_exc()}")

    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# BOOKING EMAIL TOOL (after payment — with PDF)
# =====================================================
@app.route('/booking-email-tool', methods=['POST'])
def booking_email_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    result = "Error: Email send failed."

    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return jsonify({"results": [{"toolCallId": tool_call_id, "result": "Error: Email not configured"}]}), 200

    try:
        venue_lower = args.get('venue', '').lower()
        venue_address = VENUE_ADDRESSES.get(venue_lower, 'See website for details')

        pdf_path = None
        if HAS_REPORTLAB:
            pdf_data = {**args, "venue_address": venue_address}
            pdf_path = tempfile.mktemp(suffix='.pdf')
            generate_pdf_receipt(pdf_data, pdf_path)

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

Your date is LOCKED and confirmed! Balance is due 10 days before your event.

Thank you for choosing Natasha Mae's Enterprises!
www.natashamaes.com | info@natashamaes.com
"""

        for recipient, subject in [
            (args.get('customer_email'), f"Booking Confirmed! {args.get('event_type', 'Event')} at {args.get('venue', '')}"),
            (EMAIL_RECEIVER, f"DATE LOCKED: {args.get('customer_name')} - {args.get('event_type')} at {args.get('venue')}")
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

        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)

        result = f"Confirmation email with PDF receipt sent to {args.get('customer_email')} and management."

    except Exception as e:
        result = f"Email error: {str(e)}"
        print(f"Booking Email Error: {traceback.format_exc()}")

    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# LEGACY SMS ENDPOINT (kept for backward compat)
# =====================================================
@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    data = request.json or {}
    tool_call_id, _, _ = extract_tool_call(data)
    return jsonify({"results": [{"toolCallId": tool_call_id, "result": "SMS disabled. Use email instead."}]}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
