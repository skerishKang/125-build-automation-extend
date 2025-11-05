#!/usr/bin/env python3
"""
Bot Runner - Start All 4 Bots Simultaneously
Main Bot: Task distribution and user interaction
Document Bot: PDF, DOCX, TXT processing
Audio Bot: OGG, MP3, WAV transcription
Image Bot: JPG, PNG analysis
"""
import os
import sys
import asyncio
import logging
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bot_runner")

# Bot processes
bots = {
    "main": {
        "script": "main_bot/main_bot.py",
        "name": "Main Bot",
        "description": "Task distribution & user interaction"
    },
    "document": {
        "script": "document_bot/document_bot.py",
        "name": "Document Bot",
        "description": "PDF, DOCX, TXT processing"
    },
    "audio": {
        "script": "audio_bot/audio_bot.py",
        "name": "Audio Bot",
        "description": "OGG, MP3, WAV transcription"
    },
    "image": {
        "script": "image_bot/image_bot.py",
        "name": "Image Bot",
        "description": "JPG, PNG analysis"
    }
}

running_bots = {}


async def start_bot(bot_key: str, bot_info: dict):
    """Start a single bot process"""
    bot_name = bot_info["name"]
    bot_script = bot_info["script"]

    logger.info(f"Starting {bot_name}...")

    try:
        # Set PYTHONPATH for subprocess
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

        process = await asyncio.create_subprocess_exec(
            sys.executable, bot_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env
        )

        running_bots[bot_key] = {
            "process": process,
            "info": bot_info
        }

        logger.info(f"[OK] {bot_name} started successfully (PID: {process.pid})")

        # Read output
        while True:
            line = await process.stdout.readline()
            if not line:
                break

            # Log with bot prefix
            logger.info(f"[{bot_name}] {line.decode().strip()}")

        # Wait for process to complete
        return_code = await process.wait()
        if return_code != 0:
            logger.error(f"[ERROR] {bot_name} exited with code {return_code}")

    except Exception as e:
        logger.error(f"[ERROR] Failed to start {bot_name}: {e}")


async def start_all_bots():
    """Start all 4 bots concurrently"""
    print("\n" + "="*60)
    print("4-BOT DISTRIBUTED SYSTEM")
    print("="*60 + "\n")

    print("Starting bots...\n")

    # Create tasks for all bots
    tasks = [
        start_bot(bot_key, bot_info)
        for bot_key, bot_info in bots.items()
    ]

    try:
        # Run all bots concurrently
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("\n[SHUTDOWN] Signal received")
        await shutdown_bots()


async def shutdown_bots():
    """Shutdown all running bots"""
    print("\n" + "="*60)
    print("SHUTTING DOWN ALL BOTS")
    print("="*60 + "\n")

    # Terminate all bots
    for bot_key, bot_data in list(running_bots.items()):
        process = bot_data["process"]
        bot_name = bot_data["info"]["name"]

        if process.returncode is None:  # Still running
            logger.info(f"Terminating {bot_name}...")
            process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=5)
                logger.info(f"[OK] {bot_name} terminated gracefully")
            except asyncio.TimeoutError:
                logger.warning(f"[WARNING] {bot_name} didn't respond, killing...")
                process.kill()
                await process.wait()
                logger.info(f"[OK] {bot_name} killed")

    print("\nAll bots stopped. Goodbye!\n")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"\nSignal {signum} received, initiating shutdown...")
    asyncio.create_task(shutdown_bots())


async def main():
    """Main function"""
    print("\n" + "="*60)
    print("4-BOT DISTRIBUTED SYSTEM")
    print("="*60 + "\n")

    # Check environment
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        "MAIN_BOT_TOKEN",
        "DOCUMENT_BOT_TOKEN",
        "AUDIO_BOT_TOKEN",
        "IMAGE_BOT_TOKEN",
        "GEMINI_API_KEY_MAIN",
        "GEMINI_API_KEY_DOCUMENT",
        "GEMINI_API_KEY_AUDIO",
        "GEMINI_API_KEY_IMAGE"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"[ERROR] Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print(f"\nPlease set these in your .env file")
        return 1

    # Check Redis connection
    try:
        import redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0
        )
        r.ping()
        print("✅ Redis connection: OK\n")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Make sure Redis is running\n")

    # Print bot information
    print("📋 Bot Configuration:")
    for bot_key, bot_info in bots.items():
        print(f"   {bot_key.upper():12} - {bot_info['name']:20} ({bot_info['description']})")

    print("\n" + "="*60 + "\n")

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await start_all_bots()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
