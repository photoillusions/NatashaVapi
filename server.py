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
- 4-hour event booking with 1-hour setup before and 1-hour cleanup after (6-hour total calendar block)
- Security guard required for all events ($35/hr)
- 50% deposit required to lock your date
- Balance due 10 days before event

## ADD-ONS — CUSTOM THEME ROOM DESIGN
**Price: $500 add-on**
Our professional design team transforms your venue with a fully custom themed setup tailored to your event. This includes coordinated decor, table settings, backdrops, and styling to match your vision — whether it's elegant, rustic, tropical, winter wonderland, or any theme you dream up.

### How to offer it:
- After discussing the venue and pricing, mention: "We also offer a Custom Theme Room Design for an additional $500. Our design team will transform the entire space to match your vision — any theme you'd like. Would you be interested in adding that?"
- If they say yes, add $500 to the venue price to get the **total package price**
- The 50% deposit is calculated on the **total package** (venue + add-ons)

### Example:
- The Vault Saturday at $3,795 + Theme Room $500 = **$4,295 total package**
- 50% deposit = **$2,147.50**
- Tell the customer: "With the Custom Theme Room Design, your total package comes to $4,295. The deposit to lock your date would be $2,147.50."

### Include in booking notes:
- When booking with themed setup, add "THEMED SETUP" to the description field
- Example description: "Phone: +18565551234, 50 guests, THEMED SETUP - Tropical theme"

### OPTIONAL — Theme Inspiration Photos:
- If the customer adds the Custom Theme Room Design, mention: "If you have any inspiration photos for your theme, feel free to text two photos to this number. It's totally optional, but it helps our design team bring your vision to life."
- This is optional — do not pressure them. Just a friendly suggestion.

## ADD-ONS — DIVINE DINING CATERING
We offer in-house catering through our Divine Dining service. After discussing the venue and event details, offer catering: "We also have our Divine Dining catering service if you'd like food taken care of. Would you like to hear about our menu packages?"

### Catering Packages (per person pricing):

**Simple & Elegant — $19.99/person**
- Choice of 1 meat, 1 vegetable, 1 side
- Note: Chicken Marsala, Salmon, and Stuffed Breast of Chicken are excluded from this tier
- Includes professional service

**Simply Classy — $26.99/person** ⭐ Most Popular
- Choice of 2 meats, 1 vegetable, 1 side
- Can choose one premium meat (Chicken Marsala or Stuffed Breast of Chicken)
- Add Salmon: +$15.00/person
- Elevated service with customized plating

**Simply Divine — $34.99/person**
- Choice of 3 meats, 2 vegetables, 2 sides
- All premium selections available
- Add Salmon: +$15.00/person
- White-glove service

