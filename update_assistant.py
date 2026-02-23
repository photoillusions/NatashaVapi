import requests
import json

API_KEY = "fbc467c0-5e14-4a9b-afe0-7d33486ade3f"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
ASSISTANT_ID = "5b9978af-44ec-44bd-ab9f-30cdb409bb8d"

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

TOOLS = [
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
        "server": {"url": "https://natashavapi.onrender.com/calendar-tool", "timeoutSeconds": 30},
        "async": False
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
        "server": {"url": "https://natashavapi.onrender.com/calendar-tool", "timeoutSeconds": 30},
        "async": False
    },
    {
        "type": "function",
        "function": {
            "name": "send_info_email",
            "description": "Emails the customer detailed package and pricing information for their venue of interest. Use this instead of texting.",
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
        "server": {"url": "https://natashavapi.onrender.com/info-email-tool", "timeoutSeconds": 30},
        "async": False
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
        "server": {"url": "https://natashavapi.onrender.com/payment-tool", "timeoutSeconds": 30},
        "async": False
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
        "server": {"url": "https://natashavapi.onrender.com/booking-email-tool", "timeoutSeconds": 30},
        "async": False
    }
]

def update():
    url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"

    # 1. Get current config
    print("1. Fetching current assistant...")
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED to fetch: {resp.status_code} {resp.text}")
        return
    current = resp.json()
    print(f"   Name: {current.get('name')}")
    old_tools = current.get('model', {}).get('tools', [])
    print(f"   Current tools: {len(old_tools)}")
    for t in old_tools:
        fn = t.get('function', {})
        print(f"     - {fn.get('name')}")

    # 2. Update
    print("\n2. Updating assistant...")
    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-5-mini",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "tools": TOOLS,
            "toolIds": []
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "EXAVITQu4vr4xnSDxMaL"
        },
        "firstMessage": "Thank you for calling Natasha Mae's Enterprises. This is Jessica. Are you inquiring about our Philadelphia locations or The Vault in New Jersey?",
        "serverMessages": ["conversation-update", "end-of-call-report", "speech-update", "status-update", "tool-calls"],
        "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "en-US"}
    }

    resp = requests.patch(url, json=payload, headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED to update: {resp.status_code}")
        print(resp.text[:500])
        return

    print("   Update sent!")

    # 3. Verify
    print("\n3. Verifying...")
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        updated = resp.json()
        new_tools = updated.get('model', {}).get('tools', [])
        prompt = updated.get('model', {}).get('messages', [{}])[0].get('content', '')
        print(f"   Tools: {len(new_tools)}")
        for t in new_tools:
            fn = t.get('function', {})
            srv = t.get('server', {}).get('url', 'N/A')
            print(f"     - {fn.get('name')} -> {srv}")
        print(f"   Prompt length: {len(prompt)}")
        print(f"   Has PENCILED: {'PENCILED' in prompt}")
        print(f"   Has NEVER text: {'NEVER offer to text' in prompt}")
        print(f"   Has send_sms_link: {'send_sms_link' in prompt}")
        print(f"   Has send_info_email: {'send_info_email' in prompt}")
        print(f"   Voice: {updated.get('voice', {}).get('voiceId', 'N/A')}")

        sms_in_tools = any(t.get('function',{}).get('name') == 'send_sms_link' for t in new_tools)
        if sms_in_tools:
            print("\n   WARNING: send_sms_link still in tools!")
        else:
            print("\n   send_sms_link REMOVED from tools")

        print("\n" + "="*50)
        print("DONE! Test by calling in now.")
        print("="*50)

if __name__ == "__main__":
    update()
