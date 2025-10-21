## Steps to add OAuth Desktop flow

1) Place `client_secret.json` (downloaded from Google Cloud Console) next to the scripts that will run the auth flow.

2) Run a one-off bootstrap that triggers the local consent screen; it will write `token.json` with access + refresh tokens scoped to your chosen Gmail scopes (e.g., `gmail.readonly`).

3) For everyday use, load the persisted token file rather than re-running the flow:

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
```

4) Build the Gmail API client and call endpoints:

```python
from googleapiclient.discovery import build

service = build("gmail", "v1", credentials=creds)
res = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=10).execute()
```

5) Integrate with your repository/services by isolating OAuth logic in a helper that returns structured data your code understands (e.g., EmailRecords). Consider environment-based configuration later for non-local use.

6) Handle errors (e.g., `HttpError`) and consider backoff for continuous ingestion.

