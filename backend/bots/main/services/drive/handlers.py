"""Drive command handlers for the unified Telegram bot runtime."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - imported for type hints only
    from telegram import Update
    from telegram.ext import ContextTypes


async def handle_drive(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /drive command - show Google Drive sync help."""
    reply_text = runtime.reply_text

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


async def handle_drive_list(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /drivelist command - list all files in Google Drive."""
    reply_text = runtime.reply_text
    logger = runtime.logger

    progress_messages = []
    progress_messages.append(await update.message.reply_text("📁 드라이브 파일 목록 조회 중... [0%]"))

    try:
        backend_path = os.path.join(os.path.dirname(__file__), "..")
        backend_path = os.path.abspath(backend_path)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        from backend.services.drive_sync import get_folder_files, format_file_list  # noqa: WPS433

        progress_messages.append(await update.message.reply_text("📂 드라이브 연결 중... [30%]"))

        files = get_folder_files()

        progress_messages.append(await update.message.reply_text("📋 파일 목록 생성 중... [70%]"))

        result = format_file_list(files)

        progress_messages.append(await update.message.reply_text("✅ 조회 완료! [100%]"))

        await reply_text(update, result)

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Drive list error: %s", exc)
        await reply_text(update, f"드라이브 목록 조회 중 오류가 발생했어요: {str(exc)[:100]}")


async def handle_drive_get(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /driveget command - download a file from Google Drive."""
    reply_text = runtime.reply_text
    logger = runtime.logger

    args = context.args
    if not args:
        await reply_text(update, "사용법: `/driveget <file_id>`\n\n예: `/driveget 1A2B3C4D`")
        return

    file_id = args[0]

    progress_messages = []
    progress_messages.append(await update.message.reply_text("📥 드라이브에서 파일 다운로드 중... [0%]"))

    try:
        backend_path = os.path.join(os.path.dirname(__file__), "..")
        backend_path = os.path.abspath(backend_path)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        from backend.services.drive_sync import get_file_info, download_file  # noqa: WPS433

        progress_messages.append(await update.message.reply_text("📂 파일 정보 조회 중... [30%]"))

        file_info = get_file_info(file_id)

        if not file_info:
            progress_messages.append(await update.message.reply_text("❌ 파일을 찾을 수 없습니다 [100%]"))
            await reply_text(update, "❌ 파일을 찾을 수 없어요. File ID를 확인해주세요.")
            return

        file_name = file_info["name"]
        progress_messages.append(await update.message.reply_text(f"📄 {file_name} 다운로드 중... [60%]"))

        tmp_path = os.path.join(tempfile.gettempdir(), f"drive_download_{file_id}_{file_name}")
        success = download_file(file_id, tmp_path)

        if not success:
            progress_messages.append(await update.message.reply_text("❌ 다운로드 실패 [100%]"))
            await reply_text(update, "❌ 파일 다운로드에 실패했어요.")
            return

        progress_messages.append(await update.message.reply_text("✅ 다운로드 완료! [100%]"))

        from telegram import InputFile  # Imported lazily to avoid global PTB dependency

        with open(tmp_path, "rb") as file_descriptor:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=InputFile(file_descriptor, filename=file_name),
                caption=f"📄 **드라이브에서 가져온 파일**: {file_name}",
            )

        try:
            os.remove(tmp_path)
        except Exception:  # pragma: no cover - cleanup best-effort
            pass

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Drive get error: %s", exc)
        await reply_text(update, f"파일 다운로드 중 오류가 발생했어요: {str(exc)[:100]}")


