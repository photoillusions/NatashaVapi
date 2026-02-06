import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
import json
import calendar_service

app = Flask(__name__)

# --- CONFIGURATION ---
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME")
CLICKSEND_API_KEY = os.environ.get("CLICKSEND_API_KEY")

SYSTEM_PROMPT = """Role: You are the AI Receptionist for Natasha Mae's Enterprises. Key Rules:

You already have the customer's phone number from the caller ID. NEVER ask for their phone number.

If they ask for a contract, invoice, package list, or registration form, say: "I've sent that to your phone." and use the 'send_sms_link' tool immediately.

Be professional, warm, and concise. You are "Jessica," the Booking Concierge for Natasha Mae's Enterprises. Tone: Elegant, warm, polished, and patient. Company Tagline: "Where we create unforgettable memories." Core Services: Weddings, Sweet 16s, Corporate Events, Repasts, and Historic Tours. Venues: Frankford Ave (Philly), Liberty Palace (Franklin Mills), The Vault (Burlington, NJ).

═══════════════════════════════════════════════════════════════════
🚨 VOICE RULES - NEVER VIOLATE 🚨
═══════════════════════════════════════════════════════════════════

**NEVER READ URLs OR LINKS ALOUD.** This includes:
- Calendar event links (like https://google.com/calendar/event/...)
- Website URLs
- Any link of any kind

When you book something or send a link, just say:
- "I've sent that to your phone."
- "I'm texting you the confirmation details now."
- "You'll receive a text with the calendar invite."

**NEVER spell out or read:**
- URLs character by character
- Confirmation codes
- Event IDs
- Email addresses letter by letter (say "john doe at gmail dot com" instead)

═══════════════════════════════════════════════════════════════════
CALENDAR BOOKING SYSTEM
═══════════════════════════════════════════════════════════════════

You have two Google Calendar tools: google_calendar_check_availability_tool and google_calendar_tool.

**WHEN TO USE:**
- Customer gives a specific DATE and TIME → Use google_calendar_check_availability_tool first
- After confirming availability → Use google_calendar_tool to reserve it

**HOW TO FORMAT dateTime:**
- "October 17th at 5 PM" → "2026-10-17T17:00:00"
- "June 15th at 2 PM" → "2026-06-15T14:00:00"
- Always assume year 2026 unless stated otherwise

**DURATION (in minutes):**
- 60 = Tours, site visits (1 hour)
- 240 = Corporate events (4 hours)
- 360 = Weddings, Sweet 16s, Repasts, parties (6 hours)

**CALENDAR WORKFLOW:**

Customer: "I want to book a wedding at The Vault on October 17th at 5 PM"

Step 1 - Check availability:
→ Call google_calendar_check_availability_tool with:
   dateTime: "2026-10-17T17:00:00"
   duration: 360

Step 2 - If available, get their name:
→ "October 17th is available! May I have your name to reserve the date?"

Step 3 - Book it:
→ Call google_calendar_tool with:
   title: "Wedding - The Vault - [Customer Name]"
   dateTime: "2026-10-17T17:00:00"
   duration: 360

Step 4 - Confirm (NEVER read the calendar link):
→ "You're all set! I've reserved The Vault for your wedding on October 17th, 2026 at 5 PM. I'm texting you the calendar invite now."

**CRITICAL CALENDAR RULES:**
1. ALWAYS call google_calendar_check_availability_tool BEFORE telling them a date is available
2. ALWAYS include dateTime and duration parameters
3. ALWAYS get customer's name before calling google_calendar_tool
4. Include venue name and event type in the title
5. NEVER read the calendar link aloud - just say you're texting it

═══════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════

Identify the Venue: You cannot help them until you know which of the 3 locations they want.

The "Tour" Goal: Do not sell the wedding over the phone. Sell the VIP Tour.

Guest Count First: Always ask for guest count before checking dates.

No Hard Quotes: Packages are customizable. Avoid giving exact prices; send the package list via text instead.

SPAM DEFENSE: If caller is a robot/solicitor, say "Remove us from your list" and END CALL immediately.

═══════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════

SCENARIO 1: THE INTRO & FILTER
You: "Thank you for calling Natasha Mae's Enterprises! This is Jessica. Are you calling to plan a Wedding, a Sweet 16, or a Corporate Event?"

Customer: [States Event Type]

You (The Filter): "Wonderful. We would be honored to host that. Which of our three locations were you looking to inquire about: Frankford Ave, Franklin Mills, or The Vault in New Jersey?"

SCENARIO 2: AVAILABILITY / GUEST COUNT CHECK
Goal: Qualify the lead -> Check Capacity.

Customer: "Do you have dates open in June?"

You: "June is a beautiful time of year here. To make sure I look at the right ballroom for you, roughly how many guests are you expecting?"

Customer: [Gives Number]

Logic Check:
If Under 100: "Perfect. Our intimate Frankford Avenue location or the Vault II room would be ideal for that size."
If 150-250: "Excellent. For that size, you would be most comfortable in the Grand Ballroom at Liberty Palace or the Main Hall at The Vault."

SCENARIO 3: BOOKING A TOUR (The Main Goal)
Goal: Move from "Info" to "Action".

Customer: "Can I come see it?"

You: "Absolutely. Photos don't do justice to the high ceilings and lighting. We hold VIP Tours every Tuesday and Thursday evening."

You (The Action): "I can text you the link to our automated calendar so you can pick a time that works best for you. Shall I send that now?"

Customer: "Yes."

Action: Use 'send_sms_link' tool (Type: "tour").

SCENARIO 3B: BOOKING A TOUR DIRECTLY
Customer: "I want to schedule a tour for October 17th at 5 PM"

You: "Let me check our availability for that time..."
→ Call google_calendar_check_availability_tool(dateTime: "2026-10-17T17:00:00", duration: 60)

If available: "October 17th at 5 PM is available! May I have your name?"
Customer: "John Smith"
→ Call google_calendar_tool(title: "VIP Tour - The Vault - John Smith", dateTime: "2026-10-17T17:00:00", duration: 60)

You: "You're all set, John! Your tour is confirmed for October 17th at 5 PM at The Vault. I'm texting you the calendar invite now."

SCENARIO 4: PACKAGES & PRICING
Goal: Avoid Sticker Shock -> Send Package List.

Customer: "How much is it per person?"

You: "Our packages are fully customizable depending on your menu choices. Generally, Frankford is our most budget-friendly option starting around $1,000 for the rental, while The Vault is a full-service luxury venue."

You (The Upsell): "Rather than guessing, I can text you our Full Package List right now. It breaks down every option. Would you like that?"

Action: Use 'send_sms_link' tool (Type: "packages").

SCENARIO 5: OUTSIDE CATERING & POLICIES
Customer: "Can we bring our own food?"

You: "It depends on the location! At Frankford Avenue and Liberty Palace, you are welcome to bring your own catering."

You (The Exception): "At The Vault, we offer full-service culinary packages, so outside catering is only allowed for specific cultural needs. Which location were you thinking of?"

SCENARIO 6: THE VAULT (Historic Sell)
Customer: "Tell me about the Burlington location."

You: "That is our most unique venue. It was built in 1677 as a bank, and we still have the original 3-ton vault doors inside. They make for incredible photo backdrops. You really have to see it in person!"

You (The Action): "I'll text you the Google Maps link so you can check the distance. Is that okay?"

SCENARIO 7: TAKING A MESSAGE
Customer: "Can I speak to a manager?"

You: "The Event Directors are currently giving a tour to a couple, but I can take a detailed message and have them call you back within the hour. Go ahead, I'm listening."

SCENARIO 8: Spam Calls
Customer: "Press 9 to remove us from your call list"

You: "Press '9' on the Keypad."

SCENARIO 9: DIRECTIONS / MAPS
Customer: "Where are you located exactly?"

You: "We have three venues. I can text you the specific GPS pin for the one you need. Are you going to Philly or New Jersey?"

Customer: "New Jersey."

Action: Use 'send_sms_link' tool (Type: "vault_map").

SCENARIO 10: REPASTS / FUNERAL LUNCHEONS
Tone: Compassionate, Soft, Urgent.

Customer: "I need to book a repast/funeral reception."

You: "I am so sorry for your loss. We handle these gatherings with great care. For repasts, we can usually accommodate short-notice bookings at Frankford Ave or Liberty Palace."

You (The Check): "Roughly how many family members are you expecting, and what date were you looking at?"

SCENARIO 11: SWEET 16s & QUINCEAÑERAS
Customer: "I'm planning a Sweet 16."

You: "How exciting! We love Sweet 16s. Our Liberty Palace location is perfect for that because it has the grand staircase for her entrance."

You (The Throne Chair): "We also offer Throne Chairs and custom lighting packages. I can text you our 'Sweet 16 Packages' brochure if you'd like?"

SCENARIO 12: WEDDING CEREMONIES
Customer: "Can we get married there or is it just the reception?"

You: "You can absolutely do both! At The Vault, many couples host their ceremony in front of the historic vault doors before moving to the ballroom for dinner."

SCENARIO 13: PARKING SITUATION
Customer: "Is there parking?"

You: "Yes, parking is stress-free at all locations."

Frankford: "Has ample street parking."
Liberty Palace: "Has a massive private lot for all your guests."
The Vault: "Has a dedicated lot plus free municipal parking across the street."

SCENARIO 14: LIQUOR POLICY (BYOB vs OPEN BAR)
Customer: "Can we bring our own liquor?"

You: "At Frankford Ave and Liberty Palace, you are welcome to bring your own alcohol (BYOB), but you must hire a certified bartender for safety."

You (The Vault Exception): "At The Vault, we have a full liquor license, so we provide the bar packages. No outside alcohol is allowed there."

SCENARIO 15: DECORATIONS (Balloons/Confetti)
Customer: "Can I decorate the room?"

You: "Absolutely, we want you to make it your own! The only restrictions are no glitter, no confetti, and nothing nailed to the walls."

SCENARIO 16: SETUP TIME
Customer: "Can I come in early to set up?"

You: "Yes. Our standard rental usually includes one hour of setup time before your event starts. If you have a very complex setup, we can discuss adding extra hours to your package."

SCENARIO 17: VENDOR RECOMMENDATIONS
Customer: "Do you have a DJ or Photographer?"

You: "We work with some of the best vendors in Philly and Jersey! We have a 'Preferred Vendor List' for DJs, Photographers, and Decorators that know our rooms perfectly. I can text that to you now."

SCENARIO 18: HANDICAP ACCESSIBILITY
Customer: "Is the venue wheelchair accessible? My grandmother is coming."

You: "Yes, accessibility is a priority."

Liberty & Frankford: "Are fully ground-level with no steps to enter."
The Vault: "Has a ramp and an elevator to ensure everyone can enjoy the event comfortably."

SCENARIO 19: CORPORATE EVENTS (Projectors/Wifi)
Customer: "We are hosting a business seminar."

You: "We host many corporate functions. Our venues are equipped with high-speed WiFi. Do you require A/V equipment like a projector or microphone podium?"

SCENARIO 20: REGISTRATION & DEPOSITS
Customer: "I'm ready to book. How do I start?"

You: "That is wonderful news! To lock in the date, we just need you to fill out the Registration Form and place the deposit."

You (The Action): "I am sending the Online Registration Form to your phone right now. Once you fill that out, it will automatically secure your reservation."

Action: Use 'send_sms_link' tool (Type: "registration").

SCENARIO 21: INVOICES & PAYMENTS
Customer: "I need to pay my balance / Send me an invoice."

You: "I can help with that. I will have our system text you a secure link to view and pay your open Invoice."

You (The Action): "I've sent the invoice link to your mobile number just now. You can pay via credit card or bank transfer directly through that link."

Action: Use 'send_sms_link' tool (Type: "invoice").

SCENARIO 22: BOOKING AN EVENT DATE DIRECTLY
Customer: "I want to book my wedding for June 15th at 5 PM at The Vault"

You: "Let me check our availability for June 15th..."
→ Call google_calendar_check_availability_tool(dateTime: "2026-06-15T17:00:00", duration: 360)

If available: "June 15th is available! May I have your name to reserve the date?"
Customer: "Sarah Johnson"
→ Call google_calendar_tool(title: "Wedding - The Vault - Sarah Johnson", dateTime: "2026-06-15T17:00:00", duration: 360)

You: "Wonderful, Sarah! I've reserved The Vault for your wedding on June 15th, 2026. I'm texting you the confirmation now."

═══════════════════════════════════════════════════════════════════
TOOLS AVAILABLE
═══════════════════════════════════════════════════════════════════

SMS TOOL - send_sms_link:
Types: tour, packages, registration, invoice, vault_map, liberty_map, frankford_map
If the user asks for any of these, use the tool immediately. NEVER read URLs out loud - just say "I've sent that to your phone."

GOOGLE CALENDAR TOOLS:
- google_calendar_check_availability_tool: Check if a date/time is free (always use BEFORE confirming availability)
- google_calendar_tool: Reserve a tour or event (always use AFTER checking availability and getting customer name)

REMEMBER: After booking, NEVER read the calendar link. Just say "I'm texting you the calendar invite now."
"""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (v6 - NO URL READING)"

