"""Voice and photo handlers extracted from the runtime module."""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from telegram import Update
    from telegram.ext import ContextTypes


async def handle_photo(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle incoming photos with Gemini multimodal analysis."""
    GEMINI_API_KEY = runtime.GEMINI_API_KEY
    gemini_model = runtime.gemini_model
    ActionIndicator = runtime.ActionIndicator
    ChatAction = runtime.ChatAction
    format_plain = runtime.format_plain
    reply_text = runtime.reply_text
    logger = runtime.logger

    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 이미지 분석이 비활성화되어 있어요.")
        return

    progress_messages: List = []
    progress_messages.append(await update.message.reply_text("📷 이미지를 받았어요. 분석 중… [0%]"))

    tmp: Optional[str] = None
    photo_indicator: Optional[ActionIndicator] = None

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        tmp = os.path.join(tempfile.gettempdir(), f"{photo.file_id}.jpg")
        photo_indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        await photo_indicator.__aenter__()
        await file.download_to_drive(tmp)

        progress_messages.append(await update.message.reply_text("📷 이미지 다운로드 완료. 멀티모달 분석 중… [50%]"))

        import google.generativeai as genai  # noqa: WPS433

        with open(tmp, "rb") as image_fp:
            image_part = {"mime_type": "image/jpeg", "data": image_fp.read()}

        prompt = (
            "다음 이미지를 한국어로 설명하는 캡션을 작성해줘. 이미지의 주요 내용, 색감/분위기, 맥락을 간결하게 설명해주세요.\n\n"
            "항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."
        )

        response = gemini_model.generate_content([prompt, image_part])
        answer = format_plain(response.text.strip())

        progress_messages.append(await update.message.reply_text("✅ 이미지 분석 완료! [100%]"))

        final_text = f"🖼️ 이미지 설명:\n{answer}"
        await reply_text(update, final_text)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("photo error: %s", exc)
        await reply_text(update, "이미지 처리에 실패했어요.")
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:  # pragma: no cover - cleanup best effort
                pass
        if photo_indicator:
            try:
                await photo_indicator.__aexit__(None, None, None)
            except Exception:  # pragma: no cover - cleanup best effort
                pass


async def handle_voice(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle incoming voice messages with adaptive processing."""
    GEMINI_API_KEY = runtime.GEMINI_API_KEY
    gemini_model = runtime.gemini_model
    reply_text = runtime.reply_text

    if not GEMINI_API_KEY or not gemini_model:
        await reply_text(update, "Gemini 설정이 없어 음성 처리가 비활성화되어 있어요.")
        return

    ack_msg = None
    try:
        ack_msg = await update.message.reply_text(
            "🎤 음성을 받았어요. 백그라운드에서 처리 중입니다! "
            "다른 메시지도 바로 보낼 수 있어요. 😊"
        )
    except Exception:  # pragma: no cover - best effort ack
        ack_msg = None

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    asyncio.create_task(
        process_voice_background(runtime, update, context, chat_id, user_id, username, ack_msg)
    )


async def process_voice_background(
    runtime: Any,
    update,
    context,
    chat_id: int,
    user_id: str,
    username: str,
    ack_msg,
) -> None:
    """Process voice in background - non-blocking, allows immediate responses."""
    logger = runtime.logger
    get_audio_duration = runtime.get_audio_duration
    SHORT_AUDIO_THRESHOLD = runtime.SHORT_AUDIO_THRESHOLD
    LONG_AUDIO_THRESHOLD = runtime.LONG_AUDIO_THRESHOLD
    MID_LENGTH_MODEL = runtime.MID_LENGTH_MODEL
    save_memory = runtime.save_memory

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.ogg")
    wav_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.wav")

    progress_messages: List = []

    try:
        await file.download_to_drive(ogg_path)
        progress_messages.append(await context.bot.send_message(chat_id, "📥 음성 파일 다운로드 완료. [20%]"))

        duration = get_audio_duration(ogg_path)
        progress_messages.append(
            await context.bot.send_message(
                chat_id,
                f"⏱️ 음성 길이 분석: {duration:.1f}초. 처리 방식 결정 중... [40%]",
            )
        )

        if duration <= SHORT_AUDIO_THRESHOLD:
            result = await process_with_gemini_multimodal(runtime, ogg_path, duration, chat_id, context, progress_messages)
            mode = "Gemini 2.5 Flash (멀티모달)"
        elif duration >= LONG_AUDIO_THRESHOLD:
            result = await process_with_whisper_gemini(runtime, ogg_path, wav_path, duration, chat_id, context, progress_messages)
            mode = "Whisper + Gemini (정확도 최적화)"
        else:
            if MID_LENGTH_MODEL == "gemini":
                result = await process_with_gemini_multimodal(runtime, ogg_path, duration, chat_id, context, progress_messages)
                mode = "Gemini 2.5 Flash (멀티모달)"
            else:
                result = await process_with_whisper_gemini(runtime, ogg_path, wav_path, duration, chat_id, context, progress_messages)
                mode = "Whisper + Gemini (정확도 최적화)"

        progress_messages.append(await context.bot.send_message(chat_id, "✅ 음성 처리 완료! [100%]"))

        if result:
            final_text = f"🎤 {mode} 처리 결과 ({duration:.1f}초):\n\n{result}"
            await context.bot.send_message(chat_id, final_text)
            await save_memory(user_id, username, f"[음성] {duration:.1f}초", result)

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Voice processing error: %s", exc)
        error_msg = f"음성 처리 중 오류가 발생했어요: {str(exc)[:100]}"
        await context.bot.send_message(chat_id, error_msg)
    finally:
        for path in (ogg_path, wav_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:  # pragma: no cover - cleanup best effort
                pass


async def process_with_gemini_multimodal(
    runtime: Any,
    ogg_path: str,
    duration: float,
    chat_id: int,
    context,
    progress_messages,
) -> str:
    """Process short audio with Gemini 2.5 Flash multimodal."""
    gemini_model = runtime.gemini_model
    format_plain = runtime.format_plain

    progress_messages.append(
        await context.bot.send_message(
            chat_id,
            f"🎤 {duration:.1f}초 (짧음) - Gemini 2.5 Flash 멀티모달 분석 중... [60%]",
        )
    )

    import google.generativeai as genai  # noqa: WPS433

    with open(ogg_path, "rb") as audio_fp:
        audio_part = {"mime_type": "audio/ogg", "data": audio_fp.read()}

    prompt = (
        "이 음성 메시지를 한국어로 전사하고 적절히 요약/답변해주세요.\n"
        "음성 내용에 직접 답할 수 있는 질문이면 답변도 제공해주세요.\n"
        "항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."
    )

    def _call_gemini():
        response = gemini_model.generate_content([prompt, audio_part])
        return response.text.strip()

    result = await asyncio.to_thread(_call_gemini)
    return format_plain(result)


async def process_with_whisper_gemini(
    runtime: Any,
    ogg_path: str,
    wav_path: str,
    duration: float,
    chat_id: int,
    context,
    progress_messages,
) -> str:
    """Process long audio with Whisper + Gemini."""
    gemini_model = runtime.gemini_model
    format_plain = runtime.format_plain

    progress_messages.append(
        await context.bot.send_message(
            chat_id,
            f"🎤 {duration:.1f}초 (김음) - Whisper로 전사 중... [60%]",
        )
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            ogg_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            wav_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, _stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg 변환 실패")
    except Exception as exc:
        raise Exception(f"오디오 변환 실패: {str(exc)}")

    progress_messages.append(await context.bot.send_message(chat_id, "🎤 전사 완료! Gemini로 요약 중... [80%]"))

    try:
        from faster_whisper import WhisperModel  # noqa: WPS433

        if not hasattr(process_with_whisper_gemini, "_whisper"):
            process_with_whisper_gemini._whisper = WhisperModel("base", device="cpu", compute_type="int8")
        whisper_model = process_with_whisper_gemini._whisper

        def _transcribe():
            segments, _info = whisper_model.transcribe(wav_path, language="ko", vad_filter=True)
            return " ".join([segment.text.strip() for segment in segments if segment.text]).strip()

        transcription = await asyncio.to_thread(_transcribe)

        if not transcription:
            return "음성에서 텍스트를 인식하지 못했어요."

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
