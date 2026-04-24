"""
One-time Gmail OAuth2 setup script.
Run this ONCE to get your GMAIL_REFRESH_TOKEN.
Then paste the token into your .env file.

Usage:
  python utils/gmail_auth.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()


def main():
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")

    if not (client_id and client_secret):
        print("\n[ERROR] Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env first.\n")
        print("Steps:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project → Enable Gmail API + Google Sheets API")
        print("  3. OAuth Consent Screen → External → Add your email as test user")
        print("  4. Create Credentials → OAuth 2.0 Client ID → Desktop App")
        print("  5. Paste client_id and client_secret into .env")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
    )

    creds = flow.run_local_server(port=0)

    print("\n" + "="*60)
    print("  AUTH SUCCESSFUL")
    print("="*60)
    print(f"\nAdd this to your .env file:\n")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