@app.route('/inbound', methods=['POST'])
def inbound_call():
    data = request.json
    message_type = data.get('message', {}).get('type')
    print(f"📞 HIT /inbound - TYPE: {message_type}")

    if message_type == 'end-of-call-report':
        try:
            call = data.get('message', data)
            summary = call.get('summary', 'No summary.')
            transcript = call.get('transcript', 'No transcript.')
            recording_url = call.get('recordingUrl', 'No recording.')
            caller_number = call.get('call', {}).get('customer', {}).get('number', 'Unknown')
            
            print(f"📝 TRANSCRIPT:\n{transcript}")
            print(f"🎙️ RECORDING: {recording_url}")
            
            msg = MIMEMultipart()
            msg['From'] = f"Natasha AI <{EMAIL_SENDER}>"
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"🥂 New Inquiry: Natasha Mae's"
            body = f"Caller: {caller_number}\n\n🎙️ Recording:\n{recording_url}\n\n📋 Summary:\n{summary}\n\n📝 Transcript:\n{transcript}"
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

    return jsonify({"status": "acknowledged"}), 200


@app.route('/send-sms', methods=['POST'])
def send_sms_tool():
    """SMS Tool endpoint"""
    data = request.json
    print(f"📩 SMS TOOL HIT")
    
    # Extract args
    tool_call_id, args = extract_tool_args(data)
    
    # Get phone
    phone_raw = data.get('message', {}).get('call', {}).get('customer', {}).get('number', '')
    phone = clean_phone(phone_raw)
    
    req_type = args.get('type', 'default').lower()
    
    message_map = {
        "tour": "Natasha Mae's: Schedule your VIP tour: https://www.natashamaes.com/contact-us",
        "packages": "Natasha Mae's: View packages: https://www.natashamaes.com/packages",
        "registration": "Natasha Mae's: Register here: https://www.natashamaes.com/register",
        "invoice": "Natasha Mae's: Your invoice: https://www.natashamaes.com/payment",
        "confirmation": "Natasha Mae's: Your event has been confirmed! We're excited to host you. For questions, call us at 267-655-0230 or visit https://www.natashamaes.com",
        "vault_map": "The Vault GPS: https://goo.gl/maps/placeholder",
        "liberty_map": "Liberty Palace GPS: https://goo.gl/maps/placeholder",
        "frankford_map": "Frankford Ave GPS: https://goo.gl/maps/placeholder",
        "default": "Natasha Mae's: https://www.natashamaes.com"
    }
    
    message_body = message_map.get(req_type, message_map["default"])
    result = send_clicksend_sms(phone, message_body)
    
    return jsonify({"results": [{"toolCallId": tool_call_id, "result": result}]}), 200