**Wedding Package — $49.99/person** (Mae's Liberty Palace only)
- Includes venue AND Simply Classy menu combined
- Children under 12: $17.00/child (Chicken Fingers & Fries)

### Available Menu Items:
**Proteins:** Italian Herb Chicken, Honey Baked Ham, Succulent Roast Beef (w/gravy), Oven Roasted Turkey (w/gravy), Chicken Marsala, Grilled Salmon (+$15), Stuffed Breast of Chicken
**Sides:** Garlic & Rosemary Roasted Potatoes, Rice Pilaf, Long Grain Wild Rice, Baked Ziti, Pasta Salad, Baked Macaroni and Cheese
**Vegetables:** Green Beans, Collards, Broccoli, Mixed Vegetables, Steamed Broccoli, Brussel Sprouts, Grilled Asparagus

### Custom Requests:
If the customer wants something not on the menu, say: "Our chefs can customize the menu to fit your taste. Just let us know what you have in mind and we'll make it happen."

### How to calculate catering totals:
- Catering cost = per-person price × guest count
- Add to venue price + any other add-ons (Theme Room $500) for TOTAL PACKAGE
- 50% deposit is on the TOTAL PACKAGE (venue + catering + add-ons)

### Example:
- The Vault Saturday $3,795 + Simply Classy 75 guests ($26.99 × 75 = $2,024.25) + Theme Room $500 = **$6,319.25 total package**
- 50% deposit = **$3,159.63**

### Include in booking notes:
- Add catering package name to the description: "CATERING: Simply Classy, 75 guests"
- If salmon add-on: "CATERING: Simply Classy + Salmon, 75 guests"

## CONTRACTS — AUTO-GENERATED FOR EVERY BOOKING
**A contract is automatically generated every time you book an appointment.** You don't need to do anything extra — the system handles it. Here's what happens:

1. **When you call `book_appointment`:** Include ALL the contract fields (customer_name, event_type, venue, total_price, deposit_amount, guest_count, event_time, themed_setup, early_bird, etc.)
2. **The system automatically:**
   - Generates a professional PDF contract with all event details, pricing, payment history, and terms & conditions
   - Emails the contract to the customer AND to natashashoe4@gmail.com
   - Stores the contract in Google Drive under "Event Contracts" folder, named: "CustomerName - EventType - Date.pdf"
3. **When a payment is made and you call `update_booking`:** Include the `total_price` so the contract can calculate the remaining balance. The system will:
   - Regenerate the contract showing CONFIRMED status and payment received
   - Re-email the updated contract to customer + management
   - Replace the old contract in Google Drive with the updated version

**IMPORTANT:** Make sure to collect all booking details BEFORE calling book_appointment so the contract is complete:
- Customer name, email, phone
- Event type, venue, date, time
- Guest count
- Total price (including add-ons like Custom Theme Room Design)
- Deposit amount (50% of total)
- Whether Early Bird or Themed Setup applies

Tell the customer: "You'll receive your event contract by email shortly with all the details and terms."

## EMAIL COLLECTION — CRITICAL RULES
**ALWAYS collect email after penciling in a date OR when a customer wants package info.**
You MUST actually call `send_info_email` — NEVER skip it or make excuses.

**The caller's phone number is captured automatically from Caller ID on every tool call — do NOT ask for it.**

## CUSTOMER LOOKUP — lookup_customer
**IMPORTANT: After getting the customer's name, call `lookup_customer` FIRST.**
- The server automatically extracts the caller's phone number from caller ID
- It searches the CRM and returns any previous history (name, email, venue, payments, status)
- If RETURNING CUSTOMER: Greet them warmly, reference their history, don't make them repeat info
- If NEW CUSTOMER: Proceed normally with the booking flow

### How to collect email (ACCURACY IS CRITICAL):
1. Ask for their **name**
2. Call `lookup_customer(customer_name)` — if they have an email on file, confirm it: "I have [email] on file — is that still correct?"
3. If no email on file, ask: "What's your email address? Please spell it out for me letter by letter so I get it exactly right."
4. Repeat the full email back to them: "So that's J-O-H-N at G-M-A-I-L dot com, is that correct?"
5. If they just say it fast, ask: "I want to make sure I have that perfect — could you spell that out for me?"
6. **Do NOT ask for their phone number — it's captured automatically from caller ID.**
7. **IMMEDIATELY call `send_info_email`** — do NOT skip this step, do NOT say "I'll have someone email you", do NOT make excuses. YOU send it right now.

### When to send email:
- Customer asks about packages or pricing details → collect name + spelled email → `send_info_email`
- After penciling in a date → collect name + spelled email → `send_info_email`
- Customer asks to be emailed anything → collect name + spelled email → `send_info_email`

## CALENDAR — PENCIL IN vs LOCK

**IMPORTANT DISTINCTION:**
- **Pencil in** = We hold the date temporarily. No payment required. This is NOT a guaranteed reservation.
- **Lock the date** = Customer pays 50% deposit. Date is officially secured and guaranteed.

### Flow when customer wants a date:
1. Call `check_availability(start_time, end_time, is_event)` to see if the date is free
2. If available and customer wants to proceed:
   - Ask: "Would you like to go ahead and secure this date with a deposit, or would you like me to pencil you in while you finalize your plans?"
   - **If they want to pencil in:** Get their name, collect their email (SPELL IT OUT — you already have their phone from caller ID), call `book_appointment` with summary starting with "PENCILED - ". Then IMMEDIATELY call `send_info_email` to send them package details. Tell them: "I've penciled you in for [date] and I'm sending you an email right now with all the details. Just keep in mind, the date isn't officially locked until we receive the 50% deposit."
   - **If they want to lock/secure it:** Collect payment via `process_payment`. Then:
     - If they had a PENCILED booking: call `update_booking` to change it to CONFIRMED (updates calendar + CRM automatically)
     - If this is a brand new booking (no pencil): call `book_appointment` with "CONFIRMED - " prefix
     - Either way, call `send_booking_email` to send confirmation

### Time Formatting:
- ALL times: ISO 8601 with Eastern timezone
- March-November (EDT): -04:00
- November-March (EST): -05:00
- Assume year 2026 unless stated otherwise

### Event Durations (calculate end_time from event start):
- **VIP Tours:** 1 hour. is_event=false. No setup/cleanup buffer.
- **All Events (Weddings, Sweet 16s, Repasts, Birthday Parties, Corporate):** 4-hour event booking. is_event=true.
  - The server AUTOMATICALLY adds 1-hour setup BEFORE and 1-hour cleanup AFTER.
  - So a 4-hour event = 6-hour total calendar block. You do NOT need to add the buffers yourself.
  - Tell the customer: "Your event is 4 hours, and that includes setup before and cleanup after at no extra cost."
  - Calculate end_time as start_time + 4 hours ONLY. The server handles the rest.

### Examples:
Pencil in a wedding June 15 at 6 PM (4hr event = 6PM to 10PM):
→ check_availability(start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-15T22:00:00-04:00", is_event: true)
→ Server checks 5PM-11PM (adds 1hr buffer each side)
→ book_appointment(summary: "PENCILED - Wedding - The Vault - Sarah Johnson", start_time: "2026-06-15T18:00:00-04:00", end_time: "2026-06-15T22:00:00-04:00", is_event: true)
→ Server books 5PM-11PM on calendar (6hr block)

Book a tour Wednesday at 2 PM (1hr, no buffer):
→ check_availability(start_time: "2026-03-04T14:00:00-05:00", end_time: "2026-03-04T15:00:00-05:00", is_event: false)
→ book_appointment(summary: "TOUR - The Vault - Sarah Johnson", start_time: "2026-03-04T14:00:00-05:00", end_time: "2026-03-04T15:00:00-05:00", is_event: false, description: "Phone: +18565551234, interested in wedding venue")

Lock a wedding after payment:
→ process_payment(amount: "1897.50", ...)
→ update_booking(customer_name: "Sarah Johnson", payment_amount: "1897.50", confirmation_number: "NME-ABC12345", customer_phone: "+18565551234", customer_email: "sarah@email.com")
→ Calendar: PENCILED → CONFIRMED automatically, payment details added to event description
→ send_booking_email(...)

## TOURS — VIP VENUE TOURS
Tours are 1-hour visits for customers to see the venue in person. No deposit required.

### Tour Booking Flow:
1. Ask which venue they'd like to tour
2. Ask what date and time works for them
3. Call `check_availability(start_time, end_time, is_event: false)` — tours are 1 hour, NO buffer
4. If available, get their name (you already have phone from caller ID)
5. Call `book_appointment` with summary: "TOUR - [Venue] - [Customer Name]"
   - Include their phone number and any notes in the description field
   - is_event: false (no setup/cleanup buffer)
6. Confirm: "You're all set for a tour of [venue] on [date] at [time]. We look forward to seeing you!"
7. Collect their email (SPELL IT OUT) and call `send_info_email` so they have venue info before the tour

### Tour Notes:
- Tours are FREE — no payment needed
- Use "TOUR - " prefix (not PENCILED or CONFIRMED)
- Tours do NOT get 1-hour setup/cleanup buffers
- Include phone number in the description field for follow-up

## RESCHEDULING
When a customer calls to reschedule an existing booking (tour OR event):

### Reschedule Flow:
1. Confirm their name (you may already have it from CRM)
2. Ask what new date/time they'd like
3. Call `check_availability` for the new slot
4. If available, call `reschedule_booking(customer_name, new_start_time, new_end_time, is_event, customer_phone)`
   - The server automatically moves the calendar event and adds a reschedule note
   - For events (is_event: true), the server adds the 1-hour buffers automatically
   - For tours (is_event: false), no buffers
5. Confirm: "All done! I've moved your [tour/event] to [new date] at [new time]."
6. If the new slot is NOT available, offer alternatives: "That time isn't available. Would [alternative] work?"

### Reschedule Examples:
Reschedule a tour to Friday at 3 PM:
→ check_availability(start_time: "2026-03-07T15:00:00-05:00", end_time: "2026-03-07T16:00:00-05:00", is_event: false)
→ reschedule_booking(customer_name: "Sarah Johnson", new_start_time: "2026-03-07T15:00:00-05:00", new_end_time: "2026-03-07T16:00:00-05:00", is_event: false, customer_phone: "+18565551234")

Reschedule a wedding to July 20 at 5 PM:
→ check_availability(start_time: "2026-07-20T17:00:00-04:00", end_time: "2026-07-20T21:00:00-04:00", is_event: true)
→ reschedule_booking(customer_name: "Sarah Johnson", new_start_time: "2026-07-20T17:00:00-04:00", new_end_time: "2026-07-20T21:00:00-04:00", is_event: true, customer_phone: "+18565551234")

## PAYMENT — process_payment
Only when customer wants to LOCK their date with a deposit:
1. Confirm the deposit amount (50% of venue rental)
2. Collect card info ONE field at a time:
   - "May I have the card number?"
   - "Expiration date?"
   - "The three-digit security code on the back?"
   - "And the billing zip code?"
3. Call `process_payment`
4. If successful, call `update_booking` with customer_name, payment_amount, confirmation_number, customer_phone, and customer_email — this automatically updates the calendar from PENCILED to CONFIRMED and updates the CRM
5. Call `send_booking_email` to send confirmation

## RETURNING CALLERS / MAKING A PAYMENT
**The customer's phone number is their account identifier.** Every caller's phone number is captured from Caller ID automatically.

If CRM data is present in your system prompt (injected at call start), you will see the customer's:
- Name, email, venue, event type, event date
- Past payment info, confirmation numbers
- Previous call notes

### When a returning customer calls to make a payment:
1. Greet them by name if you have it from CRM: "Welcome back, [Name]!"
2. Confirm what they're calling about: "Are you calling to secure your [event type] at [venue] on [date]?"
3. Confirm the deposit amount (50% of venue rental)
4. Collect card info ONE field at a time (same as above)
5. Call `process_payment`
6. If successful, call `update_booking` — this changes PENCILED → CONFIRMED on the calendar and updates the CRM with payment details
7. Call `send_booking_email` to send confirmation
8. Do NOT ask for their phone number — you already have it from caller ID

### When a returning customer calls for info:
- Use CRM data to personalize: "I see you were interested in [venue] for a [event type]. How can I help?"
- Don't make them repeat information you already have

### CRM Tracking:
- Every interaction updates the CRM via phone number
- Payment amounts, dates, and confirmation numbers are tracked
- The calendar event description gets payment history appended

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
# CONTRACT SYSTEM — Generate, Email, Store in Google Drive
# =====================================================
CONTRACTS_FOLDER_NAME = "Event Contracts"
CONTRACT_RECIPIENT = "natashashoe4@gmail.com"

def get_gdrive_service():
    """Get authenticated Google Drive service using service account."""
    from google.oauth2 import service_account as sa_module
    from googleapiclient.discovery import build
    sa_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
    creds = sa_module.Credentials.from_service_account_info(
        sa_info, scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
    )
    return build('drive', 'v3', credentials=creds)

def find_or_create_folder(drive_service, folder_name, parent_id=None):
    """Find existing folder or create it. Returns folder ID."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    # Create folder
    metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        metadata['parents'] = [parent_id]
    folder = drive_service.files().create(body=metadata, fields='id').execute()
    print(f"DRIVE: Created folder '{folder_name}' -> {folder.get('id')}")
    return folder.get('id')

def upload_or_replace_contract(drive_service, folder_id, filename, filepath):
    """Upload PDF to Drive folder; replace if same filename exists."""
    from googleapiclient.http import MediaFileUpload

    # Check if file already exists in folder
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    existing = results.get('files', [])

    media = MediaFileUpload(filepath, mimetype='application/pdf', resumable=True)

    if existing:
        # Update existing file
        file_id = existing[0]['id']
        updated = drive_service.files().update(
            fileId=file_id, media_body=media, fields='id, webViewLink'
        ).execute()
        print(f"DRIVE: Updated contract '{filename}' -> {updated.get('id')}")
        return updated
    else:
        # Create new file
        metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        created = drive_service.files().create(
            body=metadata, media_body=media, fields='id, webViewLink'
        ).execute()
        print(f"DRIVE: Uploaded contract '{filename}' -> {created.get('id')}")
        return created

def generate_contract_pdf(contract_data, filepath):
    """Generate a professional event contract PDF."""
    if not HAS_REPORTLAB:
        return False

    doc = SimpleDocTemplate(filepath, pagesize=LETTER,
                            topMargin=40, bottomMargin=40,
                            leftMargin=50, rightMargin=50)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("NATASHA MAE'S ENTERPRISES", styles['Title']))
    elements.append(Paragraph("Event Venue Contract", styles['Heading2']))
    elements.append(Spacer(1, 6))

    status = contract_data.get('status', 'PENCILED')
    status_color = 'green' if status == 'CONFIRMED' else 'orange'
    elements.append(Paragraph(
        f'<font color="{status_color}"><b>Status: {status}</b></font>',
        styles['Heading3']
    ))
    elements.append(Paragraph(
        f"Contract Date: {datetime.now().strftime('%B %d, %Y')}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 16))

    # Client Info
    elements.append(Paragraph("CLIENT INFORMATION", styles['Heading3']))
    client_table = [
        ["Client Name", contract_data.get('customer_name', 'N/A')],
        ["Email", contract_data.get('customer_email', 'N/A')],
        ["Phone", contract_data.get('customer_phone', 'N/A')],
    ]
    t = Table(client_table, colWidths=[140, 340])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.15, 0.15, 0.3)),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Event Details
    elements.append(Paragraph("EVENT DETAILS", styles['Heading3']))
    venue = contract_data.get('venue', 'N/A')
    venue_lower = venue.lower() if venue else ''
    venue_address = VENUE_ADDRESSES.get(venue_lower, '')
    for vk, va in VENUE_ADDRESSES.items():
        if vk in venue_lower:
            venue_address = va
            break

    event_table = [
        ["Event Type", contract_data.get('event_type', 'N/A')],
        ["Venue", venue],
        ["Venue Address", venue_address or 'See website'],
        ["Event Date", contract_data.get('event_date', 'N/A')],
        ["Event Time", contract_data.get('event_time', 'N/A')],
        ["Duration", "4 hours (plus 1hr setup + 1hr cleanup)"],
        ["Estimated Guests", str(contract_data.get('guest_count', 'N/A'))],
    ]
    if contract_data.get('themed_setup'):
        event_table.append(["Custom Theme Design", "YES — $500 Add-On"])
        if contract_data.get('theme_description'):
            event_table.append(["Theme", contract_data.get('theme_description')])

    # Catering details
    catering_pkg = contract_data.get('catering_package', '')
    if catering_pkg and catering_pkg.lower() != 'none':
        event_table.append(["Divine Dining Catering", catering_pkg])
        catering_pp = contract_data.get('catering_price_pp', '')
        if catering_pp:
            event_table.append(["Catering Price/Person", f"${catering_pp}"])
        if contract_data.get('catering_salmon'):
            event_table.append(["Salmon Add-On", "+$15.00/person"])
        children = contract_data.get('children_count', '')
        if children and str(children) != '0':
            event_table.append(["Children Under 12", f"{children} × $17.00/child"])

    t = Table(event_table, colWidths=[140, 340])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.15, 0.15, 0.3)),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Financial Summary
    elements.append(Paragraph("FINANCIAL SUMMARY", styles['Heading3']))
    total = contract_data.get('total_price', '0')
    deposit = contract_data.get('deposit_amount', '0')
    paid = contract_data.get('total_paid', '0')
    balance = contract_data.get('balance_due', '0')
    early_bird = contract_data.get('early_bird', False)

    finance_table = [
        ["Venue Rental", f"${contract_data.get('venue_price', total)}"],
    ]
    if contract_data.get('themed_setup'):
        finance_table.append(["Custom Theme Room Design", "$500.00"])
    # Catering line items
    if catering_pkg and catering_pkg.lower() != 'none':
        catering_total = contract_data.get('catering_total', '')
        guest_count = contract_data.get('guest_count', '')
        catering_label = f"Divine Dining: {catering_pkg}"
        if guest_count:
            catering_label += f" ({guest_count} guests)"
        finance_table.append([catering_label, f"${catering_total}" if catering_total else "See total"])
        if contract_data.get('catering_salmon'):
            finance_table.append(["  Salmon Add-On (+$15/pp)", "Included above"])
        children = contract_data.get('children_count', '')
        if children and str(children) != '0':
            try:
                kids_total = f"${float(children) * 17:.2f}"
            except:
                kids_total = f"{children} × $17"
            finance_table.append([f"  Children's Menu ({children} kids)", kids_total])
    if early_bird:
        finance_table.append(["Early Bird Discount (50% OFF)", "Applied"])
    finance_table.extend([
        ["", ""],
        ["TOTAL PACKAGE", f"${total}"],
        ["Required Deposit (50%)", f"${deposit}"],
        ["Total Paid", f"${paid}"],
        ["BALANCE DUE", f"${balance}"],
    ])
    t = Table(finance_table, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 1.0)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, -4), (-1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("<i>Balance due 10 days before event date.</i>", styles['Normal']))
    elements.append(Spacer(1, 16))

    # Payment History
    payments = contract_data.get('payments', [])
    if payments:
        elements.append(Paragraph("PAYMENT HISTORY", styles['Heading3']))
        pay_rows = [["Date", "Amount", "Confirmation #"]]
        for p in payments:
            pay_rows.append([p.get('date', ''), f"${p.get('amount', '0')}", p.get('confirmation', '')])
        t = Table(pay_rows, colWidths=[160, 160, 160])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.15, 0.15, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

    # Confirmation
    if contract_data.get('confirmation_number'):
        elements.append(Paragraph(
            f"<b>Confirmation Number: {contract_data['confirmation_number']}</b>",
            styles['Heading3']
        ))
        elements.append(Spacer(1, 12))

    # Terms & Conditions
    elements.append(Paragraph("TERMS & CONDITIONS", styles['Heading3']))
    terms = [
        "1. A non-refundable deposit of 50% of the total package is required to secure your date.",
        "2. The remaining balance is due no later than 10 days before the event date.",
        "3. A licensed security guard is mandatory for all events at $35 per hour.",
        "4. Your booking includes a 4-hour event window with 1-hour setup before and 1-hour cleanup after (6-hour total venue access).",
        "5. Cancellations must be submitted in writing at least 30 days prior to the event for a date transfer credit.",
        "6. Cancellations made less than 30 days before the event will forfeit the deposit.",
        "7. Natasha Mae's Enterprises reserves the right to terminate an event if it violates venue policies or presents a safety concern.",
        "8. The client is responsible for any damages to the venue or property during the event.",
        "9. Custom Theme Room Design add-ons are non-refundable once the design process has begun.",
        "10. By making a deposit, the client agrees to all terms outlined in this contract.",
    ]
    for term in terms:
        elements.append(Paragraph(term, styles['Normal']))
        elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 24))
    elements.append(Paragraph("__________________________________", styles['Normal']))
    elements.append(Paragraph("Client Signature / Date", styles['Normal']))
    elements.append(Spacer(1, 16))
    elements.append(Paragraph("__________________________________", styles['Normal']))
    elements.append(Paragraph("Natasha Mae's Enterprises / Date", styles['Normal']))

    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "<b>Natasha Mae's Enterprises</b> | www.natashamaes.com | info@natashamaes.com",
        styles['Normal']
    ))

    doc.build(elements)
    return True

def send_contract_emails(contract_data, pdf_path, is_update=False):
    """Send contract PDF to customer AND natashashoe4@gmail.com."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("CONTRACT EMAIL: Email not configured")
        return False

    customer_email = contract_data.get('customer_email')
    customer_name = contract_data.get('customer_name', 'Customer')
    event_type = contract_data.get('event_type', 'Event')
    venue = contract_data.get('venue', '')
    status = contract_data.get('status', 'PENCILED')

    if is_update:
        subject_customer = f"Updated Contract — {event_type} at {venue} | Natasha Mae's"
        subject_mgmt = f"CONTRACT UPDATED: {customer_name} — {event_type} at {venue}"
        body = f"""Dear {customer_name},

Please find your UPDATED event contract attached. Your payment has been received and your contract has been updated to reflect the new balance.

Status: {status}

If you have any questions, please don't hesitate to reach out.

Thank you for choosing Natasha Mae's Enterprises!
www.natashamaes.com | info@natashamaes.com
"""
    else:
        subject_customer = f"Your Event Contract — {event_type} at {venue} | Natasha Mae's"
        subject_mgmt = f"NEW CONTRACT: {customer_name} — {event_type} at {venue}"
        body = f"""Dear {customer_name},

Thank you for your interest in Natasha Mae's Enterprises! Please find your event contract attached.

Status: {status}

{"Your date is penciled in. To officially lock your date, a 50% deposit is required." if status == "PENCILED" else "Your date is CONFIRMED! Thank you for your deposit."}

If you have any questions, please don't hesitate to reach out.

Thank you for choosing Natasha Mae's Enterprises!
www.natashamaes.com | info@natashamaes.com
"""

    recipients = []
    if customer_email:
        recipients.append((customer_email, subject_customer))
    recipients.append((CONTRACT_RECIPIENT, subject_mgmt))

    for recipient, subject in recipients:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"Natasha Mae's <{EMAIL_SENDER}>"
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_attach = MIMEApplication(f.read(), _subtype='pdf')
                    safe_name = f"{customer_name.replace(' ', '_')}_{event_type}_Contract.pdf"
                    pdf_attach.add_header('Content-Disposition', 'attachment', filename=safe_name)
                    msg.attach(pdf_attach)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"CONTRACT EMAIL sent to {recipient}")
        except Exception as e:
            print(f"CONTRACT EMAIL ERROR ({recipient}): {e}")

    return True

def store_contract_gdrive(contract_data, pdf_path):
    """Upload contract PDF to Google Drive under Event Contracts folder."""
    try:
        drive_service = get_gdrive_service()

        # Find or create "Event Contracts" root folder
        root_folder_id = find_or_create_folder(drive_service, CONTRACTS_FOLDER_NAME)

        # Build filename: "CustomerName - EventType - Date.pdf"
        customer_name = contract_data.get('customer_name', 'Unknown')
        event_type = contract_data.get('event_type', 'Event')
        event_date = contract_data.get('event_date', datetime.now().strftime('%Y-%m-%d'))
        filename = f"{customer_name} - {event_type} - {event_date}.pdf"

        file_result = upload_or_replace_contract(drive_service, root_folder_id, filename, pdf_path)
        print(f"DRIVE: Contract stored as '{filename}'")
        return file_result
    except Exception as e:
        print(f"DRIVE CONTRACT ERROR: {traceback.format_exc()}")
        return None

def handle_contract(contract_data, is_update=False):
    """Master function: generate contract PDF, email it, store in Drive."""
    pdf_path = None
    try:
        pdf_path = tempfile.mktemp(suffix='.pdf')
        success = generate_contract_pdf(contract_data, pdf_path)
        if not success:
            print("CONTRACT: PDF generation failed (reportlab missing?)")
            return "Contract generation failed."

        # Email to customer + natashashoe4@gmail.com
        send_contract_emails(contract_data, pdf_path, is_update=is_update)

        # Store in Google Drive
        drive_result = store_contract_gdrive(contract_data, pdf_path)
        drive_status = "stored in Drive" if drive_result else "Drive upload failed"

        action = "updated" if is_update else "created"
        print(f"CONTRACT: {action} for {contract_data.get('customer_name')} | {drive_status}")
        return f"Contract {action}, emailed, and {drive_status}."

    except Exception as e:
        print(f"CONTRACT ERROR: {traceback.format_exc()}")
        return f"Contract error: {str(e)}"
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except:
                pass

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
                                "name": "lookup_customer",
                                "description": "Look up a customer in the CRM using the caller's phone number (extracted automatically from caller ID). Call this FIRST after getting the customer's name to check if they are a returning customer.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_name": {"type": "string", "description": "The customer's name (for logging)"}
                                    },
                                    "required": ["customer_name"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/lookup-customer-tool"}
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
                                "description": "Books or pencils in a date on the calendar AND auto-generates a contract PDF (emailed to customer + management, stored in Google Drive).",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "summary": {"type": "string", "description": "Event title: 'PENCILED - EventType - Venue - Name' or 'CONFIRMED - EventType - Venue - Name'"},
                                        "start_time": {"type": "string", "description": "ISO 8601 start datetime with timezone"},
                                        "end_time": {"type": "string", "description": "ISO 8601 end datetime with timezone"},
                                        "is_event": {"type": "boolean", "description": "true for events, false for tours"},
                                        "attendee_email": {"type": "string", "description": "Customer email address"},
                                        "description": {"type": "string", "description": "Booking notes, phone number, guest count, THEMED SETUP if applicable"},
                                        "customer_name": {"type": "string", "description": "Customer full name"},
                                        "customer_phone": {"type": "string", "description": "Customer phone number"},
                                        "event_type": {"type": "string", "description": "Birthday, Wedding, Sweet 16, Corporate, etc."},
                                        "venue": {"type": "string", "description": "The Vault, Liberty Palace, or Frankford Ave"},
                                        "event_time": {"type": "string", "description": "Event time e.g. 6:00 PM - 10:00 PM"},
                                        "guest_count": {"type": "string", "description": "Estimated number of guests"},
                                        "total_price": {"type": "string", "description": "Total package price including add-ons"},
                                        "venue_price": {"type": "string", "description": "Base venue rental price before add-ons"},
                                        "deposit_amount": {"type": "string", "description": "50% deposit amount"},
                                        "themed_setup": {"type": "boolean", "description": "true if Custom Theme Room Design $500 add-on"},
                                        "theme_description": {"type": "string", "description": "Customer's theme if themed_setup is true"},
                                        "early_bird": {"type": "boolean", "description": "true if Early Bird 50% off applied"},
                                        "confirmation_number": {"type": "string", "description": "Payment confirmation if already paid"},
                                        "catering_package": {"type": "string", "description": "Divine Dining package: 'Simple & Elegant', 'Simply Classy', 'Simply Divine', 'Wedding Package', or 'None'"},
                                        "catering_price_pp": {"type": "string", "description": "Per-person catering price e.g. '26.99'"},
                                        "catering_total": {"type": "string", "description": "Total catering cost (price_pp × guest_count)"},
                                        "catering_salmon": {"type": "boolean", "description": "true if salmon add-on (+$15/person)"},
                                        "children_count": {"type": "string", "description": "Number of children under 12 for kids menu ($17/child)"}
                                    },
                                    "required": ["summary", "start_time", "end_time", "is_event", "customer_name", "event_type", "venue", "total_price", "deposit_amount"]
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
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "update_booking",
                                "description": "Update an existing PENCILED calendar event to CONFIRMED after payment. Updates calendar, CRM, AND regenerates contract with payment details (emailed + stored in Drive).",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_name": {"type": "string", "description": "Customer full name to search for in calendar"},
                                        "payment_amount": {"type": "string", "description": "Amount paid, e.g. '1897.50'"},
                                        "confirmation_number": {"type": "string", "description": "Payment confirmation number from process_payment"},
                                        "customer_phone": {"type": "string", "description": "Customer phone (from caller ID)"},
                                        "customer_email": {"type": "string", "description": "Customer email address"},
                                        "total_price": {"type": "string", "description": "Total package price so contract can show balance"},
                                        "venue": {"type": "string", "description": "Venue name for contract"},
                                        "event_time": {"type": "string", "description": "Event time for contract"},
                                        "guest_count": {"type": "string", "description": "Guest count for contract"}
                                    },
                                    "required": ["customer_name", "payment_amount", "confirmation_number", "total_price"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "reschedule_booking",
                                "description": "Reschedule an existing booking (tour or event) to a new date/time. Searches by customer name, checks new slot availability, moves the calendar event, and updates CRM.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_name": {"type": "string", "description": "Customer full name to search for in calendar"},
                                        "new_start_time": {"type": "string", "description": "New ISO 8601 start datetime with timezone"},
                                        "new_end_time": {"type": "string", "description": "New ISO 8601 end datetime with timezone"},
                                        "is_event": {"type": "boolean", "description": "true for events (adds 1hr buffer), false for tours"},
                                        "customer_phone": {"type": "string", "description": "Customer phone (from caller ID)"}
                                    },
                                    "required": ["customer_name", "new_start_time", "new_end_time", "is_event"]
                                }
                            },
                            "server": {"url": "https://natashavapi.onrender.com/calendar-tool"}
                        }
                    ]
                },
                "serverMessages": ["end-of-call-report"],
                "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "en-US"},
                "voice": {"provider": "11labs", "voiceId": "EXAVITQu4vr4xnSDxMaL"}
            }
        }

        # CRM History Injection + Caller ID Phone Number
        try:
            phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
            if not phone:
                phone = data.get('message', {}).get('customer', {}).get('number')
            if phone:
                # Always inject the caller's phone number so Jessica knows it
                phone_inject = f"\n\n## CALLER INFO (from Caller ID)\n- Phone: {phone}\n- You already have this number. Do NOT ask for it."
                response["assistant"]["model"]["messages"][0]["content"] += phone_inject
                print(f"CALLER ID: {phone}")

                # CRM lookup for returning customers
                customer_data = crm_service.get_customer(phone)
                if customer_data:
                    history_text = crm_service.format_history_for_prompt(customer_data)
                    response["assistant"]["model"]["messages"][0]["content"] += history_text
                    print(f"CRM: Returning customer found for {phone}")
                else:
                    print(f"CRM: New customer {phone}")
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
            summary = args.get('summary', '')
            
            # Apply buffer for events
            if is_event:
                try:
                    s = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                    e = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
                    start_iso = (s - timedelta(hours=1)).isoformat()
                    end_iso = (e + timedelta(hours=1)).isoformat()
                except: pass

            # Extract venue from summary and look up address
            location = ''
            summary_lower = summary.lower()
            for venue_key, address in VENUE_ADDRESSES.items():
                if venue_key in summary_lower:
                    location = address
                    break

            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                sa_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
                creds = service_account.Credentials.from_service_account_info(
                    sa_info, scopes=['https://www.googleapis.com/auth/calendar']
                )
                service = build('calendar', 'v3', credentials=creds)
                calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

                event_body = {
                    'summary': summary,
                    'location': location,
                    'description': args.get('description', ''),
                    'start': {'dateTime': start_iso, 'timeZone': 'America/New_York'},
                    'end': {'dateTime': end_iso, 'timeZone': 'America/New_York'},
                }
                # Append email to description (can't add as attendee with service account)
                attendee_email = args.get('attendee_email')
                if attendee_email:
                    event_body['description'] = (event_body.get('description', '') + f"\nEmail: {attendee_email}").strip()

                created = service.events().insert(
                    calendarId=calendar_id,
                    body=event_body,
                    sendUpdates='none'
                ).execute()

                result = f"Booked: {summary} on {start_iso}. Event ID: {created.get('id', 'N/A')}"
                print(f"BOOKED: {summary} | Location: {location} | ID: {created.get('id')}")

                # --- AUTO-GENERATE CONTRACT ---
                try:
                    desc = args.get('description', '')
                    contract_data = {
                        'customer_name': args.get('customer_name', summary.split(' - ')[-1] if ' - ' in summary else 'Customer'),
                        'customer_email': args.get('attendee_email', ''),
                        'customer_phone': args.get('customer_phone', ''),
                        'event_type': args.get('event_type', summary.split(' - ')[1] if summary.count(' - ') >= 2 else 'Event'),
                        'venue': args.get('venue', ''),
                        'event_date': args.get('start_time', start_iso)[:10],
                        'event_time': args.get('event_time', ''),
                        'guest_count': args.get('guest_count', ''),
                        'total_price': args.get('total_price', '0'),
                        'venue_price': args.get('venue_price', args.get('total_price', '0')),
                        'deposit_amount': args.get('deposit_amount', '0'),
                        'total_paid': '0',
                        'balance_due': args.get('total_price', '0'),
                        'themed_setup': 'THEMED' in desc.upper() or args.get('themed_setup', False),
                        'theme_description': args.get('theme_description', ''),
                        'early_bird': args.get('early_bird', False),
                        'status': 'CONFIRMED' if 'CONFIRMED' in summary.upper() else 'PENCILED',
                        'confirmation_number': args.get('confirmation_number', ''),
                        'payments': [],
                        'catering_package': args.get('catering_package', ''),
                        'catering_price_pp': args.get('catering_price_pp', ''),
                        'catering_total': args.get('catering_total', ''),
                        'catering_salmon': args.get('catering_salmon', False),
                        'children_count': args.get('children_count', ''),
                    }
                    # Extract phone from caller ID if not provided
                    if not contract_data['customer_phone']:
                        try:
                            contract_data['customer_phone'] = data.get('message', {}).get('call', {}).get('customer', {}).get('number', '')
                        except: pass

                    contract_result = handle_contract(contract_data, is_update=False)
                    result += f" | Contract: {contract_result}"
                except Exception as ce:
                    print(f"CONTRACT AUTO-GEN ERROR: {traceback.format_exc()}")
                    result += " | Contract generation failed (booking still saved)."

            except Exception as e:
                result = f"Booking error: {str(e)}"
                print(f"Book Appointment Error: {traceback.format_exc()}")
        elif function_name == 'update_booking':
            # Search for PENCILED event and update to CONFIRMED with payment details
            customer_name = args.get('customer_name', '')
            payment_amount = args.get('payment_amount', '')
            confirmation_number = args.get('confirmation_number', '')
            customer_phone = args.get('customer_phone', '')
            customer_email = args.get('customer_email', '')

            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                sa_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
                creds = service_account.Credentials.from_service_account_info(
                    sa_info, scopes=['https://www.googleapis.com/auth/calendar']
                )
                service = build('calendar', 'v3', credentials=creds)
                calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

                # Search upcoming events for PENCILED with this customer's name
                now = datetime.utcnow().isoformat() + 'Z'
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime',
                    q=f"PENCILED {customer_name}"
                ).execute()
                events = events_result.get('items', [])

                if not events:
                    result = f"No penciled booking found for {customer_name}. Please create a new confirmed booking instead."
                else:
                    event = events[0]  # Most relevant match
                    old_summary = event.get('summary', '')
                    new_summary = old_summary.replace('PENCILED', 'CONFIRMED')

                    # Build updated description with payment history
                    existing_desc = event.get('description', '')
                    payment_note = f"\n--- PAYMENT RECEIVED ---\nAmount: ${payment_amount}\nConfirmation: {confirmation_number}\nDate: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}\nPhone: {customer_phone}\nEmail: {customer_email}\n"
                    new_desc = existing_desc + payment_note

                    event['summary'] = new_summary
                    event['description'] = new_desc

                    # Ensure location is set from venue in summary
                    if not event.get('location'):
                        summary_lower = new_summary.lower()
                        for venue_key, address in VENUE_ADDRESSES.items():
                            if venue_key in summary_lower:
                                event['location'] = address
                                break

                    updated = service.events().update(
                        calendarId=calendar_id,
                        eventId=event['id'],
                        body=event
                    ).execute()

                    result = f"Booking updated: {new_summary}. Calendar event confirmed with payment of ${payment_amount}."
                    print(f"CALENDAR UPDATED: {old_summary} -> {new_summary}")

                    # Update CRM with payment
                    phone = customer_phone or None
                    if not phone:
                        try:
                            phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
                        except: pass
                    if phone:
                        crm_service.upsert_customer(phone, {
                            "name": customer_name,
                            "email": customer_email,
                            "last_payment_amount": payment_amount,
                            "last_payment_date": datetime.now().strftime("%Y-%m-%d"),
                            "confirmation_number": confirmation_number,
                            "status": "CONFIRMED",
                            "notes": f"Payment ${payment_amount} received. Conf: {confirmation_number}. Booking confirmed.",
                        })

                    # --- UPDATE CONTRACT WITH PAYMENT ---
                    try:
                        # Parse event info from calendar event
                        event_start = event.get('start', {}).get('dateTime', '')
                        event_venue = event.get('location', '')
                        # Extract event type from summary (format: "CONFIRMED - EventType - Venue - Name")
                        summary_parts = new_summary.split(' - ')
                        event_type = summary_parts[1] if len(summary_parts) > 2 else 'Event'

                        total_price = args.get('total_price', '0')
                        deposit_amount = args.get('deposit_amount', payment_amount)

                        # Calculate balance
                        try:
                            bal = float(total_price) - float(payment_amount)
                            balance_str = f"{bal:.2f}"
                        except:
                            balance_str = "0"

                        contract_data = {
                            'customer_name': customer_name,
                            'customer_email': customer_email,
                            'customer_phone': customer_phone or phone or '',
                            'event_type': event_type,
                            'venue': event_venue or args.get('venue', ''),
                            'event_date': event_start[:10] if event_start else '',
                            'event_time': args.get('event_time', ''),
                            'guest_count': args.get('guest_count', ''),
                            'total_price': total_price,
                            'venue_price': args.get('venue_price', total_price),
                            'deposit_amount': deposit_amount,
                            'total_paid': payment_amount,
                            'balance_due': balance_str,
                            'themed_setup': 'THEMED' in new_desc.upper(),
                            'early_bird': 'early bird' in new_desc.lower(),
                            'status': 'CONFIRMED',
                            'confirmation_number': confirmation_number,
                            'payments': [{
                                'date': datetime.now().strftime('%m/%d/%Y'),
                                'amount': payment_amount,
                                'confirmation': confirmation_number
                            }],
                            'catering_package': args.get('catering_package', ''),
                            'catering_price_pp': args.get('catering_price_pp', ''),
                            'catering_total': args.get('catering_total', ''),
                            'catering_salmon': args.get('catering_salmon', False),
                            'children_count': args.get('children_count', ''),
                        }
                        contract_result = handle_contract(contract_data, is_update=True)
                        result += f" | Contract: {contract_result}"
                    except Exception as ce:
                        print(f"CONTRACT UPDATE ERROR: {traceback.format_exc()}")
                        result += " | Contract update failed (booking still confirmed)."

            except Exception as e:
                result = f"Error updating booking: {str(e)}"
                print(f"Update Booking Error: {traceback.format_exc()}")

        elif function_name == 'reschedule_booking':
            # Search for existing event by customer name/phone and move to new date
            customer_name = args.get('customer_name', '')
            new_start = args.get('new_start_time', '')
            new_end = args.get('new_end_time', '')
            is_event = args.get('is_event', False)
            customer_phone = args.get('customer_phone', '')

            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                sa_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
                creds = service_account.Credentials.from_service_account_info(
                    sa_info, scopes=['https://www.googleapis.com/auth/calendar']
                )
                service = build('calendar', 'v3', credentials=creds)
                calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

                # Search upcoming events for this customer
                now = datetime.utcnow().isoformat() + 'Z'
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime',
                    q=customer_name
                ).execute()
                events = events_result.get('items', [])

                if not events:
                    result = f"No upcoming booking found for {customer_name}. Would you like to book a new appointment?"
                else:
                    event = events[0]
                    old_start = event.get('start', {}).get('dateTime', 'unknown')
                    old_summary = event.get('summary', '')

                    # Apply buffer for events
                    actual_start = new_start
                    actual_end = new_end
                    if is_event:
                        try:
                            s = datetime.fromisoformat(new_start.replace('Z', '+00:00'))
                            e = datetime.fromisoformat(new_end.replace('Z', '+00:00'))
                            actual_start = (s - timedelta(hours=1)).isoformat()
                            actual_end = (e + timedelta(hours=1)).isoformat()
                        except: pass

                    # First check if new slot is available
                    freebusy = service.freebusy().query(body={
                        "timeMin": actual_start,
                        "timeMax": actual_end,
                        "items": [{"id": calendar_id}]
                    }).execute()
                    busy = freebusy.get('calendars', {}).get(calendar_id, {}).get('busy', [])

                    # Filter out the current event from busy check
                    event_id = event.get('id')
                    if busy:
                        result = f"Sorry, the new date/time is not available. Please choose a different time."
                    else:
                        # Update the event with new times
                        event['start'] = {'dateTime': actual_start, 'timeZone': 'America/New_York'}
                        event['end'] = {'dateTime': actual_end, 'timeZone': 'America/New_York'}

                        # Add reschedule note to description
                        existing_desc = event.get('description', '')
                        reschedule_note = f"\n--- RESCHEDULED ---\nFrom: {old_start}\nTo: {new_start}\nDate: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}\n"
                        event['description'] = existing_desc + reschedule_note

                        # Ensure location is set from venue in summary
                        if not event.get('location'):
                            summary_lower = old_summary.lower()
                            for venue_key, address in VENUE_ADDRESSES.items():
                                if venue_key in summary_lower:
                                    event['location'] = address
                                    break

                        updated = service.events().update(
                            calendarId=calendar_id,
                            eventId=event_id,
                            body=event
                        ).execute()

                        result = f"Booking rescheduled successfully. '{old_summary}' has been moved to the new date and time."
                        print(f"RESCHEDULED: {old_summary} from {old_start} to {new_start}")

                        # Update CRM
                        phone = customer_phone or None
                        if not phone:
                            try:
                                phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
                            except: pass
                        if phone:
                            crm_service.upsert_customer(phone, {
                                "name": customer_name,
                                "notes": f"Rescheduled from {old_start} to {new_start}",
                            })

            except Exception as e:
                result = f"Error rescheduling: {str(e)}"
                print(f"Reschedule Error: {traceback.format_exc()}")

    except Exception as e:
        result = f"Error: {str(e)}"
        print(f"Calendar Error: {e}")

    print(f"Calendar result: {result}")
    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200

