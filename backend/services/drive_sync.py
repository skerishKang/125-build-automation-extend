"""
Google Drive Sync Service - Monitor and Sync Drive ↔ Telegram
"""
import os
import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import tempfile

logger = logging.getLogger("drive_sync")

# Service account key file path
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'service_account.json')

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Cache the service object
_drive_service = None

# Your Drive Folder ID (from pasted URL)
FOLDER_ID = "19hVkhtfoX1s7EVzoeuc8bvo2mosBJg75"

# Track last seen files
LAST_CHECK_FILE = os.path.join(tempfile.gettempdir(), 'drive_sync_last_check.json')
DELETED_FILES_TRACKER = os.path.join(tempfile.gettempdir(), 'drive_sync_deleted_files.json')

# Cache current files for deletion detection
CACHE_FILE = os.path.join(tempfile.gettempdir(), 'drive_sync_cache.json')


def get_drive_service():
    """Get or create Google Drive service object"""
    global _drive_service

    if _drive_service is None:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            _drive_service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise

    return _drive_service


def get_folder_files(folder_id: str = None, max_results: int = 50) -> List[Dict[str, Any]]:
    """Get all files in a specific folder"""
    service = get_drive_service()
    folder_id = folder_id or FOLDER_ID

    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, webContentLink)"
        ).execute()

        items = results.get('files', [])
        logger.info(f"Found {len(items)} files in folder")
        return items

    except Exception as e:
        logger.error(f"Error getting folder files: {e}")
        return []


def get_file_info(file_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific file"""
    service = get_drive_service()

    try:
        file = service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, size, createdTime, modifiedTime, webViewLink, webContentLink'
        ).execute()

        return file

    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return None


def download_file(file_id: str, destination_path: str) -> bool:
    """Download a file from Google Drive"""
    service = get_drive_service()

    try:
        request = service.files().get_media(fileId=file_id)

        with open(destination_path, 'wb') as fh:
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"Download {int(status.progress() * 100)}%")

        logger.info(f"File downloaded successfully to {destination_path}")
        return True

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return False


def upload_file(file_path: str, folder_id: str = None, file_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Upload a file to Google Drive"""
    service = get_drive_service()
    folder_id = folder_id or FOLDER_ID

    try:
        file_name = file_name or os.path.basename(file_path)

        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink, mimeType, createdTime'
        ).execute()

        logger.info(f"File uploaded successfully: {file_name} (ID: {file['id']})")
        return file

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return None


def save_last_check(timestamp: str):
    """Save the last check timestamp"""
    try:
        with open(LAST_CHECK_FILE, 'w') as f:
            json.dump({'last_check': timestamp}, f)
    except Exception as e:
        logger.error(f"Error saving last check: {e}")


def load_last_check() -> str:
    """Load the last check timestamp"""
    try:
        if os.path.exists(LAST_CHECK_FILE):
            with open(LAST_CHECK_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_check', '1970-01-01T00:00:00.000Z')
    except Exception as e:
        logger.error(f"Error loading last check: {e}")

    return '1970-01-01T00:00:00.000Z'


def cache_current_files(files: List[Dict[str, Any]]):
    """Cache current file list for deletion detection"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'cached_files': {f['id']: f for f in files},
                'last_cache_update': datetime.utcnow().isoformat() + 'Z'
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error caching files: {e}")


def load_cached_files() -> Dict[str, Dict[str, Any]]:
    """Load cached file list"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('cached_files', {})
    except Exception as e:
        logger.error(f"Error loading cached files: {e}")
    return {}


def check_deleted_files(current_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Check for deleted files by comparing with cached file list"""
    cached_files = load_cached_files()
    current_file_ids = {f['id'] for f in current_files}
    cached_file_ids = set(cached_files.keys())

    # Find deleted files (in cache but not in current)
    deleted_file_ids = cached_file_ids - current_file_ids

    deleted_files = []
    for file_id in deleted_file_ids:
        if file_id in cached_files:
            deleted_files.append(cached_files[file_id])

    if deleted_files:
        logger.info(f"Found {len(deleted_files)} deleted files")
        # Update cache with current files
        cache_current_files(current_files)

    return deleted_files


def save_last_check(timestamp: str):
    """Save the last check timestamp"""
    try:
        with open(LAST_CHECK_FILE, 'w') as f:
            json.dump({'last_check': timestamp}, f)
    except Exception as e:
        logger.error(f"Error saving last check: {e}")


def check_new_files() -> List[Dict[str, Any]]:
    """Check for new files uploaded since last check"""
    service = get_drive_service()
    last_check = load_last_check()
    folder_id = FOLDER_ID

    try:
        # Query for files modified after last check
        query = f"'{folder_id}' in parents and trashed = false and modifiedTime > '{last_check}'"

        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)"
        ).execute()

        files = results.get('files', [])

        if files:
            logger.info(f"Found {len(files)} new files")
            # Update last check time
            save_last_check(datetime.utcnow().isoformat() + 'Z')
            # Update cache
            cache_current_files(get_folder_files())

        return files

    except Exception as e:
        logger.error(f"Error checking new files: {e}")
        return []


def format_file_list(files: List[Dict[str, Any]]) -> str:
    """Format file list for Telegram message"""
    if not files:
        return "📁 드라이브에 파일이 없습니다."

    lines = [f"📁 **Google Drive 파일 목록** (총 {len(files)}개):\n"]

    for i, file in enumerate(files, 1):
        # Check if it's a folder
        if file.get('mimeType') == 'application/vnd.google-apps.folder':
            file_type = "📁 폴더"
            size_str = ""
        else:
            file_type = "📄 파일"
            size = file.get('size', '0')
            if size and size != '0':
                size_int = int(size)
                if size_int > 1024 * 1024:
                    size_str = f"{size_int / (1024 * 1024):.1f}MB"
                elif size_int > 1024:
                    size_str = f"{size_int / 1024:.1f}KB"
                else:
                    size_str = f"{size_int}B"
            else:
                size_str = "N/A"

        # Format the entry
        line = f"{i}. {file_type}: **{file['name']}**\n"
        line += f"   ID: `{file['id']}`"
        if size_str:
            line += f" | 크기: {size_str}"
        line += f"\n   생성일: {file.get('createdTime', 'N/A')[:10]}\n"

        if 'webViewLink' in file:
            line += f"   링크: {file['webViewLink']}\n"

        lines.append(line)

    return "\n".join(lines)
