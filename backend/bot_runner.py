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
import asyncio

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
    from telegram.constants import ChatAction
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

# Smart audio processing configuration
SHORT_AUDIO_THRESHOLD = int(os.getenv("SHORT_AUDIO_THRESHOLD", "30"))  # 30초 이하
LONG_AUDIO_THRESHOLD = int(os.getenv("LONG_AUDIO_THRESHOLD", "300"))  # 5분 이상
MID_LENGTH_MODEL = os.getenv("MID_LENGTH_AUDIO", "gemini")  # 30초-5분 기본


def get_audio_duration(ogg_path: str) -> float:
    """Get audio duration in seconds using ffprobe (if available) or estimate"""
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", ogg_path],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except Exception:
        # Fallback: estimate based on file size (rough)
        # ~1MB per minute at 64kbps
        size_mb = os.path.getsize(ogg_path) / (1024 * 1024)
        return size_mb * 60 * 0.7  # conservative estimate


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


# Thread pool for CPU-intensive operations (transcription, etc.)
from concurrent.futures import ThreadPoolExecutor
audio_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audio_processing")


async def _action_indicator(context: ContextTypes.DEFAULT_TYPE, chat_id: int, action: str, stop_event: asyncio.Event):
    try:
        while not stop_event.is_set():
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action=action)
            except Exception:
                pass
            # Telegram은 5초 동안 액션 유지. 4초 주기로 새로 송신.
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                continue
    except Exception:
        pass

class ActionIndicator:
    def __init__(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, action: str):
        self.context = context
        self.chat_id = chat_id
        self.action = action
        self.stop_event = asyncio.Event()
        self.task: asyncio.Task | None = None

    async def __aenter__(self):
        self.task = asyncio.create_task(_action_indicator(self.context, self.chat_id, self.action, self.stop_event))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.stop_event.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=1.5)
            except Exception:
                self.task.cancel()


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

    # 1) 즉시 수신 확인 + 액션 인디케이터 + 진행률 업데이트 루프 시작
    ack_msg = None
    try:
        ack_msg = await update.message.reply_text("💬 답변 생성 중… [0%]")
    except Exception:
        ack_msg = None

    indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.TYPING)
    await indicator.__aenter__()

    progress_stop = asyncio.Event()

    async def progress_updater():
        if not ack_msg:
            return
        pct = 0
        try:
            while not progress_stop.is_set():
                pct = min(90, pct + 10)
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=ack_msg.message_id,
                        text=f"💬 답변 생성 중… [{pct}%]"
                    )
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(progress_stop.wait(), timeout=1.6)
                except asyncio.TimeoutError:
                    continue
        except Exception:
            pass

    progress_task = asyncio.create_task(progress_updater())

    try:
        # 2) 블로킹 추론을 스레드로 오프로딩하여 동시 메시지 처리 유지
        def _call_gemini():
            resp = gemini_model.generate_content(prompt)
            return resp.text.strip()
        raw = await asyncio.to_thread(_call_gemini)
        answer = format_plain(raw)
        logger.info(f"Bot replied ({len(answer)} chars): {answer[:100]}...")
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        answer = "죄송해요, 지금은 답변을 생성할 수 없어요."
    finally:
        # 3) 진행 루프 종료
        progress_stop.set()
        try:
            await asyncio.wait_for(progress_task, timeout=1.0)
        except Exception:
            progress_task.cancel()
        await indicator.__aexit__(None, None, None)

    # 4) 최종 100%로 교체 또는 새 메시지 전송
    if ack_msg:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=ack_msg.message_id,
                text=f"✅ 답변 [100%]:\n{answer}"
            )
        except Exception:
            await reply_text(update, answer)
    else:
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
    # 업로드 액션 인디케이터 시작
    doc_indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
    await doc_indicator.__aenter__()
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
        await doc_indicator.__aexit__(None, None, None)
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    try:
        prompt = f"다음 문서를 요약/분석해줘. 파일명: {doc.file_name}\n\n{text}"
        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

        # Gemini call
        # 블로킹 추론 오프로딩
        def _call_gemini_doc():
            resp = gemini_model.generate_content(prompt)
            return resp.text.strip()
        answer = await asyncio.to_thread(_call_gemini_doc)
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
    await doc_indicator.__aexit__(None, None, None)


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
        photo_indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        await photo_indicator.__aenter__()
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
        try:
            if 'photo_indicator' in locals():
                await photo_indicator.__aexit__(None, None, None)
        except Exception:
            pass


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 음성 처리가 비활성화되어 있어요.")
        return

    # Immediate acknowledgment + background processing message
    ack_msg = None
    try:
        ack_msg = await update.message.reply_text(
            "🎤 음성을 받았어요. 백그라운드에서 처리 중입니다! "
            "다른 메시지도 바로 보낼 수 있어요. 😊"
        )
    except Exception:
        ack_msg = None

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    # Create background task for voice processing (non-blocking)
    asyncio.create_task(process_voice_background(update, context, chat_id, user_id, username, ack_msg))


