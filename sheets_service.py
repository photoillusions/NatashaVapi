import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    """Authenticates using environment variables and returns the Sheets service."""
    try:
        creds = Credentials(
            token=None,
            refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=SCOPES
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"❌ Sheets Auth Error: {e}")
        return None

def log_call_to_sheet(spreadsheet_id, call_data):
    """
    Appends a new row of call data to the specified Google Sheet.
    call_data: list of values [Timestamp, Name, Phone, Summary, Duration, Disposition]
    """
    service = get_sheets_service()
    if not service:
        return "Error: Sheets service unavailable."

    # Add timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp] + call_data

    try:
        body = {
            'values': [row]
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A:A",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        return f"Success: Logged to Sheet. Cells updated: {result.get('updates').get('updatedCells')}"
    except Exception as e:
        print(f"❌ Sheets Logging Error: {e}")
        return f"Error logging to sheet: {str(e)}"