async def handle_drive_sync(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /drivesync command - check for new files in Google Drive."""
    reply_text = runtime.reply_text
    logger = runtime.logger

    progress_messages = []
    progress_messages.append(await update.message.reply_text("🔍 드라이브 새 파일 확인 중... [0%]"))

    try:
        backend_path = os.path.join(os.path.dirname(__file__), "..")
        backend_path = os.path.abspath(backend_path)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        from backend.services.drive_sync import (  # noqa: WPS433
            check_deleted_files,
            check_new_files,
            get_folder_files,
        )

        progress_messages.append(await update.message.reply_text("📂 드라이브 스캔 중... [50%]"))

        current_files = get_folder_files()
        new_files = check_new_files()
        deleted_files = check_deleted_files(current_files)

        progress_messages.append(await update.message.reply_text("✅ 확인 완료! [100%]"))

        result_lines = []
        has_changes = False

        if new_files:
            has_changes = True
            result_lines.append(f"🆕 **새로 올라온 파일** ({len(new_files)}개):\n")
            for index, file in enumerate(new_files, 1):
                file_type = "📁 폴더" if file.get("mimeType") == "application/vnd.google-apps.folder" else "📄 파일"
                result_lines.append(f"{index}. {file_type}: **{file['name']}**")
                result_lines.append(f"   ID: `{file['id']}`")
            result_lines.append("")

        if deleted_files:
            has_changes = True
            result_lines.append(f"🗑️ **삭제된 파일** ({len(deleted_files)}개):\n")
            for index, file in enumerate(deleted_files, 1):
                result_lines.append(f"{index}. **{file['name']}**")
                result_lines.append(f"   ID: `{file['id']}`")
            result_lines.append("")

        if not has_changes:
            await reply_text(update, "📭 새 파일이 없습니다.")
        else:
            await reply_text(update, "\n".join(result_lines).strip())

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Drive sync error: %s", exc)
        await reply_text(update, f"드라이브 동기화 중 오류가 발생했어요: {str(exc)[:100]}")


async def monitor_drive_changes(runtime: Any) -> None:
    """Background task to monitor Google Drive for changes."""
    logger = runtime.logger
    ENABLE_DRIVE_MONITORING = runtime.ENABLE_DRIVE_MONITORING
    DRIVE_MONITOR_INTERVAL = runtime.DRIVE_MONITOR_INTERVAL
    app_instance = runtime._app_instance

    logger.info("🔍 Drive monitoring worker started")

    backend_path = os.path.join(os.path.dirname(__file__), "..")
    backend_path = os.path.abspath(backend_path)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    while True:
        try:
            if not ENABLE_DRIVE_MONITORING:
                await asyncio.sleep(60)
                continue

            from backend.services.drive_sync import (  # noqa: WPS433
                cache_current_files,
                check_deleted_files,
                check_new_files,
                get_folder_files,
                load_cached_files,
            )

            current_files = get_folder_files()
            deleted_files = check_deleted_files(current_files)
            new_files = check_new_files()

            if (new_files or deleted_files) and app_instance:
                message_parts = []

                if new_files:
                    message_parts.append(f"🆕 **새로 올라온 파일** ({len(new_files)}개):")
                    for file in new_files[:5]:
                        file_type = "📁 폴더" if file.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
                        message_parts.append(f"• {file_type}: {file['name']}")
                    if len(new_files) > 5:
                        message_parts.append(f"... 외 {len(new_files) - 5}개")
                    message_parts.append("")

                if deleted_files:
                    message_parts.append(f"🗑️ **삭제된 파일** ({len(deleted_files)}개):")
                    for file in deleted_files[:5]:
                        message_parts.append(f"• {file['name']}")
                    if len(deleted_files) > 5:
                        message_parts.append(f"... 외 {len(deleted_files) - 5}개")
                    message_parts.append("")

                notification_text = "\n".join(message_parts).strip()
                logger.info(
                    "Drive changes detected: %s new, %s deleted",
                    len(new_files),
                    len(deleted_files),
                )

                if notification_text and app_instance.chat_ids:
                    for chat_id in app_instance.chat_ids:
                        try:
                            await app_instance.bot.send_message(chat_id=chat_id, text=notification_text)
                        except Exception as exc:  # pragma: no cover - best effort
                            logger.warning("Failed to send drive notification to %s: %s", chat_id, exc)

            if not load_cached_files():
                cache_current_files(current_files)
                logger.info("Initialized Drive file cache")

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Drive monitoring error: %s", exc)

        await asyncio.sleep(DRIVE_MONITOR_INTERVAL)

    logger.info("🔍 Drive monitoring worker stopped")


async def handle_document_auto_save(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    runtime.logger.info("handle_document_auto_save entered")
    """Auto-save incoming documents to Google Drive and analyze them."""
    ActionIndicator = runtime.ActionIndicator
    ChatAction = runtime.ChatAction
    GEMINI_API_KEY = runtime.GEMINI_API_KEY
    gemini_model = runtime.gemini_model
    extract_text_from_file = runtime.extract_text_from_file
    format_plain = runtime.format_plain
    reply_text = runtime.reply_text
    logger = runtime.logger

    doc = update.message.document
    if not doc:
        await reply_text(update, "문서를 찾을 수 없어요.")
        return

    # Check if it's an audio file - redirect to voice processing
    file_name = doc.file_name or ""
    # Get file extension (case-insensitive)
    file_ext = os.path.splitext(file_name)[1].lower() if file_name else ""
    audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma', '.opus', '.m4b', '.mp4']
    if file_ext in audio_extensions:
        logger.info(f"Detected audio file: {file_name}, extension: {file_ext}")
        # Send immediate acknowledgment message
        await update.message.reply_text(f"🎤 오디오 파일을 받았습니다!\n파일: {file_name}")
        return  # Simply acknowledge and return - no further processing

    progress_messages = []
    progress_messages.append(await update.message.reply_text(f"📁 {doc.file_name} Google Drive 자동 저장 중... [0%]"))

    file = await context.bot.get_file(doc.file_id)
    tmp = os.path.join(tempfile.gettempdir(), f"{doc.file_id}_{doc.file_name}")

    doc_indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
    await doc_indicator.__aenter__()
    await file.download_to_drive(tmp)

    progress_messages.append(await update.message.reply_text("📁 파일 다운로드 완료. 드라이브 저장 중... [30%]"))

    try:
        backend_path = os.path.join(os.path.dirname(__file__), "..")
        backend_path = os.path.abspath(backend_path)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        from backend.services.drive_sync import upload_file  # noqa: WPS433

        result = upload_file(tmp)

        if result:
            progress_messages.append(await update.message.reply_text("✅ Google Drive 저장 완료! [100%]"))

            file_id = result.get("id", "N/A")
            web_link = result.get("webViewLink", "")

            confirm_text = (
                f"✅ **{doc.file_name}** Google Drive에 자동 저장되었습니다!\n\n"
                f"📋 파일 ID: `{file_id}`"
            )
            if web_link:
                confirm_text += f"\n🔗 [드라이브에서 보기]({web_link})"

            await reply_text(update, confirm_text)

            if GEMINI_API_KEY and gemini_model:
                try:
                    progress_messages.append(await update.message.reply_text("🧠 Gemini 문서 분석 중... [70%]"))

                    extracted_text = extract_text_from_file(tmp, doc.file_name)

                    if extracted_text and extracted_text.strip():
                        prompt = f"다음 문서를 요약/분석해줘. 파일명: {doc.file_name}\n\n{extracted_text}"
                        prompt += "\n\n항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요."

                        def _call_gemini_doc():
                            response = gemini_model.generate_content(prompt)
                            return response.text.strip()

                        answer = await asyncio.to_thread(_call_gemini_doc)
                        answer = format_plain(answer)

                        analysis_text = f"\n\n📄 **문서 분석 결과**:\n\n{answer}"
                        await reply_text(update, analysis_text)
                    else:
                        logger.warning("No text extracted from %s", doc.file_name)

                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Document analysis error: %s", exc)

        else:
            progress_messages.append(await update.message.reply_text("❌ 드라이브 저장 실패 [100%]"))
            await reply_text(update, "❌ Google Drive 저장에 실패했어요. 권한을 확인해주세요.")

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Auto-save error: %s", exc)
        await reply_text(update, f"자동 저장 중 오류가 발생했어요: {str(exc)[:100]}")
    finally:
        try:
            os.remove(tmp)
        except Exception:  # pragma: no cover - cleanup best-effort
            pass
        await doc_indicator.__aexit__(None, None, None)
