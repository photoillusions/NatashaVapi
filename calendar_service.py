"""
VAPI ASSISTANT FIXER
This updates the Assistant's inline tool definitions (not just standalone tools).
"""

import requests
import json

API_KEY = "fbc467c0-5e14-4a9b-afe0-7d33486ade3f"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

ASSISTANT_ID = "5b9978af-44ec-44bd-ab9f-30cdb409bb8d"

def fix_assistant():
    """Update the assistant to use only toolIds (remove inline tool definitions)"""
    print("=" * 60)
    print("VAPI ASSISTANT FIXER")
    print("=" * 60)
    
    # First, get current assistant config
    print("\n1. Fetching current assistant config...")
    url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"ERROR: Could not fetch assistant: {response.status_code}")
        print(response.text)
        return False
    
    assistant = response.json()
    print(f"   Found assistant: {assistant.get('name')}")
    
    # Check current model.tools
    current_tools = assistant.get('model', {}).get('tools', [])
    print(f"   Current inline tools: {len(current_tools)}")
    
    for tool in current_tools:
        func = tool.get('function', {})
        print(f"   - {func.get('name')}")
        params = func.get('parameters', {}).get('properties', {})
        for param_name, param_config in params.items():
            if 'default' in param_config:
                print(f"     WARNING: {param_name} has default='{param_config['default']}'")
    
    # Build fixed tool definitions
    print("\n2. Building fixed tool definitions...")
    
    fixed_tools = [
        {
            "type": "function",
            "function": {
                "name": "send_sms_link",
                "description": "Sends a text message with a link/brochure/invoice to the caller",
                "parameters": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["tour", "packages", "registration", "invoice", "vault_map", "liberty_map", "frankford_map"],
                            "description": "The type of information to send"
                        }
                    }
                }
            },
            "messages": [{"type": "request-start", "content": "I'm sending that to your phone now.", "blocking": False}],
            "server": {"url": "https://natashavapi.onrender.com/send-sms", "timeoutSeconds": 20},
            "async": False
        },
        {
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": "Checks if a date/time is available on the calendar. ALWAYS use before confirming availability.",
                "parameters": {
                    "type": "object",
                    "required": ["start_time", "end_time"],
                    "properties": {
                        "start_time": {
                            "type": "string",
                            "description": "ISO 8601 datetime like 2026-10-17T17:00:00-04:00"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "ISO 8601 datetime like 2026-10-17T18:00:00-04:00"
                        }
                    }
                }
            },
            "messages": [{"type": "request-start", "content": "Let me check our availability for that date...", "blocking": False}],
            "server": {"url": "https://natashavapi.onrender.com/calendar-tool", "timeoutSeconds": 20},
            "async": False
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Books a tour or event after availability is confirmed.",
                "parameters": {
                    "type": "object",
                    "required": ["summary", "start_time", "end_time"],
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Format: EventType - Venue - CustomerName"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "ISO 8601 datetime like 2026-10-17T17:00:00-04:00"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "ISO 8601 datetime like 2026-10-17T23:00:00-04:00"
                        },
                        "attendee_email": {
                            "type": "string",
                            "description": "Optional email address for calendar invite"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional notes about the booking"
                        }
                    }
                }
            },
            "messages": [{"type": "request-start", "content": "Perfect, I'm booking that for you now...", "blocking": False}],
            "server": {"url": "https://natashavapi.onrender.com/calendar-tool", "timeoutSeconds": 20},
            "async": False
        }
    ]
    
    # Update the assistant
    print("\n3. Updating assistant with fixed tools...")
    
    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "tools": fixed_tools,
            "toolIds": []  # Clear toolIds since we're using inline tools
        }
    }
    
    response = requests.patch(url, json=payload, headers=HEADERS)
    
    if response.status_code == 200:
        print("   SUCCESS! Assistant updated.")
        
        # Verify the update
        print("\n4. Verifying update...")
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            updated = response.json()
            tools = updated.get('model', {}).get('tools', [])
            print(f"   New inline tools: {len(tools)}")
            
            all_good = True
            for tool in tools:
                func = tool.get('function', {})
                name = func.get('name')
                params = func.get('parameters', {}).get('properties', {})
                
                has_defaults = False
                for param_name, param_config in params.items():
                    if 'default' in param_config:
                        print(f"   WARNING: {name}.{param_name} still has default!")
                        has_defaults = True
                        all_good = False
                
                if not has_defaults:
                    print(f"   OK: {name} - no defaults")
            
            if all_good:
                print("\n" + "=" * 60)
                print("ALL TOOLS FIXED! Test by calling in now.")
                print("=" * 60)
                return True
    else:
        print(f"   FAILED: {response.status_code}")
        print(f"   {response.text}")
        return False
    
    return False


if __name__ == "__main__":
    fix_assistant()
