"""
Google Drive Service Integration for Telegram Bot
"""
import os
import logging
from typing import List, Dict, Optional, Any
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

logger = logging.getLogger("google_drive")

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Service account key file path
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'service_account.json')

# Cache the service object
_drive_service = None


def get_drive_service():
    """
    Get or create Google Drive service object using service account
    """
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


def list_files(folder_id: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    List files in Google Drive (optionally in a specific folder)

    Args:
        folder_id: ID of the folder to list files from (None for root)
        max_results: Maximum number of files to return

    Returns:
        List of file dictionaries
    """
    try:
        service = get_drive_service()

        query = f"'{folder_id}' in parents" if folder_id else "trashed = false"
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)"
        ).execute()

        items = results.get('files', [])
        return items

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return []


def upload_file(file_path: str, folder_id: Optional[str] = None, file_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Upload a file to Google Drive

    Args:
        file_path: Path to the file to upload
        folder_id: ID of the folder to upload to (None for root)
        file_name: Name for the file (defaults to basename if not provided)

    Returns:
        File metadata dictionary or None if failed
    """
    try:
        service = get_drive_service()

        file_name = file_name or os.path.basename(file_path)

        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink'
        ).execute()

        logger.info(f"File uploaded successfully: {file_name} (ID: {file['id']})")
        return file

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return None


def download_file(file_id: str, destination_path: str) -> bool:
    """
    Download a file from Google Drive

    Args:
        file_id: ID of the file to download
        destination_path: Path to save the downloaded file

    Returns:
        True if successful, False otherwise
    """
    try:
        service = get_drive_service()

        request = service.files().get_media(fileId=file_id)

        with open(destination_path, 'wb') as fh:
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


def create_folder(name: str, parent_id: Optional[str] = None) -> Optional[str]:
    """
    Create a folder in Google Drive

    Args:
        name: Name of the folder
        parent_id: ID of the parent folder (None for root)

    Returns:
        Folder ID if successful, None otherwise
    """
    try:
        service = get_drive_service()

        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        logger.info(f"Folder created successfully: {name} (ID: {folder['id']})")
        return folder['id']

    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        return None


def get_file_info(file_id: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a file

    Args:
        file_id: ID of the file

    Returns:
        File metadata dictionary or None if failed
    """
    try:
        service = get_drive_service()
        file = service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, size, createdTime, modifiedTime, webViewLink, webContentLink'
        ).execute()

        return file

    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return None


def delete_file(file_id: str) -> bool:
    """
    Delete a file from Google Drive

    Args:
        file_id: ID of the file to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()

        logger.info(f"File deleted successfully: {file_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return False


def share_file(file_id: str, email: str, role: str = 'reader') -> bool:
    """
    Share a file with a specific email

    Args:
        file_id: ID of the file to share
        email: Email address to share with
        role: Permission role ('reader', 'writer', 'commenter')

    Returns:
        True if successful, False otherwise
    """
    try:
        service = get_drive_service()

        permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }

        service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()

        logger.info(f"File shared successfully with {email}")
        return True

    except Exception as e:
        logger.error(f"Error sharing file: {e}")
        return False
