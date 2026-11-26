"""Run once (and again if the login expires): python login_google.py"""
from google_auth_oauthlib.flow import InstalledAppFlow

from connectors.google_auth import CREDS_FILE, SCOPES, TOKEN_FILE

if not CREDS_FILE.exists():
    raise SystemExit("credentials.json not found in the project folder. See the Google setup steps.")

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
creds = flow.run_local_server(port=0)
TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
print("Logged in. Saved token.json (it is in .gitignore, never commit it).")