#!/usr/bin/env python3
"""
125 Build Automation - Telegram Bot Runner (Gemini 2.0 Flash Multimodal)
- Single file handling text/document/image/voice with Gemini 2.0 Flash
- Free chat with memory (Supabase optional)
- Document/Image/Voice processed directly with Gemini's multimodal capabilities
- Google Drive bidirectional sync
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

# Drive monitoring configuration
DRIVE_MONITOR_INTERVAL = int(os.getenv("DRIVE_MONITOR_INTERVAL", "300"))  # 5분 (300초)
ENABLE_DRIVE_MONITORING = os.getenv("ENABLE_DRIVE_MONITORING", "true").lower() == "true"

# Global application instance for Drive monitoring
_app_instance = None


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
    monitoring_status = "🔄 Drive 자동 모니터링" if ENABLE_DRIVE_MONITORING else "📋 Manual Drive 체크"
    await reply_text(update,
        f"안녕하세요 {name}님! 👋\n\n"
        "이 봇은 Gemini 2.5 Flash 기반 \"올인원\"입니다.\n"
        "- 자유 대화 (메모리 포함)\n"
        "- 문서/이미지/음성 멀티모달 처리\n"
        "- Google Drive 양방향 동기화\n"
        f"- {monitoring_status}\n\n"
        "도움말: /drive")


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

    # Cumulative progress messages
    progress_messages = []
    progress_messages.append(await update.message.reply_text("💬 답변 생성 중… [10%]"))

    indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.TYPING)
    await indicator.__aenter__()

    progress_messages.append(await update.message.reply_text("🧠 Gemini 2.5 Flash 분석 중… [50%]"))

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
        await indicator.__aexit__(None, None, None)

    progress_messages.append(await update.message.reply_text("✅ 답변 완성! [100%]"))

    # 4) Send final result as new message
    final_text = f"{answer}"
    await reply_text(update, final_text)

    await save_memory(user_id, username, text, answer)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 이미지 분석이 비활성화되어 있어요.")
        return

    # Cumulative progress messages
    progress_messages = []
    progress_messages.append(await update.message.reply_text("📷 이미지를 받았어요. 분석 중… [0%]"))

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        tmp = os.path.join(tempfile.gettempdir(), f"{photo.file_id}.jpg")
        photo_indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        await photo_indicator.__aenter__()
        await file.download_to_drive(tmp)

        # Step update: download complete
        progress_messages.append(await update.message.reply_text("📷 이미지 다운로드 완료. 멀티모달 분석 중… [50%]"))

        # Use Gemini's multimodal capability - upload image directly
        import google.generativeai as genai
        image_part = {"mime_type": "image/jpeg", "data": open(tmp, "rb").read()}

        prompt = "다음 이미지를 한국어로 설명하는 캡션을 작성해줘. 이미지의 주요 내용, 색감/분위기, 맥락을 간결하게 설명해주세요."
        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

        # Multimodal call with image
        response = gemini_model.generate_content([prompt, image_part])
        answer = response.text.strip()
        answer = format_plain(answer)

        progress_messages.append(await update.message.reply_text("✅ 이미지 분석 완료! [100%]"))

        final_text = f"🖼️ 이미지 설명:\n{answer}"
        await reply_text(update, final_text)
    except Exception as e:
        logger.error(f"photo error: {e}")
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

    # Progress tracking for voice processing
    progress_messages = []

    try:
        # Download voice file
        await file.download_to_drive(ogg_path)
        progress_messages.append(await context.bot.send_message(chat_id, "📥 음성 파일 다운로드 완료. [20%]"))

        # Get audio duration
        duration = get_audio_duration(ogg_path)
        progress_messages.append(await context.bot.send_message(chat_id, f"⏱️ 음성 길이 분석: {duration:.1f}초. 처리 방식 결정 중... [40%]"))

        # Select model based on duration
        if duration <= SHORT_AUDIO_THRESHOLD:
            # SHORT: Use Gemini 2.5 Flash (multimodal, fast)
            result = await process_with_gemini_multimodal(ogg_path, duration, chat_id, context, progress_messages)
            mode = "Gemini 2.5 Flash (멀티모달)"
        elif duration >= LONG_AUDIO_THRESHOLD:
            # LONG: Use Whisper + Gemini (accurate, free)
            result = await process_with_whisper_gemini(ogg_path, wav_path, duration, chat_id, context, progress_messages)
            mode = "Whisper + Gemini (정확도 최적화)"
        else:
            # MID: Use environment setting
            if MID_LENGTH_MODEL == "gemini":
                result = await process_with_gemini_multimodal(ogg_path, duration, chat_id, context, progress_messages)
                mode = "Gemini 2.5 Flash (멀티모달)"
            else:
                result = await process_with_whisper_gemini(ogg_path, wav_path, duration, chat_id, context, progress_messages)
                mode = "Whisper + Gemini (정확도 최적화)"

        progress_messages.append(await context.bot.send_message(chat_id, "✅ 음성 처리 완료! [100%]"))

        # Send result
        if result:
            final_text = f"🎤 {mode} 처리 결과 ({duration:.1f}초):\n\n{result}"
            await context.bot.send_message(chat_id, final_text)

            # Save to memory
            await save_memory(user_id, username, f"[음성] {duration:.1f}초", result)

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        error_msg = f"음성 처리 중 오류가 발생했어요: {str(e)[:100]}"
        await context.bot.send_message(chat_id, error_msg)
    finally:
        # Clean up
        try:
            for path in [ogg_path, wav_path]:
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass


async def process_with_gemini_multimodal(ogg_path: str, duration: float, chat_id: int, context, progress_messages):
    """Process short audio with Gemini 2.5 Flash multimodal"""
    # Send progress update
    progress_messages.append(await context.bot.send_message(chat_id, f"🎤 {duration:.1f}초 (짧음) - Gemini 2.5 Flash 멀티모달 분석 중... [60%]"))

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


async def process_with_whisper_gemini(ogg_path: str, wav_path: str, duration: float, chat_id: int, context, progress_messages):
    """Process long audio with Whisper + Gemini"""
    # Send progress update
    progress_messages.append(await context.bot.send_message(chat_id, f"🎤 {duration:.1f}초 (김음) - Whisper로 전사 중... [60%]"))

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

    # Send progress update
    progress_messages.append(await context.bot.send_message(chat_id, f"🎤 전사 완료! Gemini로 요약 중... [80%]"))

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


# ========== Google Drive Sync Handlers ==========

async def handle_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /drive command - show Google Drive sync help"""
    help_text = (
        "📁 **Google Drive 동기화 가이드**\n\n"
        "**사용 가능한 명령어:**\n"
        "• `/drive` - 이 도움말 보기\n"
        "• `/drivelist` - 드라이브 파일 목록 보기\n"
        "• `/driveget <file_id>` - 드라이브에서 파일 가져오기\n"
        "• `/drivesync` - 새로 올라온 파일 확인\n\n"
        "**자동 동기화:**\n"
        "✓ 텔레그램 파일 자동 드라이브 저장 + Gemini 분석\n\n"
        "**지원 파일 형식:**\n"
        "✓ 텍스트: txt, md, py, js, html, css, json, xml, csv 등\n"
        "✓ Office: pdf, docx, pptx, xlsx\n"
        "✓ 압축: zip (내용 미리보기)\n\n"
        "**예시:**\n"
        "1. `/drivelist` - 전체 파일 목록 보기\n"
        "2. `/driveget 1A2B3C4D` - ID가 1A2B3C4D인 파일 다운로드\n"
        "3. `/drivesync` - 새 파일 체크\n"
        "4. 파일 전송 → 자동 드라이브 저장 + 분석\n"
    )
    await reply_text(update, help_text)


