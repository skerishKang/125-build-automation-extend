#!/usr/bin/env python3
"""
125 Build Automation - Telegram Bot Runner (Unified)
- 단일 파일로 텍스트/문서/이미지/음성 모두 처리
- 자유 대화는 Gemini 사용, 최근 대화는 Supabase에 저장 (선택)
- 문서/이미지/음성은 즉시 Gemini로 전달
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
MINIMAX_API_TOKEN = os.getenv("MINIMAX_API_TOKEN")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
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

# telegram
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
except ImportError:
    logger.error("python-telegram-bot이 설치되지 않았습니다. pip install python-telegram-bot==21.6")
    sys.exit(1)

# minimax
text_model = None
if MINIMAX_API_TOKEN:
    try:
        import httpx
        import json
        text_model = "minimax"  # Use 'minimax' flag to indicate MiniMax API
        logger.info("Using MiniMax API (MiniMax-M2)")
    except Exception as e:
        logger.error(f"MiniMax setup failed: {e}")
else:
    logger.warning("MINIMAX_API_TOKEN not set; chat will be disabled")

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
    # telegram 409 방지: 409 발생 시 재시도 약간 대기
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
        "이 봇은 \"올인원\"입니다.\n"
        "- 자유 대화 (메모리 포함)\n"
        "- 문서/이미지/음성 업로드 즉시 처리\n\n"
        "그냥 메시지를 보내거나 파일을 올려보세요.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text or text.startswith('/'):
        return

    if not MINIMAX_API_TOKEN:
        await reply_text(update, "MiniMax 설정이 없어 대화가 비활성화되어 있어요.")
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    # 메모리 불러와 컨텍스트 구성
    memory = await fetch_memory(user_id)
    context_lines = []
    if memory:
        context_lines.append("[이전 대화 맥락]")
        for m in memory:
            context_lines.append(f"User: {m['message']}")
            context_lines.append(f"Assistant: {m['response']}")
        context_lines.append("")
    prompt = "\n".join(context_lines + [f"현재 사용자 메시지: {text}"])

    try:
        # MiniMax API 호출 (Anthropic 호환)
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "x-api-key": MINIMAX_API_TOKEN,
                "content-type": "application/json"
            }
            data = {
                "model": "minimax-m2",
                "max_tokens": 2048,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"MiniMax response: {result}")  # 디버깅용 로깅
            # Anthropic 호환 응답 형식
            content = result.get("content", [])
            if content and isinstance(content, list):
                answer = content[0].get("text", "(응답이 비어있어요)")
            else:
                answer = str(result)  # 전체 응답을 문자열로
    except Exception as e:
        logger.error(f"MiniMax error: {e}")
        answer = "죄송해요, 지금은 답변을 생성할 수 없어요."

    await reply_text(update, answer)
    await save_memory(user_id, username, text, answer)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return
    file = await context.bot.get_file(doc.file_id)
    tmp = os.path.join(tempfile.gettempdir(), f"{doc.file_id}_{doc.file_name}")
    await file.download_to_drive(tmp)

    # 텍스트 파일만 우선 처리 (간단화)
    try:
        content = open(tmp, 'rb').read()
        import chardet
        enc = chardet.detect(content).get('encoding') or 'utf-8'
        text = content.decode(enc, errors='ignore')
    except Exception as e:
        await reply_text(update, f"파일 읽기 실패: {e}")
        return
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

    if not MINIMAX_API_TOKEN:
        await reply_text(update, "MiniMax 설정이 없어 파일 분석이 비활성화되어 있어요.")
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    try:
        # MiniMax API 호출 (Anthropic 호환)
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "x-api-key": MINIMAX_API_TOKEN,
                "content-type": "application/json"
            }
            prompt = f"다음 문서를 요약/분석해줘. 파일명: {doc.file_name}\n\n{text}"
            data = {
                "model": "minimax-m2",
                "max_tokens": 2048,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("content", [{}])[0].get("text", "(응답이 비어있어요)")
    except Exception as e:
        logger.error(f"MiniMax doc error: {e}")
        answer = "문서 분석 중 오류가 발생했어요."

    await reply_text(update, f"📄 {doc.file_name} 분석 결과:\n\n{answer}")
    recent_documents.setdefault(int(user_id), []).append({
        "file_name": doc.file_name,
        "text_length": len(text),
        "timestamp": datetime.utcnow()
    })
    await save_memory(user_id, username, f"[문서] {doc.file_name}", answer)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MINIMAX_API_TOKEN:
        await reply_text(update, "MiniMax 설정이 없어 이미지 분석이 비활성화되어 있어요.")
        return
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        tmp = os.path.join(tempfile.gettempdir(), f"{photo.file_id}.jpg")
        await file.download_to_drive(tmp)
        # 이미지는 텍스트 요청 (멀티모달 미사용 환경)
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "x-api-key": MINIMAX_API_TOKEN,
                "content-type": "application/json"
            }
            data = {
                "model": "minimax-m2",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": "이미지를 설명하는 캡션을 만들어줘. (이미지의 주요 내용, 톤, 색감, 맥락 추정)"
                    }
                ]
            }
            response = await client.post(
                f"{MINIMAX_BASE_URL}/v1/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("content", [{}])[0].get("text", "이미지 설명 생성 실패")
        await reply_text(update, f"🖼️ 이미지 설명:\n{answer}")
    except Exception as e:
        logger.error(f"photo error: {e}")
        await reply_text(update, "이미지 처리에 실패했어요.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MINIMAX_API_TOKEN:
        await reply_text(update, "MiniMax 설정이 없어 음성 처리가 비활성화되어 있어요.")
        return
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        ogg_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.ogg")
        wav_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.wav")
        await file.download_to_drive(ogg_path)

        # ogg to wav 변환 (ffmpeg 필요)
        try:
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", wav_path],
                          check=True, capture_output=True)
        except Exception as e:
            await reply_text(update, f"오디오 변환 실패: {e}. ffmpeg가 설치되어 있는지 확인하세요.")
            return

        # Whisper로 전사
        try:
            from faster_whisper import WhisperModel
            # base 모델 사용 (빠르고 정확)
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(wav_path, language="ko")
            transcription = " ".join([segment.text for segment in segments]).strip()

            if not transcription:
                await reply_text(update, "음성에서 텍스트를 인식하지 못했어요. 다시 시도해주세요.")
                return

            # MiniMax로 요약/답변 생성
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "x-api-key": MINIMAX_API_TOKEN,
                    "content-type": "application/json"
                }
                prompt = f"다음 음성 메시지가 전사된 텍스트입니다. 적절히 요약하거나 답변해 주세요:\n\n{transcription}"
                data = {
                    "model": "minimax-m2",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                response = await client.post(
                    f"{MINIMAX_BASE_URL}/v1/messages",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("content", [])
                if content and isinstance(content, list):
                    answer = content[0].get("text", "처리 실패")
                else:
                    answer = "처리 실패"

            await reply_text(update, f"🎤 **전사된 텍스트:**\n{transcription}\n\n📝 **처리 결과:**\n{answer}")
        except ImportError:
            await reply_text(update, "faster-whisper가 설치되어 있지 않아요. `pip install faster-whisper`로 설치해주세요.")
        except Exception as e:
            logger.error(f"Whisper error: {e}")
            await reply_text(update, f"음성 전사 중 오류가 발생했어요: {str(e)[:100]}")
        finally:
            # 임시 파일 삭제
            try:
                os.remove(ogg_path)
                os.remove(wav_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"voice error: {e}")
        await reply_text(update, "음성 처리에 실패했어요.")


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    docs = recent_documents.get(user_id, [])[-5:]
    if not docs:
        await reply_text(update, "저장된 최근 문서가 없어요.")
        return
    lines = [f"{i+1}. {d['file_name']} ({d['text_length']}자)" for i, d in enumerate(docs)]
    await reply_text(update, "최근 문서 목록:\n" + "\n".join(lines))


def main():
    print("=== 125 Unified Telegram Bot ===")
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
