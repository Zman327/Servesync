from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import datetime
import os

# Path to your OAuth 2.0 Desktop JSON
OAUTH_FILE = os.path.join(os.path.dirname(__file__), 'client_secret_26915404481-9hb1v0m38fm6b5tvsgf6i60fu5pm2k4c.apps.googleusercontent.com.json')

# Token file to store credentials
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.pickle')

# Shared Drive folder ID
DRIVE_FOLDER_ID = '1JaeKjES4yge5QO__3_xovb_loLItaLsG'

# Path to your database
DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'Servesync', 'ServeSync.db')
if not os.path.exists(DB_FILE):
    raise FileNotFoundError(f"Database file not found: {DB_FILE}")

# Scopes required
SCOPES = ['https://www.googleapis.com/auth/drive.file']

creds = None

# Load existing token
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)

# If no valid credentials, do OAuth flow
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(OAUTH_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    # Save credentials for next run
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)

# Build the Drive service
service = build('drive', 'v3', credentials=creds)

# Create a timestamped filename
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"servesync_backup_{timestamp}.db"

# Upload to Google Drive
file_metadata = {
    'name': filename,
    'parents': [DRIVE_FOLDER_ID]
}
media = MediaFileUpload(DB_FILE, mimetype='application/x-sqlite3')

uploaded_file = service.files().create(
    body=file_metadata,
    media_body=media,
    fields='id',
    supportsAllDrives=True
).execute()

print(f"✅ Backup uploaded successfully! File ID: {uploaded_file.get('id')}")