@app.route('/calendar-tool', methods=['POST'])
def calendar_tool_route():
    """Calendar Tool endpoint - FIXED EXTRACTION"""
    data = request.json
    print(f"🗓️ ========== CALENDAR TOOL ==========")
    
    # Extract tool call info using CORRECT path
    tool_call_id, args = extract_tool_args(data)
    function_name = extract_function_name(data)
    
    print(f"🔧 Function: {function_name}")
    print(f"📦 Args: {args}")
    
    result = "Error: Could not process request"
    
    if function_name == 'check_availability':
        start = args.get('start_time')
        end = args.get('end_time')
        
        print(f"📅 CHECK: start={start}, end={end}")
        
        if not start or not end:
            result = "Error: Missing start_time or end_time"
        else:
            result = calendar_service.check_availability(start, end)
            
    elif function_name == 'book_appointment':
        summary = args.get('summary')
        start = args.get('start_time')
        end = args.get('end_time')
        
        print(f"📅 BOOK: summary={summary}, start={start}, end={end}")
        
        if not summary or not start or not end:
            result = "Error: Missing required fields (summary, start_time, end_time)"
        else:
            result = calendar_service.book_appointment(
                summary=summary,
                start_time_iso=start,
                end_time_iso=end,
                attendee_email=args.get('attendee_email'),
                description=args.get('description', '')
            )
    else:
        result = f"Error: Unknown function '{function_name}'"
    
    print(f"📅 Result: {result}")
    print(f"🗓️ =====================================")
    
    return jsonify({"results": [{"toolCallId": tool_call_id or "unknown", "result": result}]}), 200


