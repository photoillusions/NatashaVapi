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

SYSTEM_PROMPT = """You are "Jessica," the Booking Concierge for Natasha Mae's Enterprises."""

@app.route('/', methods=['GET'])
def home():
    return "Natasha Mae's Server Online (v5 - FIXED ARGS)"

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
