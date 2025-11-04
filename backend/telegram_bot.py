#!/usr/bin/env python3
"""
125 Build Automation - Telegram Bot
간결하고 깔끔한 텔레그램 봇
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import httpx

from dotenv import load_dotenv
load_dotenv()

# 환경변수
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 텔레그램 관련
from telegram import Update, Document
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# 사용자별 문서 저장
user_docs: Dict[int, List[Dict[str, Any]]] = {}

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start 명령어"""
    await update.message.reply_text(
        "🤖 125 Build Automation Bot\n\n"
        "📤 문서를 업로드하고 '/summarize'로 요약해보세요!\n"
        "/help - 도움말"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말"""
    await update.message.reply_text(
        "**명령어:**\n"
        "/start - 시작\n"
        "/summarize - 최근 문서 요약\n"
        "/help - 도움말\n\n"
        "문서를 먼저 업로드하세요!",
        parse_mode='Markdown'
    )

async def summarize_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 요약"""
    user_id = update.effective_user.id

    if user_id not in user_docs or not user_docs[user_id]:
        await update.message.reply_text("❌ 업로드된 문서가 없습니다.")
        return

    latest_doc = user_docs[user_id][-1]
    # 즉시 수신 확인 메시지로 대기 체감 감소
    ack_msg = await update.message.reply_text("📝 요약 중…")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {
                'file': (
                    latest_doc['file_name'],
                    latest_doc['text'].encode('utf-8'),
                    'text/plain'
                )
            }
            response = await client.post(
                "http://127.0.0.1:8000/api/summarize",
                files=files
            )
            if response.status_code == 200:
                result = response.json()
                summary = result.get("summary", "요약 실패")
            else:
                summary = f"❌ 서비스 오류: {response.status_code}"

        final_text = f"**{latest_doc['file_name']}**\n\n{summary}"
        # 완료 시 기존 메시지를 결과로 교체 (실패 시 새로 전송)
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=ack_msg.message_id,
                text=final_text,
                parse_mode='Markdown'
            )
        except Exception:
            await update.message.reply_text(final_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"요약 실패: {e}")
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=ack_msg.message_id,
                text=f"❌ 오류: {str(e)}"
            )
        except Exception:
            await update.message.reply_text(f"❌ 오류: {str(e)}")

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 처리"""
    doc = update.message.document
    if not doc:
        return

    user_id = update.effective_user.id
    file_name = doc.file_name

    # 파일 다운로드
    file = await context.bot.get_file(doc.file_id)
    file_path = f"/tmp/{doc.file_id}_{file_name}"
    await file.download_to_drive(file_path)

    # 텍스트 읽기
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        import chardet
        encoding = chardet.detect(content).get('encoding', 'utf-8')
        text = content.decode(encoding, errors='ignore')

        # 저장 (임시 파일은 정리)
        if user_id not in user_docs:
            user_docs[user_id] = []

        user_docs[user_id].append({
            'file_name': file_name,
            'text': text,
            'timestamp': datetime.now()
        })
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        # 최대 5개까지만
        if len(user_docs[user_id]) > 5:
            old_doc = user_docs[user_id].pop(0)
            if os.path.exists(old_doc.get('file_path', '')):
                os.remove(old_doc['file_path'])

        await update.message.reply_text(
            f"✅ {file_name} 저장됨\n"
            f"길이: {len(text)}자\n"
            "/summarize로 요약하세요!"
        )

    except Exception as e:
        logger.error(f"문서 처리 실패: {e}")
        await update.message.reply_text(f"❌ 처리 실패: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일반 텍스트"""
    await update.message.reply_text("문서를 업로드하세요!")

async def main():
    """메인"""
    print("=== Telegram Bot Starting ===")
    print(f"Token: {'OK' if TELEGRAM_BOT_TOKEN else 'Not Set'}")

    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not found!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 핸들러
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("summarize", summarize_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Handlers registered")
    print("Bot starting...")

    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
