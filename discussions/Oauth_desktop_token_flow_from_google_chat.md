## OAuth Desktop token flow (from Google Chat)

To access your Gmail account from your local environment using OAuth, you'll need to configure a Google Cloud project, create OAuth credentials, and then integrate those into your local application. This process ensures secure access without exposing your Gmail password.

### Step 1: Set up a Google Cloud project

- Go to the Google Cloud Console: `https://console.cloud.google.com`
- Create a new project (if needed):
  - Project selector → New Project → Name it (e.g., "My Local Gmail App") → Create
- Select your new project in the project selector dropdown

### Step 2: Enable the Gmail API

- Navigate to APIs & Services → Enabled APIs & Services
- Click "+ Enable APIs and Services"
- Search for "Gmail API" → Enable

### Step 3: Configure the OAuth consent screen

- APIs & Services → OAuth consent screen
- Choose user type:
  - External (likely for local/testing)
- Fill in app information:
  - App name, support email, developer contact
- Add scopes (start with minimal necessary):
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/gmail.send`
  - `https://www.googleapis.com/auth/gmail.compose`
  - `https://www.googleapis.com/auth/gmail.modify`
- Add test users (for External apps): add your testing accounts
- Save and return to dashboard

### Step 4: Create OAuth Client ID credentials

- APIs & Services → Credentials → + Create Credentials → OAuth client ID
- Application type:
  - Desktop app (recommended for local desktop flows)
  - Alternatively Web application for a local web server
- If Web app: set Authorized origins/redirect URIs (e.g., `http://localhost:8000`, `http://localhost:8000/oauth2callback`)
- Name the client → Create → Download credentials JSON (keep it secure)

### Step 5: Integrate OAuth into your local application

- Use Google client libraries to run the Installed App (Desktop) flow
- On first run, a browser opens for consent; the app stores `token.json` with refresh + access tokens
- Reuse `token.json` next runs, refreshing silently when needed

#### Conceptual Python example (google-auth-oauthlib)

```python
# pip install google-auth-oauthlib google-api-python-client
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", labelIds=["INBOX"]).execute()
        messages = results.get("messages", [])
        if not messages:
            print("No messages found.")
            return
        print("Messages:")
        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            print(f"- ID: {msg['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()
```

### Notes

- Keep `client_secret.json` private; treat the client secret like a password
- Store `token.json` securely; it contains refresh credentials
- Start with the narrowest scopes your app needs

