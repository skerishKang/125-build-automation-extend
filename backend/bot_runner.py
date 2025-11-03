#!/usr/bin/env python3
"""
125 Build Automation - Telegram Bot Runner
별도 프로세스로 실행되는 텔레그램 봇
"""
import os
import asyncio
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

# 환경변수 로드
from dotenv import load_dotenv
env_file_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_file_path)

# 환경변수 확인
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 텔레그램 관련 import
try:
    from telegram import Update, Document
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        ContextTypes, filters
    )
except ImportError:
    logger.error("python-telegram-bot이 설치되지 않았습니다")
    logger.error("pip install python-telegram-bot==21.6 을 실행해주세요")
    sys.exit(1)


# AI 서비스 import (동적으로)
ai_service = None
try:
    from backend.services.ai_service import summarize_text, analyze_document, rag_answer
    ai_service = 'backend'
except ImportError:
    try:
        from services.ai_service import summarize_text, analyze_document, rag_answer
        ai_service = 'local'
    except ImportError:
        logger.warning("AI 서비스를 찾을 수 없습니다")


# 글로벌 변수: 사용자별 최근 문서 저장
recent_documents: Dict[int, List[Dict[str, Any]]] = {}


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """start 명령어 핸들러"""
    user_name = update.effective_user.first_name or "User"
    await update.message.reply_text(
        f"👋 안녕하세요 {user_name}님!\n\n"
        "125 Build Automation Bot에 오신 것을 환영합니다.\n\n"
        "🤖 **주요 기능:**\n"
        "• 문서 업로드 및 AI 분석\n"
        "• 문서 요약 (/summarize)\n"
        "• 문서 상세 분석 (/analyze)\n"
        "• RAG 기반 질문 (/ask)\n"
        "• 문서 목록 (/list)\n\n"
        "문서를 업로드하거나 '/help'를 입력해보세요!"
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말 명령어 핸들러"""
    help_text = """
🤖 **125 Build Automation Bot 도움말**

**📄 문서 처리:**
1. 문서 업로드 → 자동 저장
2. 다음 명령어 사용:

**명령어:**
• `/summarize` - 최근 문서 요약
• `/analyze` - 최근 문서 상세 분석
• `/ask [질문]` - RAG 기반 질문 (RAG 활성화 시)
• `/list` - 저장된 문서 목록
• `/health` - 서비스 상태 확인
• `/help` - 이 도움말

**지원 형식:**
• 텍스트 파일 (.txt, .log, .md)
• 마크다운 (.md)
• CSV (.csv)
• JSON (.json)
• 기타 텍스트 기반 파일

💡 **팁:** 여러 문서를 업로드하면 최근 5개까지 저장됩니다.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """서비스 상태 확인"""
    if ai_service:
        try:
            if ai_service == 'backend':
                from backend.services.ai_service import health_check
            else:
                from services.ai_service import health_check

            status = health_check()

            status_text = "🔍 **서비스 상태**\n\n"
            status_text += f"• Gemini AI: {'✅ 활성화' if status.get('gemini_ai') else '❌ 비활성화'}\n"
            status_text += f"• RAG 시스템: {'✅ 활성화' if status.get('rag_enabled') else '❌ 비활성화'}\n"
            status_text += f"• RAG 초기화: {'✅ 완료' if status.get('rag_initialized') else '❌ 미완료'}\n"

            await update.message.reply_text(status_text, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ 상태 확인 실패: {str(e)}")
    else:
        await update.message.reply_text("❌ AI 서비스를 사용할 수 없습니다")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 핸들러"""
    try:
        document = update.message.document
        if not document:
            return

        file_name = document.file_name
        mime_type = document.mime_type or ""
        user_id = update.effective_user.id

        # 지원 형식 확인
        supported_extensions = ['.txt', '.log', '.md', '.csv', '.json', '.xml']
        file_ext = os.path.splitext(file_name)[1].lower()

        if file_ext not in supported_extensions and not mime_type.startswith('text/'):
            await update.message.reply_text(
                f"❌ 지원하지 않는 파일 형식입니다: {file_ext}\n"
                "지원 형식: .txt, .log, .md, .csv, .json, .xml"
            )
            return

        # 파일 다운로드
        file = await context.bot.get_file(document.file_id)
        file_path = f"/tmp/{document.file_id}_{file_name}"

        await file.download_to_drive(file_path)

        # 텍스트 추출
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            # 인코딩 감지
            import chardet
            detected = chardet.detect(content)
            encoding = detected.get('encoding', 'utf-8')
            text = content.decode(encoding, errors='ignore')
        except Exception as e:
            await update.message.reply_text(f"❌ 파일 읽기 실패: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return

        # 사용자별 최근 문서 저장
        if user_id not in recent_documents:
            recent_documents[user_id] = []

        doc_info = {
            'file_name': file_name,
            'file_path': file_path,
            'text': text,
            'text_length': len(text),
            'timestamp': datetime.now()
        }

        recent_documents[user_id].append(doc_info)

        # 최대 5개까지만 저장
        if len(recent_documents[user_id]) > 5:
            old_doc = recent_documents[user_id].pop(0)
            if os.path.exists(old_doc['file_path']):
                os.remove(old_doc['file_path'])

        await update.message.reply_text(
            f"📎 **문서 저장 완료**\n\n"
            f"**파일명:** {file_name}\n"
            f"**크기:** {len(text)}자\n\n"
            f"분석을 원하시면 다음 명령어를 사용하세요:\n"
            f"• `/summarize` - 문서 요약\n"
            f"• `/analyze` - 문서 분석\n"
            f"• `/ask [질문]` - 질문하기",
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"문서 처리 실패: {e}")
        await update.message.reply_text("❌ 문서 처리 중 오류가 발생했습니다")


async def handle_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 요약 핸들러"""
    user_id = update.effective_user.id

    if user_id not in recent_documents or not recent_documents[user_id]:
        await update.message.reply_text("❌ 최근에 업로드한 문서가 없습니다. 먼저 문서를 업로드해주세요.")
        return

    if not ai_service:
        await update.message.reply_text("❌ AI 서비스를 사용할 수 없습니다")
        return

    try:
        latest_doc = recent_documents[user_id][-1]

        await update.message.reply_text("📝 문서를 요약하고 있습니다...")

        summary = summarize_text(latest_doc['text'], latest_doc['file_name'])

        response_msg = f"📄 **문서 요약 결과**\n\n**파일:** {latest_doc['file_name']}\n\n{summary}"

        if len(response_msg) > 4000:
            response_msg = response_msg[:3997] + "..."

        await update.message.reply_text(response_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"문서 요약 실패: {e}")
        await update.message.reply_text(f"❌ 문서 요약 중 오류가 발생했습니다: {str(e)}")


async def handle_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 분석 핸들러"""
    user_id = update.effective_user.id

    if user_id not in recent_documents or not recent_documents[user_id]:
        await update.message.reply_text("❌ 최근에 업로드한 문서가 없습니다. 먼저 문서를 업로드해주세요.")
        return

    if not ai_service:
        await update.message.reply_text("❌ AI 서비스를 사용할 수 없습니다")
        return

    try:
        latest_doc = recent_documents[user_id][-1]

        await update.message.reply_text("🔍 문서를 분석하고 있습니다...")

        analysis = analyze_document(latest_doc['text'], latest_doc['file_name'])

        response_msg = f"📊 **문서 분석 결과**\n\n**파일:** {latest_doc['file_name']}\n\n{analysis}"

        if len(response_msg) > 4000:
            response_msg = response_msg[:3997] + "..."

        await update.message.reply_text(response_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"문서 분석 실패: {e}")
        await update.message.reply_text(f"❌ 문서 분석 중 오류가 발생했습니다: {str(e)}")


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 목록 핸들러"""
    user_id = update.effective_user.id

    if user_id not in recent_documents or not recent_documents[user_id]:
        await update.message.reply_text("📂 저장된 문서가 없습니다.")
        return

    try:
        doc_list = []
        for i, doc in enumerate(recent_documents[user_id], 1):
            timestamp = doc['timestamp'].strftime('%H:%M:%S')
            doc_list.append(f"{i}. {doc['file_name']} ({doc['text_length']}자) - {timestamp}")

        response = "📂 **저장된 문서 목록**\n\n" + "\n".join(doc_list)
        response += f"\n\n총 {len(recent_documents[user_id])}개 문서가 저장되어 있습니다."

        await update.message.reply_text(response, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {e}")
        await update.message.reply_text("❌ 문서 목록 조회 중 오류가 발생했습니다")


async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """RAG 질문 핸들러"""
    if not ai_service:
        await update.message.reply_text("❌ AI 서비스를 사용할 수 없습니다")
        return

    try:
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("❌ 질문을 입력해주세요: /ask [질문]")
            return

        user_id = str(update.effective_user.id)

        answer = rag_answer(query, user_id)

        response_msg = f"🤖 **질문:** {query}\n\n**답변:**\n{answer}"

        if len(response_msg) > 4000:
            response_msg = response_msg[:3997] + "..."

        await update.message.reply_text(response_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"질문 처리 실패: {e}")
        await update.message.reply_text(f"❌ 질문 처리 중 오류가 발생했습니다: {str(e)}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """텍스트 메시지 핸들러"""
    text = (update.message.text or "").strip()

    # 명령어는 별도 핸들러에서 처리
    if text.startswith('/'):
        return

    # 기본 응답
    await update.message.reply_text(
        "🤖 문서 분석 봇입니다!\n\n"
        "📎 문서를 업로드하거나 '/help'를 입력해보세요."
    )


async def main():
    """메인 실행 함수"""
    print("=== 125 Build Automation Telegram Bot ===")
    print(f"Env file: {env_file_path}")
    print(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not Found'}")
    print(f"GEMINI_API_KEY: {'Set' if GEMINI_API_KEY else 'Not Found'}")
    print(f"AI Service: {'Available' if ai_service else 'Not Available'}")
    print("===========================================")

    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN이 설정되지 않았습니다!")
        return

    # 텔레그램 애플리케이션 생성
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 핸들러 등록
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("health", handle_health))
    application.add_handler(CommandHandler("summarize", handle_summarize))
    application.add_handler(CommandHandler("analyze", handle_analyze))
    application.add_handler(CommandHandler("list", handle_list))
    application.add_handler(CommandHandler("ask", handle_ask))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("OK: Bot handlers registered")
    print("OK: Starting bot polling...")
    print("SUCCESS: Bot is running... Press Ctrl+C to stop")

    try:
        # 봇 실행
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\nINFO: Bot stopped by user")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await application.shutdown()
        print("INFO: Bot shutdown complete")


if __name__ == "__main__":
    try:
        # 이벤트 루프 생성 및 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(main())
        except KeyboardInterrupt:
            print("\nINFO: Interrupted by user")
        except Exception as e:
            print(f"FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            # 정리
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            if pending:
                try:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                except Exception:
                    pass

            loop.close()

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)
