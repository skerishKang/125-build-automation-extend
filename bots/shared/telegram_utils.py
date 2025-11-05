"""
Telegram Utilities - Shared Telegram Bot Functions
"""
import os
import logging
import tempfile
from telegram import Update, Bot
from telegram.ext import Application
from typing import Optional

logger = logging.getLogger("telegram_utils")


class TelegramClient:
    """Shared Telegram bot client"""

    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.application = Application.builder().token(bot_token).build()

    async def send_message(self, chat_id: str, text: str, parse_mode: str = None) -> Optional[int]:
        """Send message to chat"""
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return message.message_id
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return None

    async def send_photo(self, chat_id: str, photo_path: str, caption: str = None) -> Optional[int]:
        """Send photo to chat"""
        try:
            with open(photo_path, 'rb') as f:
                message = await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=caption
                )
            return message.message_id
        except Exception as e:
            logger.error(f"Send photo error: {e}")
            return None

    async def send_document(self, chat_id: str, doc_path: str, caption: str = None) -> Optional[int]:
        """Send document to chat"""
        try:
            with open(doc_path, 'rb') as f:
                message = await self.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    caption=caption
                )
            return message.message_id
        except Exception as e:
            logger.error(f"Send document error: {e}")
            return None

    async def edit_message(self, chat_id: str, message_id: int, text: str) -> bool:
        """Edit existing message"""
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )
            return True
        except Exception as e:
            logger.error(f"Edit message error: {e}")
            return False

    async def delete_message(self, chat_id: str, message_id: int) -> bool:
        """Delete message"""
        try:
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
            return True
        except Exception as e:
            logger.error(f"Delete message error: {e}")
            return False

    async def download_file(self, file_id: str, suffix: str = "") -> Optional[str]:
        """Download file from Telegram"""
        try:
            file = await self.bot.get_file(file_id)
            temp_path = os.path.join(
                tempfile.gettempdir(),
                f"telegram_{file_id}{suffix}"
            )
            await file.download_to_drive(temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"Download file error: {e}")
            return None

    async def get_file(self, file_id: str):
        """Retrieve a file reference from Telegram without downloading."""
        try:
            return await self.bot.get_file(file_id)
        except Exception as e:
            logger.error(f"Get file error: {e}")
            return None


async def send_progress_message(
    bot: Bot,
    chat_id: str,
    text: str,
    emoji: str = "⏳"
) -> Optional[int]:
    """Send progress message with emoji"""
    return await bot.send_message(
        chat_id=chat_id,
        text=f"{emoji} {text}"
    )


async def send_success_message(
    bot: Bot,
    chat_id: str,
    text: str
) -> Optional[int]:
    """Send success message"""
    return await bot.send_message(
        chat_id=chat_id,
        text=f"✅ {text}"
    )


async def send_error_message(
    bot: Bot,
    chat_id: str,
    error: str
) -> Optional[int]:
    """Send error message"""
    return await bot.send_message(
        chat_id=chat_id,
        text=f"❌ Error: {error}"
    )


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def extract_text_from_file(file_path: str) -> Optional[str]:
    """Extract text from various file formats"""
    try:
        import chardet

        # Try to detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            enc = chardet.detect(raw_data).get('encoding') or 'utf-8'

        # Decode and return text
        return raw_data.decode(enc, errors='ignore')
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return None


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()


# Common file processing functions
def is_text_file(filename: str) -> bool:
    """Check if file is text-based"""
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
        '.html', '.htm', '.css', '.scss', '.json', '.xml',
        '.csv', '.tsv', '.yaml', '.yml', '.ini', '.cfg',
        '.conf', '.log', '.sql', '.sh', '.bat', '.ps1',
        '.dockerfile', '.gitignore', '.env', '.properties',
        '.toml', '.r', '.R', '.cpp', '.c', '.h', '.hpp',
        '.java', '.kt', '.go', '.rs', '.php', '.rb'
    }
    ext = get_file_extension(filename)
    return ext in text_extensions


def is_document_file(filename: str) -> bool:
    """Check if file is a document format"""
    doc_extensions = {
        '.pdf', '.docx', '.doc', '.pptx', '.ppt',
        '.xlsx', '.xls', '.odt', '.rtf'
    }
    ext = get_file_extension(filename)
    return ext in doc_extensions


def is_image_file(filename: str) -> bool:
    """Check if file is an image"""
    image_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.webp', '.svg', '.tiff', '.ico'
    }
    ext = get_file_extension(filename)
    return ext in image_extensions


def is_audio_file(filename: str) -> bool:
    """Check if file is audio"""
    audio_extensions = {
        '.mp3', '.wav', '.ogg', '.m4a', '.aac',
        '.flac', '.wma', '.opus'
    }
    ext = get_file_extension(filename)
    return ext in audio_extensions


if __name__ == "__main__":
    # Test utilities
    print("Telegram Utils Module Loaded")
    print(f"Text file check: {is_text_file('test.py')}")
    print(f"Image file check: {is_image_file('photo.jpg')}")
    print(f"Audio file check: {is_audio_file('song.mp3')}")
    print(f"Document file check: {is_document_file('report.pdf')}")
    print(f"File size format: {format_file_size(1024000)}")  # 1MB