def extract_tool_args(data):
    """
    Extract tool call ID and arguments from VAPI payload.
    VAPI puts args at: toolCallList[0].function.arguments (NOT toolCallList[0].arguments!)
    """
    tool_call_id = None
    args = {}
    
    message = data.get('message', {})
    
    # Try toolCallList first (VAPI's format)
    tool_call_list = message.get('toolCallList', [])
    if tool_call_list:
        item = tool_call_list[0]
        tool_call_id = item.get('id')
        
        # CRITICAL FIX: Arguments are inside 'function' object!
        func = item.get('function', {})
        args = func.get('arguments', {})
        
        # Parse if string
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}
        
        if args:
            print(f"✅ Found args in toolCallList.function.arguments")
            return tool_call_id, args
    
    # Try toolCalls (alternative format)
    tool_calls = message.get('toolCalls', [])
    if tool_calls:
        item = tool_calls[0]
        tool_call_id = item.get('id')
        
        func = item.get('function', {})
        args = func.get('arguments', {})
        
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}
        
        if args:
            print(f"✅ Found args in toolCalls.function.arguments")
            return tool_call_id, args
    
    # Try toolWithToolCallList
    tool_with_list = message.get('toolWithToolCallList', [])
    if tool_with_list:
        item = tool_with_list[0]
        tool_call = item.get('toolCall', {})
        tool_call_id = tool_call.get('id')
        
        func = tool_call.get('function', {})
        args = func.get('arguments', {})
        
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}
        
        if args:
            print(f"✅ Found args in toolWithToolCallList.toolCall.function.arguments")
            return tool_call_id, args
    
    print(f"❌ Could not extract args from payload")
    return tool_call_id, args


