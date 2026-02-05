import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """Authenticates using environment variables and returns the Calendar service."""
    # We use the Refresh Token flow for server-side auth
    try:
        creds = Credentials(
            token=None, # access_token is None, we'll fetch it using refresh_token
            refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Calendar Auth Error: {e}")
        return None

def check_availability(start_time_iso, end_time_iso):
    """
    Checks for conflicts in the given time range.
    start_time_iso, end_time_iso: ISO strings (e.g., '2023-10-27T10:00:00-04:00')
    """
    service = get_calendar_service()
    if not service:
        return "Error: Calendar service unavailable."

    print(f"📅 Checking availability from {start_time_iso} to {end_time_iso}")
    
    events_result = service.events().list(
        calendarId='primary', 
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
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"Success: Event created. Link: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {str(e)}"