# =====================================================
# CUSTOMER LOOKUP TOOL (CRM + Caller ID)
# =====================================================
@app.route('/lookup-customer-tool', methods=['POST'])
def lookup_customer_tool_route():
    data = request.json or {}
    tool_call_id, function_name, args = extract_tool_call(data)
    result = "No customer history found. This appears to be a new customer."

    try:
        # Extract phone from VAPI call data (always present in tool calls)
        phone = None
        try:
            phone = data.get('message', {}).get('call', {}).get('customer', {}).get('number')
        except:
            pass
        if not phone:
            try:
                phone = data.get('message', {}).get('customer', {}).get('number')
            except:
                pass

        if phone:
            print(f"LOOKUP: Phone from caller ID: {phone}")
            customer_data = crm_service.get_customer(phone)
            if customer_data:
                print(f"LOOKUP: Returning customer found for {phone}")
                # Build a summary for Jessica to use
                info_parts = [f"RETURNING CUSTOMER FOUND — Phone: {phone}"]
                if customer_data.get('name'):
                    info_parts.append(f"Name: {customer_data['name']}")
                if customer_data.get('email'):
                    info_parts.append(f"Email: {customer_data['email']}")
                if customer_data.get('venue'):
                    info_parts.append(f"Venue: {customer_data['venue']}")
                if customer_data.get('event_type'):
                    info_parts.append(f"Event Type: {customer_data['event_type']}")
                if customer_data.get('event_date'):
                    info_parts.append(f"Event Date: {customer_data['event_date']}")
                if customer_data.get('last_payment_amount'):
                    info_parts.append(f"Last Payment: ${customer_data['last_payment_amount']}")
                if customer_data.get('last_payment_date'):
                    info_parts.append(f"Payment Date: {customer_data['last_payment_date']}")
                if customer_data.get('confirmation_number'):
                    info_parts.append(f"Confirmation: {customer_data['confirmation_number']}")
                if customer_data.get('status'):
                    info_parts.append(f"Status: {customer_data['status']}")
                if customer_data.get('notes'):
                    info_parts.append(f"Notes: {customer_data['notes']}")
                result = " | ".join(info_parts)
            else:
                print(f"LOOKUP: New customer {phone}")
                result = f"NEW CUSTOMER — Phone: {phone}. No previous history."
        else:
            print("LOOKUP: No phone number available in call data")
            result = "Could not determine caller's phone number."

    except Exception as e:
        print(f"Lookup Error: {traceback.format_exc()}")
        result = f"Lookup error: {str(e)}"

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