async def handle_drive_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /drivelist command - list all files in Google Drive"""
    progress_messages = []
    progress_messages.append(await update.message.reply_text("📁 드라이브 파일 목록 조회 중... [0%]"))

    try:
        from backend.services.drive_sync import get_folder_files, format_file_list

        progress_messages.append(await update.message.reply_text("📂 드라이브 연결 중... [30%]"))

        files = get_folder_files()

        progress_messages.append(await update.message.reply_text("📋 파일 목록 생성 중... [70%]"))

        result = format_file_list(files)

        progress_messages.append(await update.message.reply_text("✅ 조회 완료! [100%]"))

        await reply_text(update, result)

    except Exception as e:
        logger.error(f"Drive list error: {e}")
        await reply_text(update, f"드라이브 목록 조회 중 오류가 발생했어요: {str(e)[:100]}")


async def handle_drive_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /driveget command - download a file from Google Drive"""
    args = context.args
    if not args:
        await reply_text(update, "사용법: `/driveget <file_id>`\n\n예: `/driveget 1A2B3C4D`")
        return

    file_id = args[0]

    progress_messages = []
    progress_messages.append(await update.message.reply_text(f"📥 드라이브에서 파일 다운로드 중... [0%]"))

    try:
        from backend.services.drive_sync import get_file_info, download_file

        progress_messages.append(await update.message.reply_text("📂 파일 정보 조회 중... [30%]"))

        file_info = get_file_info(file_id)

        if not file_info:
            progress_messages.append(await update.message.reply_text("❌ 파일을 찾을 수 없습니다 [100%]"))
            await reply_text(update, "❌ 파일을 찾을 수 없어요. File ID를 확인해주세요.")
            return

        file_name = file_info['name']
        progress_messages.append(await update.message.reply_text(f"📄 {file_name} 다운로드 중... [60%]"))

        # Download file
        tmp_path = os.path.join(tempfile.gettempdir(), f"drive_download_{file_id}_{file_name}")
        success = download_file(file_id, tmp_path)

        if not success:
            progress_messages.append(await update.message.reply_text("❌ 다운로드 실패 [100%]"))
            await reply_text(update, "❌ 파일 다운로드에 실패했어요.")
            return

        progress_messages.append(await update.message.reply_text("✅ 다운로드 완료! [100%]"))

        # Send file to Telegram
        with open(tmp_path, 'rb') as f:
            from telegram import InputFile
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=InputFile(f, filename=file_name),
                caption=f"📄 **드라이브에서 가져온 파일**: {file_name}"
            )

        # Clean up
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Drive get error: {e}")
        await reply_text(update, f"파일 다운로드 중 오류가 발생했어요: {str(e)[:100]}")


