"""
Action Handlers - Post-processing hooks for specialized bot results.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import textwrap
from typing import Any, Dict, Tuple, Callable

from telegram import Bot

from backend.services.google_drive import upload_file  # type: ignore

logger = logging.getLogger("action_handlers")

# Load .env file manually
def load_env():
    """Manually load .env file from bots directory"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if os.getenv(key) is None:
                        os.environ[key] = value

# Load env on module import
load_env()

DRIVE_TARGET_FOLDER_ID = os.getenv("DRIVE_SUMMARY_FOLDER_ID") or os.getenv("DOCUMENT_DRIVE_FOLDER_ID")


def _ensure_folder_configured() -> Tuple[bool, str]:
    if not DRIVE_TARGET_FOLDER_ID:
        return False, "⚠️ Drive 폴더 ID가 설정되지 않아 업로드할 수 없어요."
    return True, ""


async def _upload_local_file(local_path: str, file_name: str) -> Tuple[bool, str]:
    ok, message = _ensure_folder_configured()
    if not ok:
        return False, message

    try:
        metadata = await asyncio.to_thread(upload_file, local_path, DRIVE_TARGET_FOLDER_ID, file_name)
        if not metadata:
            return False, "❌ Google Drive 업로드에 실패했습니다. 설정을 확인해주세요."

        web_link = metadata.get("webViewLink") or metadata.get("webContentLink")
        if web_link:
            return True, f"📂 Google Drive 업로드 완료!\n🔗 {web_link}"
        return True, "📂 Google Drive에 업로드 완료했습니다."
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Drive upload failed: %s", exc)
        return False, f"❌ Google Drive 업로드 중 오류가 발생했습니다: {exc}"


async def _download_telegram_file(bot: Bot, file_id: str, suffix: str) -> str:
    telegram_file = await bot.get_file(file_id)
    fd, tmp_path = tempfile.mkstemp(prefix="followup_", suffix=suffix)
    os.close(fd)
    await telegram_file.download_to_drive(tmp_path)
    return tmp_path


def _safe_name(original_name: str, fallback: str) -> str:
    name = (original_name or fallback).strip()
    return name or fallback


