"""One-time login that prints the Google Drive OAuth refresh token.

Usage (from backend/):
    python scripts/get_drive_refresh_token.py client_secret.json
`client_secret.json` is the "Desktop app" OAuth client downloaded from Google
Cloud Console. A browser opens; sign in with the Drive account that should own
the exported files. Put the printed values in .env.
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

if len(sys.argv) != 2:
    sys.exit(__doc__)

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
# offline + consent forces Google to return a refresh token.
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
if not creds.refresh_token:
    sys.exit("No refresh token returned. Revoke the app's access and retry.")

print(f"GOOGLE_DRIVE_OAUTH_CLIENT_ID={creds.client_id}")
print(f"GOOGLE_DRIVE_OAUTH_CLIENT_SECRET={creds.client_secret}")
print(f"GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
