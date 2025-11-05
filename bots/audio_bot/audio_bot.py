#!/usr/bin/env python3
"""
Audio Bot - Specialized Audio Processing
Role: OGG, MP3, WAV audio transcription using Whisper + Gemini AI analysis
"""
import os
import sys
import json
import logging
import tempfile
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
        logging.FileHandler('audio_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("audio_bot")

# Configuration
AUDIO_BOT_TOKEN = os.getenv("AUDIO_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_AUDIO")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Initialize
messenger = BotMessenger("audio_bot")
gemini = GeminiAnalyzer(GEMINI_API_KEY)
telegram_client = TelegramClient(AUDIO_BOT_TOKEN)


async def download_audio_from_telegram(file_id: str, file_name: str) -> str:
    """Download audio file from Telegram and return local path"""
    try:
        # Get file from Telegram
        file = await telegram_client.get_file(file_id)

        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file_name)

        # Download file
        await file.download_to_drive(file_path)

        logger.info(f"Downloaded audio: {file_name} to {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        raise


async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file using Whisper"""
    try:
        from faster_whisper import WhisperModel

        logger.info("Loading Whisper model...")

        # Use small model for faster processing
        # Options: tiny, base, small, medium, large
        model_size = "small"
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        logger.info(f"Transcribing audio with Whisper ({model_size})...")

        # Transcribe
        segments, info = model.transcribe(
            file_path,
            language='ko',  # Detect language automatically
            beam_size=5
        )

        transcription = []
        for segment in segments:
            transcription.append(segment.text)

        full_transcription = " ".join(transcription)

        logger.info(f"Transcribed {len(full_transcription)} characters")
        return full_transcription

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise


async def process_audio_task(task_data: Dict):
    """Process audio transcription task"""
    data = task_data.get('data', task_data)
    try:
        chat_id = data.get('chat_id')
        voice_data = data.get('voice_data', {})
        file_id = voice_data.get('file_id')
        duration = voice_data.get('duration', 0)
        mime_type = voice_data.get('mime_type', 'audio/ogg')

        # Determine file extension from mime type
        ext_map = {
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav'
        }
        file_ext = ext_map.get(mime_type, '.ogg')
        file_name = f"voice_{int(time.time())}{file_ext}"

        logger.info(f"Processing audio: {file_name} ({duration}s) for chat {chat_id}")

        # Send progress update
        messenger.notify_progress(chat_id, "오디오를 다운로드하는 중...")

        # Download audio file
        file_path = await download_audio_from_telegram(file_id, file_name)

        # Send progress update
        messenger.notify_progress(chat_id, "Whisper로 음성을 인식하는 중...")

        # Transcribe audio
        transcription = await transcribe_audio(file_path)

        if not transcription.strip():
            transcription = "[음성 인식 결과 없음]"

        # Send progress update
        messenger.notify_progress(chat_id, "Gemini AI로 분석하는 중...")

        # Analyze with Gemini AI
        summary = gemini.analyze_audio(transcription)

        # Prepare result
        result = {
            "transcription": transcription,
            "summary": summary,
            "duration": duration,
            "file_name": file_name,
            "processed_at": datetime.now().isoformat()
        }

        # Send result to main bot
        messenger.send_result(chat_id, result)

        # Clean up
        try:
            os.remove(file_path)
            os.rmdir(os.path.dirname(file_path))
        except:
            pass

        logger.info(f"Completed audio transcription for chat {chat_id}")

    except Exception as e:
        logger.error(f"Error processing audio task: {e}")
        # Send error result
        error_result = {
            "error": str(e),
            "duration": data.get('voice_data', {}).get('duration', 0)
        }
        messenger.send_result(data.get('chat_id'), error_result)


async def listen_for_tasks():
    """Listen for audio processing tasks"""
    logger.info("Audio bot started, listening for tasks...")

    pubsub = messenger.pubsub
    if not pubsub:
        logger.info("[MOCK] Redis disabled - audio bot in standby mode")
        while True:
            await asyncio.sleep(60)
        return
    pubsub.subscribe("audio_tasks")

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
                    await process_audio_task(data)
                except Exception as e:
                    logger.error(f"Error processing task: {e}")

            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            await asyncio.sleep(1.0)


async def main():
    """Main function"""
    print("=== Audio Bot (Audio Processing) ===")

    if not AUDIO_BOT_TOKEN:
        print("[ERROR] ERROR: AUDIO_BOT_TOKEN is missing")
        print("Please set AUDIO_BOT_TOKEN in .env file")
        return

    if not GEMINI_API_KEY:
        print("[WARN] WARNING: GEMINI_API_KEY is missing - AI features will be disabled")

    try:
        # Test Telegram connection
        bot = Bot(token=AUDIO_BOT_TOKEN)
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
    import asyncio
    asyncio.run(main())