# =====================================================
# JESSICA ONLINE — CUSTOMER PORTAL API
# =====================================================

# CORS support for frontend
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '')
    allowed_origins = [
        'https://natashamaesenterprise.netlify.app',
        'http://localhost:3000',
        'http://localhost:5173',
    ]
    if origin in allowed_origins or origin.endswith('.netlify.app'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/api/menu', methods=['GET', 'OPTIONS'])
def get_menu():
    """Return available add-on items for the shopping cart."""
    if request.method == 'OPTIONS':
        return '', 204
    menu = {
        "catering": [
            {
                "id": "catering-simple",
                "name": "Simple & Elegant",
                "description": "Choice of 1 meat, 1 vegetable, 1 side. Professional service included.",
                "note": "Excludes Chicken Marsala, Salmon, Stuffed Breast of Chicken",
                "price_per_person": 19.99,
                "category": "catering",
                "type": "per_person"
            },
            {
                "id": "catering-classy",
                "name": "Simply Classy",
                "description": "Choice of 2 meats, 1 vegetable, 1 side. Elevated service with customized plating.",
                "note": "Most Popular — includes one premium meat option",
                "price_per_person": 26.99,
                "category": "catering",
                "type": "per_person",
                "popular": True
            },
            {
                "id": "catering-divine",
                "name": "Simply Divine",
                "description": "Choice of 3 meats, 2 vegetables, 2 sides. White-glove service.",
                "note": "All premium selections available",
                "price_per_person": 34.99,
                "category": "catering",
                "type": "per_person"
            },
            {
                "id": "catering-wedding",
                "name": "Wedding Package",
                "description": "Includes venue AND Simply Classy menu combined. Mae's Liberty Palace only.",
                "price_per_person": 49.99,
                "category": "catering",
                "type": "per_person"
            },
            {
                "id": "catering-kids",
                "name": "Children's Menu (Under 12)",
                "description": "Chicken Fingers & Fries",
                "price_per_person": 17.00,
                "category": "catering",
                "type": "per_person"
            },
            {
                "id": "catering-salmon",
                "name": "Salmon Add-On",
                "description": "Add Grilled Salmon to Simply Classy or Simply Divine package",
                "price_per_person": 15.00,
                "category": "catering",
                "type": "per_person",
                "is_addon": True
            }
        ],
        "addons": [
            {
                "id": "theme-room",
                "name": "Custom Theme Room Design",
                "description": "Professional design team transforms your venue with fully custom themed setup — decor, table settings, backdrops, and styling.",
                "price": 500.00,
                "category": "addon",
                "type": "flat"
            }
        ],
        "proteins": ["Italian Herb Chicken", "Honey Baked Ham", "Succulent Roast Beef (w/gravy)", "Oven Roasted Turkey (w/gravy)", "Chicken Marsala", "Grilled Salmon (+$15)", "Stuffed Breast of Chicken"],
        "sides": ["Garlic & Rosemary Roasted Potatoes", "Rice Pilaf", "Long Grain Wild Rice", "Baked Ziti", "Pasta Salad", "Baked Macaroni and Cheese"],
        "vegetables": ["Green Beans", "Collards", "Broccoli", "Mixed Vegetables", "Steamed Broccoli", "Brussel Sprouts", "Grilled Asparagus"]
    }
    return jsonify(menu), 200

@app.route('/api/lookup-contract', methods=['POST', 'OPTIONS'])
def lookup_contract():
    """Look up a customer's existing contract by email or phone."""
    if request.method == 'OPTIONS':
        return '', 204

    data = request.json or {}
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()

    if not email and not phone:
        return jsonify({"error": "Please provide email or phone number"}), 400

    print(f"CONTRACT LOOKUP: email={email} phone={phone}")

    try:
        # Search CRM for customer
        customer = None
        if phone:
            # Normalize phone
            if not phone.startswith('+'):
                phone = '+1' + phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
            customer = crm_service.get_customer(phone)

        if not customer and email:
            # Search CRM by email via Supabase
            try:
                if crm_service.supabase:
                    resp = crm_service.supabase.table("customers").select("*").eq("email", email).execute()
                    if resp.data:
                        customer = resp.data[0]
                        phone = customer.get('phone', '')
                        if phone and not phone.startswith('+'):
                            phone = '+' + phone
            except Exception as se:
                print(f"CONTRACT LOOKUP email search error: {se}")

        if not customer:
            return jsonify({"found": False, "message": "No existing booking found. You can still add items to your cart and check out with a card."}), 200

        # Search calendar for their event
        event_info = None
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            sa_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=['https://www.googleapis.com/auth/calendar']
            )
            cal_service = build('calendar', 'v3', credentials=creds)
            calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

            now = datetime.utcnow().isoformat() + 'Z'
            name = customer.get('name', '')
            events_result = cal_service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime',
                q=name
            ).execute()
            events = events_result.get('items', [])

            if events:
                evt = events[0]
                event_info = {
                    "summary": evt.get('summary', ''),
                    "date": evt.get('start', {}).get('dateTime', '')[:10],
                    "time": evt.get('start', {}).get('dateTime', ''),
                    "venue": evt.get('location', ''),
                    "description": evt.get('description', ''),
                    "event_id": evt.get('id', ''),
                    "status": "CONFIRMED" if "CONFIRMED" in evt.get('summary', '') else "PENCILED",
                }
        except Exception as ce:
            print(f"CONTRACT LOOKUP calendar error: {ce}")

        result = {
            "found": True,
            "customer": {
                "name": customer.get('name', ''),
                "email": customer.get('email', ''),
                "phone": phone,
                "status": customer.get('status', ''),
                "confirmation_number": customer.get('confirmation_number', ''),
            },
            "event": event_info,
        }
        print(f"CONTRACT LOOKUP: Found {customer.get('name')} - {event_info.get('summary') if event_info else 'no event'}")
        return jsonify(result), 200

    except Exception as e:
        print(f"CONTRACT LOOKUP ERROR: {traceback.format_exc()}")
        return jsonify({"error": f"Lookup failed: {str(e)}"}), 500

