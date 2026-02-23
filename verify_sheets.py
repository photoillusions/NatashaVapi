import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Same scopes as the service
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def test_sheets():
    print("--- Testing Google Sheets Connection ---")
    
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN") or input("Paste GOOGLE_REFRESH_TOKEN: ").strip()
    client_id = os.environ.get("GOOGLE_CLIENT_ID") or input("Paste GOOGLE_CLIENT_ID: ").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or input("Paste GOOGLE_CLIENT_SECRET: ").strip()
    sheet_id = os.environ.get("GOOGLE_SHEET_ID") or "12MUWG3t5t9HTEihQzJ3XYKCYWk4es9KJa1i7uOcZEFQ"
    
    if not all([refresh_token, client_id, client_secret, sheet_id]):
        print("❌ Error: Missing one or more environment variables.")
        print(f"REFRESH_TOKEN: {'✅' if refresh_token else '❌'}")
        print(f"CLIENT_ID: {'✅' if client_id else '❌'}")
        print(f"CLIENT_SECRET: {'✅' if client_secret else '❌'}")
        print(f"SHEET_ID: {'✅' if sheet_id else '❌'}")
        return

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        
        # Try to write a test row
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, "Test Name", "Test Phone", "Integration Check", "0s", "TEST"]
        
        body = {'values': [row]}
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Sheet1!A:A",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        
        print(f"✅ Success! Wrote a test row to sheet: {sheet_id}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("1. Sheets API not enabled in Google Cloud Console.")
        print("2. Token was not generated with 'Sheets' checkbox checked.")
        print("3. Spreadsheet ID is incorrect.")

if __name__ == "__main__":
    test_sheets()