async def handle_drive_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /drivesync command - check for new files in Google Drive"""
    progress_messages = []
    progress_messages.append(await update.message.reply_text("🔍 드라이브 새 파일 확인 중... [0%]"))

    try:
        from backend.services.drive_sync import check_new_files, get_folder_files, check_deleted_files

        progress_messages.append(await update.message.reply_text("📂 드라이브 스캔 중... [50%]"))

        # Get current files and check for new/deleted
        current_files = get_folder_files()
        new_files = check_new_files()
        deleted_files = check_deleted_files(current_files)

        progress_messages.append(await update.message.reply_text("✅ 확인 완료! [100%]"))

        # Format results
        result_lines = []
        has_changes = False

        if new_files:
            has_changes = True
            result_lines.append(f"🆕 **새로 올라온 파일** ({len(new_files)}개):\n")
            for i, file in enumerate(new_files, 1):
                file_type = "📁 폴더" if file.get('mimeType') == 'application/vnd.google-apps.folder' else "📄 파일"
                result_lines.append(f"{i}. {file_type}: **{file['name']}**")
                result_lines.append(f"   ID: `{file['id']}`")
            result_lines.append("")

        if deleted_files:
            has_changes = True
            result_lines.append(f"🗑️ **삭제된 파일** ({len(deleted_files)}개):\n")
            for i, file in enumerate(deleted_files, 1):
                result_lines.append(f"{i}. **{file['name']}**")
                result_lines.append(f"   ID: `{file['id']}`")
            result_lines.append("")

        if not has_changes:
            await reply_text(update, "📭 새 파일이 없습니다.")
        else:
            await reply_text(update, "\n".join(result_lines).strip())

    except Exception as e:
        logger.error(f"Drive sync error: {e}")
        await reply_text(update, f"새 파일 확인 중 오류가 발생했어요: {str(e)[:100]}")


async def monitor_drive_changes():
    """Background task to monitor Google Drive for changes"""
    logger.info("🔍 Drive monitoring worker started")

    while True:
        try:
            if not ENABLE_DRIVE_MONITORING:
                await asyncio.sleep(60)
                continue

            from backend.services.drive_sync import (
                get_folder_files, check_new_files, check_deleted_files,
                cache_current_files, load_cached_files
            )

            # Get current files
            current_files = get_folder_files()

            # Check for deleted files
            deleted_files = check_deleted_files(current_files)

            # Check for new files
            new_files = check_new_files()

            # Broadcast notifications if there are changes
            if (new_files or deleted_files) and _app_instance:
                message_parts = []

                if new_files:
                    message_parts.append(f"🆕 **새로 올라온 파일** ({len(new_files)}개):")
                    for file in new_files[:5]:  # Show max 5 files
                        file_type = "📁 폴더" if file.get('mimeType') == 'application/vnd.google-apps.folder' else "📄"
                        message_parts.append(f"• {file_type}: {file['name']}")
                    if len(new_files) > 5:
                        message_parts.append(f"... 외 {len(new_files) - 5}개")
                    message_parts.append("")

                if deleted_files:
                    message_parts.append(f"🗑️ **삭제된 파일** ({len(deleted_files)}개):")
                    for file in deleted_files[:5]:  # Show max 5 files
                        message_parts.append(f"• {file['name']}")
                    if len(deleted_files) > 5:
                        message_parts.append(f"... 외 {len(deleted_files) - 5}개")
                    message_parts.append("")

                notification_text = "\n".join(message_parts).strip()

                # Get all chat IDs that have interacted with the bot
                # For now, we'll log the changes (implement user tracking if needed)
                logger.info(f"Drive changes detected: {len(new_files)} new, {len(deleted_files)} deleted")

                # TODO: Implement broadcast to specific users
                # This requires tracking which users have enabled Drive notifications

            # Update cache if it's empty (first run)
            if not load_cached_files():
                cache_current_files(current_files)
                logger.info("Initialized Drive file cache")

        except Exception as e:
            logger.error(f"Drive monitoring error: {e}")

        # Wait for next check
        await asyncio.sleep(DRIVE_MONITOR_INTERVAL)

    logger.info("🔍 Drive monitoring worker stopped")


def extract_text_from_file(file_path: str, file_name: str) -> str:
    """
    Extract text from various file formats
    Supports: txt, md, py, js, html, css, json, xml, csv, pdf, docx, pptx, xlsx, zip
    """
    import os
    import zipfile
    import chardet

    file_ext = os.path.splitext(file_name)[1].lower()

    try:
        # 1. Text-based files (most common)
        if file_ext in ['.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.html',
                        '.htm', '.css', '.scss', '.sass', '.less', '.json', '.xml',
                        '.csv', '.tsv', '.yaml', '.yml', '.ini', '.cfg', '.conf',
                        '.log', '.sql', '.sh', '.bat', '.ps1', '.dockerfile',
                        '.gitignore', '.env', '.properties', '.toml', '.r', '.R']:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                enc = chardet.detect(raw_data).get('encoding') or 'utf-8'
                return raw_data.decode(enc, errors='ignore')

        # 2. PDF files
        elif file_ext == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "PDF 읽기를 위한 PyPDF2가 설치되어 있지 않습니다."

        # 3. Word documents (.docx)
        elif file_ext == '.docx':
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                return "DOCX 읽기를 위한 python-docx가 설치되어 있지 않습니다."

        # 4. PowerPoint (.pptx)
        elif file_ext == '.pptx':
            try:
                from pptx import Presentation
                prs = Presentation(file_path)
                text = ""
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text += shape.text + "\n"
                return text
            except ImportError:
                return "PPTX 읽기를 위한 python-pptx가 설치되어 있지 않습니다."

        # 5. Excel files (.xlsx, .xls)
        elif file_ext in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                # Try to read all sheets
                df = pd.read_excel(file_path, sheet_name=None)
                text = ""
                for sheet_name, sheet_df in df.items():
                    text += f"\n=== Sheet: {sheet_name} ===\n"
                    text += sheet_df.to_string(index=False) + "\n"
                return text
            except ImportError:
                return "Excel 읽기를 위한 pandas가 설치되어 있지 않습니다."

        # 6. ZIP archives (extract and read text files inside)
        elif file_ext == '.zip':
            try:
                text = "=== ZIP 아카이브 내용 ===\n"
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    text += f"총 {len(file_list)}개 파일\n\n"
                    for file_in_zip in file_list[:10]:  # Show first 10 files
                        text += f"• {file_in_zip}\n"
                        # If it's a text file, try to extract and read
                        if any(file_in_zip.lower().endswith(ext) for ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']):
                            try:
                                content = zip_ref.read(file_in_zip).decode('utf-8', errors='ignore')
                                text += f"  내용 미리보기:\n{content[:500]}...\n"
                            except:
                                pass
                    if len(file_list) > 10:
                        text += f"\n... 외 {len(file_list) - 10}개 파일"
                return text
            except Exception as e:
                return f"ZIP 파일 읽기 오류: {str(e)}"

        # 7. Other binary files
        else:
            return f"지원하지 않는 파일 형식: {file_ext}\n파일 크기: {os.path.getsize(file_path)} bytes"

    except Exception as e:
        return f"파일 읽기 오류: {str(e)}"


async def handle_document_auto_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-save all documents to Google Drive and analyze with Gemini"""
    doc = update.message.document
    if not doc:
        return

    progress_messages = []
    progress_messages.append(await update.message.reply_text(f"📁 {doc.file_name} Google Drive 자동 저장 중... [0%]"))

    file = await context.bot.get_file(doc.file_id)
    tmp = os.path.join(tempfile.gettempdir(), f"{doc.file_id}_{doc.file_name}")

    doc_indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
    await doc_indicator.__aenter__()
    await file.download_to_drive(tmp)

    progress_messages.append(await update.message.reply_text("📁 파일 다운로드 완료. 드라이브 저장 중... [30%]"))

    try:
        from backend.services.drive_sync import upload_file

        # Upload to Google Drive
        result = upload_file(tmp)

        if result:
            progress_messages.append(await update.message.reply_text("✅ Google Drive 저장 완료! [100%]"))

            file_id = result.get('id', 'N/A')
            web_link = result.get('webViewLink', '')

            # Send confirmation
            confirm_text = (
                f"✅ **{doc.file_name}** Google Drive에 자동 저장되었습니다!\n\n"
                f"📋 파일 ID: `{file_id}`"
            )
            if web_link:
                confirm_text += f"\n🔗 [드라이브에서 보기]({web_link})"

            await reply_text(update, confirm_text)

            # Analyze with Gemini if GEMINI is available
            if GEMINI_API_KEY and gemini_model:
                try:
                    progress_messages.append(await update.message.reply_text("🧠 Gemini 문서 분석 중... [70%]"))

                    # Extract text based on file type
                    extracted_text = extract_text_from_file(tmp, doc.file_name)

                    if extracted_text and len(extracted_text.strip()) > 0:
                        prompt = f"다음 문서를 요약/분석해줘. 파일명: {doc.file_name}\n\n{extracted_text}"
                        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

                        def _call_gemini_doc():
                            resp = gemini_model.generate_content(prompt)
                            return resp.text.strip()

                        answer = await asyncio.to_thread(_call_gemini_doc)
                        answer = format_plain(answer)

                        analysis_text = f"\n\n📄 **문서 분석 결과**:\n\n{answer}"
                        await reply_text(update, analysis_text)
                    else:
                        logger.warning(f"No text extracted from {doc.file_name}")

                except Exception as e:
                    logger.error(f"Document analysis error: {e}")
                    # Don't fail the upload if analysis fails

        else:
            progress_messages.append(await update.message.reply_text("❌ 드라이브 저장 실패 [100%]"))
            await reply_text(update, "❌ Google Drive 저장에 실패했어요. 권한을 확인해주세요.")

    except Exception as e:
        logger.error(f"Auto-save error: {e}")
        await reply_text(update, f"자동 저장 중 오류가 발생했어요: {str(e)[:100]}")
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
        await doc_indicator.__aexit__(None, None, None)