async def process_voice_background(update, context, chat_id, user_id, username, ack_msg):
    """Process voice in background - non-blocking, allows immediate responses"""
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.ogg")
    wav_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.wav")

    try:
        # Download voice file
        await file.download_to_drive(ogg_path)

        # Get audio duration
        duration = get_audio_duration(ogg_path)

        # Select model based on duration
        if duration <= SHORT_AUDIO_THRESHOLD:
            # SHORT: Use Gemini 2.5 Flash (multimodal, fast)
            result = await process_with_gemini_multimodal(ogg_path, duration, chat_id, context, ack_msg)
            mode = "Gemini 2.5 Flash (멀티모달)"
        elif duration >= LONG_AUDIO_THRESHOLD:
            # LONG: Use Whisper + Gemini (accurate, free)
            result = await process_with_whisper_gemini(ogg_path, wav_path, duration, chat_id, context, ack_msg)
            mode = "Whisper + Gemini (정확도 최적화)"
        else:
            # MID: Use environment setting
            if MID_LENGTH_MODEL == "gemini":
                result = await process_with_gemini_multimodal(ogg_path, duration, chat_id, context, ack_msg)
                mode = "Gemini 2.5 Flash (멀티모달)"
            else:
                result = await process_with_whisper_gemini(ogg_path, wav_path, duration, chat_id, context, ack_msg)
                mode = "Whisper + Gemini (정확도 최적화)"

        # Send result
        if result:
            final_text = f"🎤 {mode} 처리 결과 ({duration:.1f}초):\n\n{result}"
            if ack_msg:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id, message_id=ack_msg.message_id, text=final_text
                    )
                except Exception:
                    await context.bot.send_message(chat_id, final_text)
            else:
                await context.bot.send_message(chat_id, final_text)

            # Save to memory
            await save_memory(user_id, username, f"[음성] {duration:.1f}초", result)

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        error_msg = f"음성 처리 중 오류가 발생했어요: {str(e)[:100]}"
        if ack_msg:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=ack_msg.message_id, text=error_msg
                )
            except Exception:
                await context.bot.send_message(chat_id, error_msg)
        else:
            await context.bot.send_message(chat_id, error_msg)
    finally:
        # Clean up
        try:
            for path in [ogg_path, wav_path]:
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass


async def process_with_gemini_multimodal(ogg_path: str, duration: float, chat_id: int, context, ack_msg):
    """Process short audio with Gemini 2.5 Flash multimodal"""
    # Update status
    if ack_msg:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=ack_msg.message_id,
                text=f"🎤 {duration:.1f}초 (짧음) - Gemini 2.5 Flash 멀티모달 분석 중..."
            )
        except Exception:
            pass

    # Upload audio directly to Gemini
    import google.generativeai as genai
    audio_data = open(ogg_path, "rb").read()
    audio_part = {"mime_type": "audio/ogg", "data": audio_data}

    prompt = (
        "이 음성 메시지를 한국어로 전사하고 적절히 요약/답변해주세요.\n"
        "음성 내용에 직접 답할 수 있는 질문이면 답변도 제공해주세요.\n"
        "항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."
    )

    # Call Gemini in thread pool
    def _call_gemini():
        response = gemini_model.generate_content([prompt, audio_part])
        return response.text.strip()

    result = await asyncio.to_thread(_call_gemini)
    return format_plain(result)


async def process_with_whisper_gemini(ogg_path: str, wav_path: str, duration: float, chat_id: int, context, ack_msg):
    """Process long audio with Whisper + Gemini"""
    # Update status
    if ack_msg:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=ack_msg.message_id,
                text=f"🎤 {duration:.1f}초 (김음) - Whisper로 전사 중..."
            )
        except Exception:
            pass

    # Convert ogg to wav (async)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _stdout, _stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg 변환 실패")
    except Exception as e:
        raise Exception(f"오디오 변환 실패: {str(e)}")

    # Update status
    if ack_msg:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=ack_msg.message_id,
                text=f"🎤 전사 완료! Gemini로 요약 중..."
            )
        except Exception:
            pass

    # Whisper transcription (in thread pool)
    try:
        from faster_whisper import WhisperModel
        if not hasattr(process_with_whisper_gemini, "_whisper"):
            process_with_whisper_gemini._whisper = WhisperModel("base", device="cpu", compute_type="int8")
        wmodel = process_with_whisper_gemini._whisper

        def _transcribe():
            segs, _info = wmodel.transcribe(wav_path, language="ko", vad_filter=True)
            return " ".join([s.text.strip() for s in segs if s.text]).strip()

        transcription = await asyncio.to_thread(_transcribe)

        if not transcription:
            return "음성에서 텍스트를 인식하지 못했어요."

        # Gemini summary (in thread pool)
        def _summarize():
            prompt = (
                f"다음 음성 메시지가 전사된 텍스트입니다. 적절히 요약하거나 답변해 주세요:\n\n{transcription}\n\n"
                "항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."
            )
            response = gemini_model.generate_content(prompt)
            return response.text.strip()

        result = await asyncio.to_thread(_summarize)
        return format_plain(result)

    except ImportError:
        return "faster-whisper가 설치되어 있지 않아요. 백엔드 관리자에게 문의해주세요."



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