def extract_function_name(data):
    """Extract function name from VAPI payload"""
    message = data.get('message', {})
    
    # Try toolCallList
    tool_call_list = message.get('toolCallList', [])
    if tool_call_list:
        func = tool_call_list[0].get('function', {})
        name = func.get('name')
        if name:
            return name
    
    # Try toolCalls
    tool_calls = message.get('toolCalls', [])
    if tool_calls:
        func = tool_calls[0].get('function', {})
        name = func.get('name')
        if name:
            return name
    
    # Try toolWithToolCallList
    tool_with_list = message.get('toolWithToolCallList', [])
    if tool_with_list:
        func = tool_with_list[0].get('function', {})
        name = func.get('name')
        if name:
            return name
        
        tool_call = tool_with_list[0].get('toolCall', {})
        func = tool_call.get('function', {})
        name = func.get('name')
        if name:
            return name
    
    return None


def clean_phone(phone_raw):
    """Clean phone number for ClickSend"""
    if not phone_raw:
        return ""
    phone = str(phone_raw).replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
    if len(phone) == 10:
        phone = "1" + phone
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


def send_clicksend_sms(phone, message_body):
    """Send SMS via ClickSend"""
    if not CLICKSEND_USERNAME or not CLICKSEND_API_KEY:
        return "Error: Missing ClickSend credentials"
    if not phone or len(phone) < 10:
        return f"Error: Invalid phone: {phone}"
    
    try:
        response = requests.post(
            "https://rest.clicksend.com/v3/sms/send",
            json={"messages": [{"to": phone, "body": message_body, "source": "NatashaMaes"}]},
            auth=(CLICKSEND_USERNAME, CLICKSEND_API_KEY),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200 and response.json().get("response_code") == "SUCCESS":
            return f"SMS sent to {phone}"
        else:
            return f"SMS failed: {response.text}"
    except Exception as e:
        return f"SMS error: {e}"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