async def _handle_document_original(bot: Bot, chat_id: str, record: Dict[str, Any]) -> str:
    meta = record.get("meta", {})
    file_id = meta.get("file_id")
    file_name = _safe_name(meta.get("file_name", ""), "document.pdf")

    if not file_id:
        return "⚠️ 원본 파일 정보를 찾지 못했어요."

    tmp_path = None
    try:
        suffix = os.path.splitext(file_name)[1] or ".bin"
        tmp_path = await _download_telegram_file(bot, file_id, suffix)
        success, message = await _upload_local_file(tmp_path, file_name)
        return message if success else message
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _handle_document_summary(_: Bot, __: str, record: Dict[str, Any]) -> str:
    result = record.get("result", {})
    file_name = _safe_name(result.get("file_name", ""), "document")
    summary = result.get("summary", "")
    extracted = result.get("text", "")
    processed_at = result.get("processed_at", "")

    safe_name = os.path.splitext(file_name)[0][:80] or "document"
    drive_file_name = f"{safe_name}_summary.txt"

    content_lines = [
        f"원본 파일명: {file_name}",
        f"분석 시각: {processed_at}",
        "",
        "[요약]",
        summary.strip() or "(요약 없음)",
        "",
        "[추출된 본문 일부]",
        textwrap.shorten(extracted.strip() or "(본문 없음)", width=4000, placeholder="…"),
    ]

    fd, tmp_path = tempfile.mkstemp(prefix="doc_summary_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write("\n".join(content_lines))

        success, message = await _upload_local_file(tmp_path, drive_file_name)
        return message if success else message
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _handle_image_original(bot: Bot, chat_id: str, record: Dict[str, Any]) -> str:
    meta = record.get("meta", {})
    file_id = meta.get("file_id")
    file_name = _safe_name(meta.get("file_name", ""), "image.jpg")

    if not file_id:
        return "⚠️ 원본 이미지 정보를 찾지 못했어요."

    tmp_path = None
    try:
        suffix = os.path.splitext(file_name)[1] or ".jpg"
        tmp_path = await _download_telegram_file(bot, file_id, suffix)
        success, message = await _upload_local_file(tmp_path, file_name)
        return message if success else message
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _handle_image_summary(_: Bot, __: str, record: Dict[str, Any]) -> str:
    result = record.get("result", {})
    processed_at = result.get("processed_at", "")
    description = result.get("description", "")
    analysis = result.get("analysis", "")

    drive_file_name = f"image_analysis_{processed_at[:19].replace(':', '') or 'result'}.txt"

    content_lines = [
        f"분석 시각: {processed_at}",
        "",
        "[설명]",
        description.strip() or "(설명이 비어 있습니다)",
        "",
        "[분석]",
        analysis.strip() or "(분석 내용이 없습니다)",
    ]

    fd, tmp_path = tempfile.mkstemp(prefix="image_summary_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write("\n".join(content_lines))

        success, message = await _upload_local_file(tmp_path, drive_file_name)
        return message if success else message
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _handle_audio_original(bot: Bot, chat_id: str, record: Dict[str, Any]) -> str:
    meta = record.get("meta", {})
    file_id = meta.get("file_id")
    file_name = _safe_name(meta.get("file_name", ""), "audio.ogg")

    if not file_id:
        return "⚠️ 원본 오디오 정보를 찾지 못했어요."

    tmp_path = None
    try:
        suffix = os.path.splitext(file_name)[1] or ".ogg"
        tmp_path = await _download_telegram_file(bot, file_id, suffix)
        success, message = await _upload_local_file(tmp_path, file_name)
        return message if success else message
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _handle_audio_summary(_: Bot, __: str, record: Dict[str, Any]) -> str:
    result = record.get("result", {})
    processed_at = result.get("processed_at", "")
    transcription = result.get("transcription", "")
    summary = result.get("summary", "")

    drive_file_name = f"audio_summary_{processed_at[:19].replace(':', '') or 'result'}.txt"

    content_lines = [
        f"분석 시각: {processed_at}",
        "",
        "[전사]",
        transcription.strip() or "(전사 내용이 없습니다)",
        "",
        "[요약]",
        summary.strip() or "(요약이 없습니다)",
    ]

    fd, tmp_path = tempfile.mkstemp(prefix="audio_summary_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write("\n".join(content_lines))

        success, message = await _upload_local_file(tmp_path, drive_file_name)
        return message if success else message
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _handle_combo(
    primary: Callable[[Bot, str, Dict[str, Any]], asyncio.Future],
    secondary: Callable[[Bot, str, Dict[str, Any]], asyncio.Future],
    bot: Bot,
    chat_id: str,
    record: Dict[str, Any],
) -> str:
    messages = []
    messages.append(await primary(bot, chat_id, record))
    messages.append(await secondary(bot, chat_id, record))
    combined = "\n".join(filter(None, messages))
    return combined or "처리할 작업이 없습니다."


FOLLOWUP_ACTIONS: Dict[str, Dict[str, Any]] = {
    "document_original": {
        "task_type": "document",
        "label_once": "Drive 원본 저장",
        "label_auto": "항상 원본 저장",
        "display": "문서 원본 Drive 저장",
        "handler": _handle_document_original,
    },
    "document_summary": {
        "task_type": "document",
        "label_once": "Drive 요약 저장",
        "label_auto": "항상 요약 저장",
        "display": "문서 요약 Drive 저장",
        "handler": _handle_document_summary,
    },
    "document_original_summary": {
        "task_type": "document",
        "label_once": "원본+요약 저장",
        "label_auto": "항상 원본+요약",
        "display": "문서 원본+요약 저장",
        "handler": lambda bot, chat_id, record: _handle_combo(
            _handle_document_original, _handle_document_summary, bot, chat_id, record
        ),
    },
    "image_original": {
        "task_type": "image",
        "label_once": "이미지 원본 저장",
        "label_auto": "항상 이미지 저장",
        "display": "이미지 원본 Drive 저장",
        "handler": _handle_image_original,
    },
    "image_summary": {
        "task_type": "image",
        "label_once": "설명/분석 텍스트 저장",
        "label_auto": "항상 분석 저장",
        "display": "이미지 분석 텍스트 저장",
        "handler": _handle_image_summary,
    },
    "image_original_summary": {
        "task_type": "image",
        "label_once": "이미지+분석 저장",
        "label_auto": "항상 이미지+분석",
        "display": "이미지 원본+분석 저장",
        "handler": lambda bot, chat_id, record: _handle_combo(
            _handle_image_original, _handle_image_summary, bot, chat_id, record
        ),
    },
    "audio_original": {
        "task_type": "audio",
        "label_once": "오디오 원본 저장",
        "label_auto": "항상 오디오 저장",
        "display": "오디오 원본 Drive 저장",
        "handler": _handle_audio_original,
    },
    "audio_summary": {
        "task_type": "audio",
        "label_once": "전사/요약 저장",
        "label_auto": "항상 전사/요약",
        "display": "오디오 전사/요약 저장",
        "handler": _handle_audio_summary,
    },
    "audio_original_summary": {
        "task_type": "audio",
        "label_once": "오디오+요약 저장",
        "label_auto": "항상 오디오+요약",
        "display": "오디오 원본+요약 저장",
        "handler": lambda bot, chat_id, record: _handle_combo(
            _handle_audio_original, _handle_audio_summary, bot, chat_id, record
        ),
    },
}

ACTION_LABELS: Dict[str, str] = {"none": "아무 작업하지 않기"}
ACTION_LABELS.update({code: data["display"] for code, data in FOLLOWUP_ACTIONS.items()})


async def execute_followup_action(action: str, bot: Bot, chat_id: str, record: Dict[str, Any]) -> Tuple[str, str]:
    action = (action or "none").lower()

    if action == "none":
        message = "처리 결과를 저장하지 않고 마무리했어요."
    else:
        info = FOLLOWUP_ACTIONS.get(action)
        if not info:
            message = "⚠️ 지원하지 않는 작업입니다."
        else:
            handler = info["handler"]
            message = await handler(bot, chat_id, record)

    try:
        await bot.send_message(chat_id=int(chat_id), text=message)
    except Exception as exc:
        logger.error("Failed to send action confirmation message: %s", exc)

    return action, message

