import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# SCOPES required for the assistant
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/spreadsheets'
]

def main():
    print("--- Google Calendar Token Generator ---")
    print("1. Make sure you have 'credentials.json' in this folder.")
    print("   (Download it from Google Cloud Console -> APIs & Services -> Credentials -> Create OAuth Client ID -> Desktop App)")
    
    if not os.path.exists('credentials.json'):
        print("\n❌ ERROR: 'credentials.json' not found!")
        print("Please download it and save it in this directory.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    
    # Run the local server flow to let the user log in via browser
    creds = flow.run_local_server(port=0)

    print("\n✅ Authentication Successful!")
    print("\n--- SAVE THESE TO RENDER ENVIRONMENT VARIABLES ---")
    
    # Extract the necessary values
    # Note: Client ID and Secret are already in credentials.json, but handy to print here too if needed.
    # The most important one is the REFRESH TOKEN.
    
    print(f"\nGOOGLE_CLIENT_ID: {creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET: {creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN: {creds.refresh_token}")
    
    print("\n----------------------------------------------")
    print("Copy the values above and paste them into your Render.com Service Settings -> Environment.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        input("Press Enter to exit...")