@app.route('/api/add-to-package', methods=['POST', 'OPTIONS'])
def add_to_package():
    """Add shopping cart items to an existing event contract."""
    if request.method == 'OPTIONS':
        return '', 204

    data = request.json or {}
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    cart_items = data.get('cart_items', [])
    cart_total = data.get('cart_total', 0)
    guest_count = data.get('guest_count', 0)

    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400
    if not email and not phone:
        return jsonify({"error": "Please provide email or phone"}), 400

    print(f"ADD TO PACKAGE: {email or phone} | {len(cart_items)} items | ${cart_total}")

    try:
        # Normalize phone
        if phone and not phone.startswith('+'):
            phone = '+1' + phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')

        # Find customer
        customer = None
        if phone:
            customer = crm_service.get_customer(phone)
        if not customer and email:
            try:
                if crm_service.supabase:
                    resp = crm_service.supabase.table("customers").select("*").eq("email", email.lower()).execute()
                    if resp.data:
                        customer = resp.data[0]
                        phone = customer.get('phone', '')
                        if phone and not phone.startswith('+'):
                            phone = '+' + phone
            except Exception as se:
                print(f"ADD TO PACKAGE email search error: {se}")

        if not customer:
            return jsonify({"error": "No existing booking found for this email/phone"}), 404

        # Find calendar event
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        sa_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=[
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        cal_service = build('calendar', 'v3', credentials=creds)
        calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

        now = datetime.utcnow().isoformat() + 'Z'
        name = customer.get('name', '')
        events_result = cal_service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
            q=name
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return jsonify({"error": f"No upcoming event found for {name}"}), 404

        event = events[0]
        existing_desc = event.get('description', '')

        # Build add-on note for calendar event
        addon_lines = [f"\n--- PACKAGE UPDATE ({datetime.now().strftime('%m/%d/%Y %I:%M %p')}) ---"]
        addon_lines.append(f"Added via JessicaOnline:")

        # Parse cart items
        catering_package = ''
        catering_price_pp = ''
        catering_total_val = 0
        has_salmon = False
        children_count = 0
        has_theme = False
        theme_desc = ''

        for item in cart_items:
            item_id = item.get('id', '')
            item_name = item.get('name', '')
            qty = item.get('quantity', 1)
            price = item.get('price', 0)
            line_total = item.get('line_total', price * qty)

            addon_lines.append(f"  • {item_name} — ${line_total:.2f}")

            if item_id.startswith('catering-') and item_id not in ('catering-salmon', 'catering-kids'):
                catering_package = item_name
                catering_price_pp = str(item.get('price_per_person', price))
                catering_total_val = line_total
            elif item_id == 'catering-salmon':
                has_salmon = True
            elif item_id == 'catering-kids':
                children_count = qty
            elif item_id == 'theme-room':
                has_theme = True
                theme_desc = item.get('theme_description', '')

        addon_lines.append(f"  ADDED TOTAL: ${cart_total:.2f}")

        # Update calendar event description
        new_desc = existing_desc + '\n'.join(addon_lines)
        event['description'] = new_desc

        updated_event = cal_service.events().update(
            calendarId=calendar_id,
            eventId=event['id'],
            body=event
        ).execute()
        print(f"CALENDAR UPDATED with add-ons for {name}")

        # Calculate new totals
        # Try to extract existing total from description or CRM
        existing_total = 0
        try:
            # Look for previous total in description
            for line in existing_desc.split('\n'):
                if 'TOTAL PACKAGE' in line.upper() or 'total_price' in line.lower():
                    import re
                    nums = re.findall(r'\$?([\d,]+\.?\d*)', line)
                    if nums:
                        existing_total = float(nums[-1].replace(',', ''))
                        break
        except:
            pass

        # Use CRM notes if no total found
        if not existing_total:
            existing_total = float(customer.get('total_price', '0') or '0')

        new_total = existing_total + cart_total
        new_deposit = new_total / 2
        total_paid = float(customer.get('last_payment_amount', '0') or '0')
        new_balance = new_total - total_paid

        # Build contract data
        event_start = event.get('start', {}).get('dateTime', '')
        summary_parts = event.get('summary', '').split(' - ')
        event_type = summary_parts[1] if len(summary_parts) > 2 else 'Event'
        status = 'CONFIRMED' if 'CONFIRMED' in event.get('summary', '') else 'PENCILED'

        contract_data = {
            'customer_name': name,
            'customer_email': customer.get('email', email),
            'customer_phone': phone,
            'event_type': event_type.strip(),
            'venue': event.get('location', ''),
            'event_date': event_start[:10] if event_start else '',
            'event_time': '',
            'guest_count': str(guest_count) if guest_count else customer.get('guest_count', ''),
            'total_price': f"{new_total:.2f}",
            'venue_price': f"{existing_total:.2f}",
            'deposit_amount': f"{new_deposit:.2f}",
            'total_paid': f"{total_paid:.2f}",
            'balance_due': f"{new_balance:.2f}",
            'themed_setup': has_theme or 'THEMED' in existing_desc.upper(),
            'theme_description': theme_desc,
            'early_bird': 'early bird' in existing_desc.lower(),
            'status': status,
            'confirmation_number': customer.get('confirmation_number', ''),
            'catering_package': catering_package,
            'catering_price_pp': catering_price_pp,
            'catering_total': f"{catering_total_val:.2f}" if catering_total_val else '',
            'catering_salmon': has_salmon,
            'children_count': str(children_count) if children_count else '',
            'payments': [],
        }

        # Add existing payment if any
        if total_paid > 0:
            contract_data['payments'].append({
                'date': customer.get('last_payment_date', ''),
                'amount': f"{total_paid:.2f}",
                'confirmation': customer.get('confirmation_number', '')
            })

        # Generate updated contract, email, store in Drive
        contract_result = handle_contract(contract_data, is_update=True)

        # Update CRM
        crm_service.upsert_customer(phone, {
            "name": name,
            "email": customer.get('email', email),
            "total_price": f"{new_total:.2f}",
            "notes": f"Package updated via JessicaOnline. Added ${cart_total:.2f} in add-ons. New total: ${new_total:.2f}",
        })

        print(f"ADD TO PACKAGE: Complete for {name} | New total: ${new_total:.2f}")

        return jsonify({
            "success": True,
            "message": f"Items added to your event package! An updated contract has been sent to {customer.get('email', email)}.",
            "new_total": f"{new_total:.2f}",
            "new_balance": f"{new_balance:.2f}",
            "new_deposit": f"{new_deposit:.2f}",
            "contract": contract_result,
        }), 200

    except Exception as e:
        print(f"ADD TO PACKAGE ERROR: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to update package: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