def main():
    print("=== 125 Unified Telegram Bot (Gemini 2.5 Flash + Drive Sync) ===")
    print(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not Found'}")
    print(f"GEMINI_API_KEY: {'Set' if GEMINI_API_KEY else 'Not Found'}")
    print(f"Supabase: {'Set' if (SUPABASE_URL and SUPABASE_KEY) else 'Not Set'}")
    print(f"Google Drive: {'Set' if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'service_account.json')) else 'Not Set'}")
    print(f"Drive Monitoring: {'Enabled' if ENABLE_DRIVE_MONITORING else 'Disabled'} (interval: {DRIVE_MONITOR_INTERVAL}s)")

    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Store app instance for Drive monitoring
    global _app_instance
    _app_instance = app

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("list", handle_list))
    app.add_handler(CommandHandler("drive", handle_drive))
    app.add_handler(CommandHandler("drivelist", handle_drive_list))
    app.add_handler(CommandHandler("driveget", handle_drive_get))
    app.add_handler(CommandHandler("drivesync", handle_drive_sync))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_auto_save))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start Drive monitoring worker
    if ENABLE_DRIVE_MONITORING:
        logger.info("Starting Drive monitoring worker...")
        app.create_task(monitor_drive_changes())

    logger.info("Handlers registered. Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
