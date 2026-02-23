import requests
import json

# URL of your live Render server
BASE_URL = "https://natashavapi.onrender.com"
TOOL_URL = f"{BASE_URL}/calendar-tool"

def test_live_server():
    print(f"🔍 Testing connection to: {BASE_URL}")
    try:
        ping = requests.get(BASE_URL)
        print(f"📡 Server Ping: {ping.status_code} - {ping.text}")
    except Exception as e:
        print(f"❌ Could not reach server: {e}")
        return

    print("\n🚀 Sending Mock Event Booking...")
    
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_test_debug",
                    "function": {
                        "name": "book_appointment",
                        "arguments": {
                            "summary": "DEBUG TEST: Buffer Check",
                            "start_time": "2026-07-20T10:00:00-05:00",
                            "end_time": "2026-07-20T14:00:00-05:00",
                            "is_event": True,
                            "attendee_email": "natashashoe4@gmail.com",
                            "description": "Final verification test."
                        }
                    }
                }
            ]
        }
    }
    
    try:
        response = requests.post(TOOL_URL, json=payload)
        print(f"Status: {response.status_code}")
        
        try:
            result = response.json()
            print(f"Response Body: {json.dumps(result, indent=2)}")
        except:
            print(f"Raw Response Content (Not JSON): {response.text}")

        if response.status_code == 200:
            print("\n✅ Success! Check June 15, 2026 on your calendar.")
        else:
            print("\n❌ Server returned an error. This usually means a credential mismatch or a crash in the logic.")
            
    except Exception as e:
        print(f"❌ Test script error: {e}")

if __name__ == "__main__":
    test_live_server()
