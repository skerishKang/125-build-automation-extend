#!/usr/bin/env python3
"""
125 Build Automation - Telegram Bot Runner (Gemini 2.0 Flash Multimodal)
- Single file handling text/document/image/voice with Gemini 2.0 Flash
- Free chat with memory (Supabase optional)
- Document/Image/Voice processed directly with Gemini's multimodal capabilities
"""
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any
import tempfile

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", "bot_runner.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("unified_bot")

# Disable httpx logging to prevent token exposure
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# telegram
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
except ImportError:
    logger.error("python-telegram-bot is not installed. pip install python-telegram-bot==21.6")
    sys.exit(1)

# gemini (multimodal)
gemini_model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("Using Gemini 2.5 Flash (multimodal)")
    except Exception as e:
        logger.error(f"Gemini setup failed: {e}")
else:
    logger.warning("GEMINI_API_KEY not set; chat will be disabled")

# supabase (optional memory)
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.warning(f"Supabase init failed: {e}")

# in-memory recent docs (fallback)
recent_documents: Dict[int, List[Dict[str, Any]]] = {}


def format_plain(text: str, max_len: int = 1200) -> str:
    """Format Gemini response to Telegram-friendly plain text"""
    import re
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove tables
    text = re.sub(r"\|.*\|", "", text)
    # Remove header symbols (keep line breaks)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # List symbols (keep line breaks)
    text = re.sub(r"^\s*[-*•]\s*", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s*", "• ", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = text.replace("**", "").replace("*", "")
    # Remove backticks
    text = text.replace("`", "'")
    # Clean up multiple line breaks (max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing spaces
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # Strip leading/trailing spaces
    text = text.strip()
    # Length limit with ...
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


async def save_memory(user_id: str, username: str, message: str, response: str):
    if not supabase:
        return
    try:
        supabase.table("conversations").insert({
            "user_id": user_id,
            "username": username,
            "message": message,
            "response": response,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        logger.warning(f"save_memory failed: {e}")


async def fetch_memory(user_id: str, limit: int = 8) -> List[Dict[str, str]]:
    if not supabase:
        return []
    try:
        res = supabase.table("conversations").select("message,response,created_at").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return list(reversed(res.data or []))
    except Exception as e:
        logger.warning(f"fetch_memory failed: {e}")
        return []


async def reply_text(update: Update, text: str):
    # Prevent telegram 409: retry with slight delay on 409
    try:
        await update.message.reply_text(text)
    except Exception as e:
        logger.warning(f"reply_text failed: {e}")
        await asyncio.sleep(0.8)
        try:
            await update.message.reply_text(text[:4000])
        except Exception:
            pass


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "사용자"
    await reply_text(update,
        f"안녕하세요 {name}님! 👋\n\n"
        "이 봇은 Gemini 2.5 Flash 기반 \"올인원\"입니다.\n"
        "- 자유 대화 (메모리 포함)\n"
        "- 문서/이미지/음성 멀티모달 처리\n\n"
        "그냥 메시지를 보내거나 파일을 올려보세요.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text or text.startswith('/'):
        return

    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 대화가 비활성화되어 있어요.")
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    # Fetch memory and build context
    memory = await fetch_memory(user_id)
    context_lines = []
    if memory:
        context_lines.append("[이전 대화 맥락]")
        for m in memory:
            context_lines.append(f"User: {m['message']}")
            context_lines.append(f"Assistant: {m['response']}")
        context_lines.append("")

    # Smart keyword detection for response length
    short_keywords = ["요약", "간단히", "짧게", "요약", "간단"]
    long_keywords = ["자세히", "구체적으로", "설명", "상세히", "자세한"]
    is_short_question = any(keyword in text for keyword in short_keywords)
    is_long_question = any(keyword in text for keyword in long_keywords)

    # Smart prompt
    if is_long_question:
        prompt_style = "자세하고 구체적으로 설명해 주세요."
    elif is_short_question:
        prompt_style = "간단히 요약해 주세요."
    else:
        prompt_style = "간단히 요약해 주세요. 더 자세히 필요하면 추가 요청해 주세요."

    prompt = "\n".join(context_lines + [
        f"현재 사용자 메시지: {text}",
        f"답변 스타일: {prompt_style}",
        "항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."
    ])

    try:
        # Gemini 2.0 Flash call
        response = gemini_model.generate_content(prompt)
        answer = response.text.strip()
        answer = format_plain(answer)
        logger.info(f"Bot replied ({len(answer)} chars): {answer[:100]}...")
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        answer = "죄송해요, 지금은 답변을 생성할 수 없어요."

    await reply_text(update, answer)
    await save_memory(user_id, username, text, answer)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    # Immediate acknowledgment to reduce perceived wait time
    ack_msg = None
    try:
        ack_msg = await update.message.reply_text("📥 파일을 받았어요. 분석 중입니다…")
    except Exception:
        ack_msg = None

    file = await context.bot.get_file(doc.file_id)
    tmp = os.path.join(tempfile.gettempdir(), f"{doc.file_id}_{doc.file_name}")
    await file.download_to_drive(tmp)

    # Only handle text files for now (simplified)
    try:
        content = open(tmp, 'rb').read()
        import chardet
        enc = chardet.detect(content).get('encoding') or 'utf-8'
        text = content.decode(enc, errors='ignore')
    except Exception as e:
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text=f"파일 읽기 실패: {e}"
                )
            except Exception:
                pass
        else:
            await reply_text(update, f"파일 읽기 실패: {e}")
        return
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

    if not GEMINI_API_KEY or not gemini_model:
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text="Gemini 설정이 없어 파일 분석이 비활성화되어 있어요."
                )
            except Exception:
                pass
        else:
            await reply_text(update, "Gemini 설정이 없어 파일 분석이 비활성화되어 있어요.")
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    try:
        prompt = f"다음 문서를 요약/분석해줘. 파일명: {doc.file_name}\n\n{text}"
        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

        # Gemini call
        response = gemini_model.generate_content(prompt)
        answer = response.text.strip()
        answer = format_plain(answer)
    except Exception as e:
        logger.error(f"Gemini doc error: {e}")
        answer = "문서 분석 중 오류가 발생했어요."

    # Update acknowledgment message or send new one
    final_text = f"📄 {doc.file_name} 분석 결과:\n\n{answer}"
    if ack_msg:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=ack_msg.message_id,
                text=final_text
            )
        except Exception:
            await reply_text(update, final_text)
    else:
        await reply_text(update, final_text)

    recent_documents.setdefault(int(user_id), []).append({
        "file_name": doc.file_name,
        "text_length": len(text),
        "timestamp": datetime.utcnow()
    })
    await save_memory(user_id, username, f"[문서] {doc.file_name}", answer)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 이미지 분석이 비활성화되어 있어요.")
        return

    # Immediate acknowledgment
    ack_msg = None
    try:
        ack_msg = await update.message.reply_text("📷 이미지를 받았어요. 분석 중…")
    except Exception:
        ack_msg = None

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        tmp = os.path.join(tempfile.gettempdir(), f"{photo.file_id}.jpg")
        await file.download_to_drive(tmp)

        # Step update: download complete
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text="📷 이미지 다운로드 완료. 멀티모달 분석 중…"
                )
            except Exception:
                pass

        # Use Gemini's multimodal capability - upload image directly
        import google.generativeai as genai
        image_part = {"mime_type": "image/jpeg", "data": open(tmp, "rb").read()}

        prompt = "다음 이미지를 한국어로 설명하는 캡션을 작성해줘. 이미지의 주요 내용, 색감/분위기, 맥락을 간결하게 설명해주세요."
        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

        # Multimodal call with image
        response = gemini_model.generate_content([prompt, image_part])
        answer = response.text.strip()
        answer = format_plain(answer)

        final_text = f"🖼️ 이미지 설명:\n{answer}"
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text=final_text
                )
            except Exception:
                await reply_text(update, final_text)
        else:
            await reply_text(update, final_text)
    except Exception as e:
        logger.error(f"photo error: {e}")
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text="이미지 처리에 실패했어요."
                )
            except Exception:
                await reply_text(update, "이미지 처리에 실패했어요.")
        else:
            await reply_text(update, "이미지 처리에 실패했어요.")
    finally:
        # Clean up temp file
        try:
            if 'tmp' in locals():
                os.remove(tmp)
        except Exception:
            pass


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 음성 처리가 비활성화되어 있어요.")
        return

    # Immediate acknowledgment
    ack_msg = None
    try:
        ack_msg = await update.message.reply_text("🎤 음성을 받았어요. 멀티모달 분석 중…")
    except Exception:
        ack_msg = None

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        tmp = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.ogg")
        await file.download_to_drive(tmp)

        # Gemini's multimodal can handle audio directly
        import google.generativeai as genai
        audio_part = {"mime_type": "audio/ogg", "data": open(tmp, "rb").read()}

        prompt = "이 음성 메시지가 전사된 텍스트와 적절한 요약/답변을 한국어로 제공해주세요."
        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

        # Multimodal call with audio
        response = gemini_model.generate_content([prompt, audio_part])
        answer = response.text.strip()
        answer = format_plain(answer)

        final_text = f"🎤 음성 분석 결과:\n{answer}"
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text=final_text
                )
            except Exception:
                await reply_text(update, final_text)
        else:
            await reply_text(update, final_text)
    except Exception as e:
        logger.error(f"voice error: {e}")
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=ack_msg.message_id,
                    text="음성 처리에 실패했어요."
                )
            except Exception:
                await reply_text(update, "음성 처리에 실패했어요.")
        else:
            await reply_text(update, "음성 처리에 실패했어요.")
    finally:
        # Clean up temp file
        try:
            if 'tmp' in locals():
                os.remove(tmp)
        except Exception:
            pass


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    docs = recent_documents.get(user_id, [])[-5:]
    if not docs:
        await reply_text(update, "저장된 최근 문서가 없어요.")
        return
    lines = [f"{i+1}. {d['file_name']} ({d['text_length']}자)" for i, d in enumerate(docs)]
    await reply_text(update, "최근 문서 목록:\n" + "\n".join(lines))


def main():
    print("=== 125 Unified Telegram Bot (Gemini 2.5 Flash) ===")
    print(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not Found'}")
    print(f"GEMINI_API_KEY: {'Set' if GEMINI_API_KEY else 'Not Found'}")
    print(f"Supabase: {'Set' if (SUPABASE_URL and SUPABASE_KEY) else 'Not Set'}")

    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("list", handle_list))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Handlers registered. Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
