"""
Google Drive Service - Upload files and manage folders
Supports both Service Account and OAuth User Credentials
"""
import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class GoogleDriveService:
    """Service for interacting with Google Drive API"""
    
    def __init__(
        self,
        credentials_path: str,
        folder_id: str = None,
        use_oauth: bool = False,
        token_path: str = None
    ):
        self.credentials_path = credentials_path
        self.folder_id = folder_id
        self.use_oauth = use_oauth
        self.token_path = token_path or credentials_path.replace('.json', '_token.json')
        self.service = self._build_service()
        self.folder_cache = {}  # Cache folder IDs
    
    def _build_service(self):
        """Build Google Drive service"""
        SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        if self.use_oauth:
            # OAuth User Credentials flow
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_path):
                import pickle
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(InstalledAppFlow._GOOGLE_AUTH_URL)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save token for next time
                import pickle
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            return build('drive', 'v3', credentials=creds)
        else:
            # Service Account flow
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )
            return build('drive', 'v3', credentials=creds)
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """Create a folder in Google Drive"""
        if folder_name in self.folder_cache:
            return self.folder_cache[folder_name]
        
        # Check if folder exists
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields='files(id, name)'
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            folder_id = files[0]['id']
            self.folder_cache[folder_name] = folder_id
            return folder_id
        
        # Create new folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        try:
            folder = self.service.files().create(
                body=folder_metadata,
                supportsAllDrives=True,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            self.folder_cache[folder_name] = folder_id
            return folder_id
        except HttpError as e:
            print(f"Error creating folder {folder_name}: {e}")
            return None
    
    def upload_file(
        self,
        file_path: str,
        folder_id: str,
        filename: str = None
    ) -> Optional[str]:
        """Upload a file to Google Drive folder"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        if filename is None:
            filename = os.path.basename(file_path)
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        try:
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields='id, name, webViewLink'
            ).execute()
            
            print(f"Uploaded: {filename} (ID: {file.get('id')})")
            return file.get('id')
            
        except HttpError as e:
            print(f"Error uploading {filename}: {e}")
            return None
    
    def upload_json_data(
        self,
        data: Dict,
        folder_id: str,
        filename: str = None
    ) -> Optional[str]:
        """Upload JSON data directly"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data_{timestamp}.json"
        
        # Save to temp file
        temp_path = f"/tmp/{filename}"
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        file_id = self.upload_file(temp_path, folder_id, filename)
        
        # Cleanup
        os.remove(temp_path)
        
        return file_id
    
    def list_files_in_folder(self, folder_id: str, max_results: int = 100) -> List[Dict]:
        """List all files in a folder"""
        query = f"'{folder_id}' in parents and trashed=false"

        results = self.service.files().list(
            q=query,
            pageSize=max_results,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields='files(id, name, mimeType, createdTime, modifiedTime, size)'
        ).execute()

        return results.get('files', [])

    def get_drive_stats(self) -> Dict:
        """Get statistics of all crawled articles stored in Drive"""
        stats = {
            'total_files': 0,
            'total_articles': 0,
            'by_source': {},
            'last_updated': None,
            'oldest_file': None,
            'sources_detail': []
        }

        try:
            # List all sub-folders in main folder (one per source)
            folder_query = (
                f"'{self.folder_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"trashed=false"
            )
            folders_result = self.service.files().list(
                q=folder_query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields='files(id, name, createdTime)'
            ).execute()

            folders = folders_result.get('files', [])

            for folder in folders:
                source_name = folder['name']
                files = self.list_files_in_folder(folder['id'], max_results=1000)

                source_articles = 0
                source_latest = None

                for f in files:
                    # Each JSON file contains crawled articles
                    if f['name'].endswith('.json'):
                        source_articles += 1

                        modified = f.get('modifiedTime', '')
                        if source_latest is None or modified > source_latest:
                            source_latest = modified

                        if stats['last_updated'] is None or modified > stats['last_updated']:
                            stats['last_updated'] = modified

                        if stats['oldest_file'] is None or modified < stats['oldest_file']:
                            stats['oldest_file'] = modified

                stats['by_source'][source_name] = {
                    'files': len(files),
                    'json_files': source_articles,
                    'latest_update': source_latest
                }

                stats['total_files'] += len(files)
                stats['total_articles'] += source_articles

                stats['sources_detail'].append({
                    'name': source_name,
                    'file_count': len(files),
                    'json_count': source_articles,
                    'latest': source_latest
                })

        except Exception as e:
            stats['error'] = str(e)

        return stats

    def ensure_source_folder(self, source_name: str) -> str:
        """Ensure folder exists for a news source, create if not"""
        return self.create_folder(source_name, self.folder_id)
    
    def upload_crawled_data(
        self,
        articles: List[Dict],
        source_name: str,
        folder_name: str
    ) -> Dict:
        """Upload crawled articles for a source"""
        # Ensure folder exists
        folder_id = self.ensure_source_folder(folder_name)
        
        # Save data locally with date format: dd-mm-yyyy_HH-MM-SS
        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        local_filename = f"{folder_name}_{timestamp}.json"
        local_path = f"/tmp/{local_filename}"
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump({
                'source': source_name,
                'folder': folder_name,
                'crawled_at': datetime.now().isoformat(),
                'article_count': len(articles),
                'articles': articles
            }, f, ensure_ascii=False, indent=2)
        
        # Upload to Drive
        file_id = self.upload_file(local_path, folder_id, local_filename)
        
        # Cleanup
        os.remove(local_path)
        
        return {
            'source': source_name,
            'folder_id': folder_id,
            'file_id': file_id,
            'article_count': len(articles)
        }


# Singleton instance
_drive_service = None


def get_drive_service() -> GoogleDriveService:
    """Get singleton Drive service instance"""
    global _drive_service
    
    if _drive_service is None:
        credentials_path = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH', './configs/google-drive-credentials.json')
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        use_oauth = os.environ.get('GOOGLE_DRIVE_USE_OAUTH', 'false').lower() == 'true'
        client_secret_path = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET', credentials_path)
        
        _drive_service = GoogleDriveService(
            credentials_path if not use_oauth else client_secret_path,
            folder_id,
            use_oauth=use_oauth
        )
    
    return _drive_service
