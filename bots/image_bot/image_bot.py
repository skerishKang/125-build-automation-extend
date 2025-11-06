#!/usr/bin/env python3
"""
Image Bot - Specialized Image Processing
Role: JPG, PNG, GIF, WEBP image analysis using Gemini Vision AI
"""
import os
import sys
import json
import logging
import tempfile
import base64
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from telegram import Bot
from bots.shared.redis_utils import BotMessenger  # type: ignore
from bots.shared.gemini_client import GeminiAnalyzer  # type: ignore
from bots.shared.telegram_utils import TelegramClient  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("image_bot")

# Configuration
IMAGE_BOT_TOKEN = os.getenv("IMAGE_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_IMAGE")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Initialize
messenger = BotMessenger("image_bot")
gemini = GeminiAnalyzer(GEMINI_API_KEY)
telegram_client = TelegramClient(IMAGE_BOT_TOKEN)


async def download_image_from_telegram(file_id: str, file_name: str) -> str:
    """Download image file from Telegram and return local path"""
    try:
        # Get file from Telegram
        file = await telegram_client.get_file(file_id)

        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file_name)

        # Download file
        await file.download_to_drive(file_path)

        logger.info(f"Downloaded image: {file_name} to {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        raise


def encode_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        logger.error(f"Error encoding image: {e}")
        raise


async def process_image_task(task_data: Dict):
    """Process image analysis task"""
    data = task_data.get('data', task_data)

    try:
        chat_id = data.get('chat_id')
        image_data = data.get('image_data', {})

        file_path = image_data.get('file_path')

        logger.info(f"Processing image from path: {file_path} for chat {chat_id}")

        messenger.notify_progress(chat_id, "이미지를 분석하는 중...")

        description = gemini.analyze_image_description(file_path)
        analysis = gemini.analyze_image_description(file_path)

        result = {
            "description": description,
            "analysis": analysis,
            "processed_at": datetime.now().isoformat()
        }

        messenger.send_result(chat_id, result)

        try:
            os.remove(file_path)
        except Exception:
            pass

        logger.info(f"Completed image analysis for chat {chat_id}")

    except Exception as e:
        logger.error(f"Error processing image task: {e}")

        error_result = {
            "error": str(e)
        }
        messenger.send_result(data.get('chat_id'), error_result)

        try:
            file_path = image_data.get('file_path')
            if file_path:
                os.remove(file_path)
        except Exception:
            pass


async def listen_for_tasks():
    """Listen for image processing tasks"""
    logger.info("Image bot started, listening for tasks...")

    pubsub = messenger.pubsub
    if not pubsub:
        logger.info("[MOCK] Redis disabled - image bot in standby mode")
        while True:
            await asyncio.sleep(60)
        return
    pubsub.subscribe("image_tasks")

    while True:
        try:
            message = await asyncio.to_thread(
                pubsub.get_message,
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message and message.get('type') == 'message':
                try:
                    data = json.loads(message['data'])
                    await process_image_task(data)
                except Exception as e:
                    logger.error(f"Error processing task: {e}")

            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            await asyncio.sleep(1.0)


async def main():
    """Main function"""
    print("=== Image Bot (Image Processing) ===")

    if not IMAGE_BOT_TOKEN:
        print("[ERROR] ERROR: IMAGE_BOT_TOKEN is missing")
        print("Please set IMAGE_BOT_TOKEN in .env file")
        return

    if not GEMINI_API_KEY:
        print("[WARN] WARNING: GEMINI_API_KEY is missing - AI features will be disabled")

    try:
        # Test Telegram connection
        bot = Bot(token=IMAGE_BOT_TOKEN)
        await bot.get_me()
        print("[OK] Telegram connection successful")
    except Exception as e:
        print(f"[ERROR] ERROR: Failed to connect to Telegram: {e}")
        return

    try:
        # Start listening for tasks
        await listen_for_tasks()
    except KeyboardInterrupt:
        print("\nBYE Shutting down...")
    finally:
        messenger.close()


if __name__ == "__main__":
    import time
    import asyncio
    asyncio.run(main())
