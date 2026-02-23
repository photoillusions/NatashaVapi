import os
import datetime
import time
import json
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """Returns the Calendar service using Service Account or Refresh Token."""
    start_time = time.time()
    # 1. Try Service Account Authentication (Preferred)
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            print("🔑 Attempting Service Account authentication...")
            info = json.loads(service_account_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            return build('calendar', 'v3', credentials=creds)
        except Exception as e:
            print(f"⚠️ Service Account Auth failed: {e}")
    
    # 2. Fallback to Refresh Token Auth
    print("🔑 Attempting Refresh Token authentication fallback...")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN2") or os.environ.get("GOOGLE_REFRESH_TOKEN")
    client_id = os.environ.get("GOOGLE_CLIENT_ID2") or os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET2") or os.environ.get("GOOGLE_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print(f"❌ Missing Google OAuth credentials: RT={'set' if refresh_token else 'MISSING'}, ID={'set' if client_id else 'MISSING'}, SEC={'set' if client_secret else 'MISSING'}")
        return None

    try:
        creds = Credentials(
            token=None, 
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Refresh Token Auth Error: {e}")
        return None
    finally:
        print(f"⏱️ Authentication took {time.time() - start_time:.2f} seconds")

def check_availability(start_time_iso, end_time_iso):
    """
    Checks for conflicts in the given time range.
    start_time_iso, end_time_iso: ISO strings (e.g., '2023-10-27T10:00:00-04:00')
    """
    service = get_calendar_service()
    if not service:
        return "Error: Calendar service unavailable."

    print(f"📅 Checking availability from {start_time_iso} to {end_time_iso}")
    
    calendar_id = os.environ.get("CALENDAR_ID", "primary")
    
    events_result = service.events().list(
        calendarId=calendar_id, 
        timeMin=start_time_iso,
        timeMax=end_time_iso,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])

    if not events:
        return "available"
    
    # Return details about the conflict so the AI can explain
    conflict_desc = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', 'Busy')
        conflict_desc.append(f"{summary} at {start}")
    
    return f"Conflict: {', '.join(conflict_desc)}"

def book_appointment(summary, start_time_iso, end_time_iso, attendee_email=None, description=""):
    """
    Books an appointment on the primary calendar.
    """
    service = get_calendar_service()
    if not service:
        return "Error: Calendar service unavailable."

    print(f"📅 Booking '{summary}' for {start_time_iso}")

    event_body = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time_iso,
        },
        'end': {
            'dateTime': end_time_iso,
        },
    }
    
    # Add attendee if provided (sends them an invite)
    if attendee_email:
        event_body['attendees'] = [{'email': attendee_email}]

    try:
        calendar_id = os.environ.get("CALENDAR_ID", "primary")
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return f"Success: Event created. Link: {event.get('htmlLink')}"
    except Exception as e:
        print(f"❌ Error creating event: {e}")
        return f"Error creating event: {str(e)}"
