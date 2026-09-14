import os
from dotenv import load_dotenv
load_dotenv()

CREDENTIALS_PATH = './configs/google-drive-credentials.json'
FOLDER_ID = '1c-vgDstkdKKeISW9uj3gjhw5n1z4lqJs'

from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
print(f'Email: {creds.service_account_email}')

service = build('drive', 'v3', credentials=creds)
query = f"'{FOLDER_ID}' in parents and trashed=false"
results = service.files().list(q=query, pageSize=10, fields='files(id, name)').execute()
files = results.get('files', [])
print(f'Files: {len(files)}')
for f in files:
    print(f'  - {f["name"]}')
