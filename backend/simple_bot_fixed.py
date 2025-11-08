#!/usr/bin/env python3
"""
125 Build Automation Bot - Fixed Event Loop Issue (Final Version)
Based on official python-telegram-bot documentation
"""
import os
import asyncio
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# 환경변수 로드 - backend/.env 파일 직접 지정
from dotenv import load_dotenv
env_file_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_file_path)

# 환경변수 확인
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

print("=== Environment Variables Check ===")
print(f"Env file path: {env_file_path}")
print(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not Found'}")
print(f"GEMINI_API_KEY: {'Set' if GEMINI_API_KEY else 'Not Found'}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Basic text handler"""
    user_name = update.effective_user.first_name or "User"
    await update.message.reply_text(
        f"Hello {user_name}! 125 Build Automation Bot is running normally.\n\n"
        "Supported features:\n"
        "- Document upload and analysis\n"
        "- AI-based summarization and Q&A\n"
        "- Various file formats support (.pdf, .docx, .txt, etc.)\n\n"
        "Upload a document to test!"
    )

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_name = update.effective_user.first_name or "User"
    await update.message.reply_text(
        f"Hello {user_name}!\n\n"
        "Welcome to 125 Build Automation Bot.\n\n"
        "This bot analyzes and summarizes documents using AI.\n\n"
        "Please upload a document or send a text message!"
    )

async def main():
    """Main bot function - Based on official documentation with proper shutdown"""
    print("=== Starting Telegram Bot (Fixed Final Version) ===")
    
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set!")
        return
    
    # Create application using ApplicationBuilder (official method)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    try:
        # Register handlers
        application.add_handler(CommandHandler("start", handle_start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        print("OK: Handlers registered")
        print("OK: Starting bot polling...")
        
        # Method: Manual initialization and startup (official pattern)
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        print("SUCCESS: Bot is running... Press Ctrl+C to stop")
        print("INFO: Bot ready to receive messages")
        
        # Keep running until interruption
        try:
            # Simple wait loop instead of infinite sleep
            while True:
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("\nINFO: Shutdown requested...")
        
    except Exception as e:
        print(f"ERROR during execution: {e}")
        raise
    finally:
        # Clean shutdown in proper order
        try:
            if hasattr(application, 'updater') and application.updater.running:
                await application.updater.stop()
            if application.running:
                await application.stop()
            await application.shutdown()
            print("SUCCESS: Clean shutdown completed")
        except Exception as e:
            print(f"WARNING: Shutdown error: {e}")

if __name__ == "__main__":
    print("125 Build Automation - Fixed Bot (Final)")
    try:
        # Create a proper event loop with cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(main())
        except KeyboardInterrupt:
            print("\nINFO: Bot stopped by user")
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            if pending:
                try:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
            
            loop.close()
            
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)