"""Google Drive 관련 텔레그램 명령 핸들러."""
from __future__ import annotations

import asyncio
from typing import List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from backend.services.drive_sync import (  # type: ignore
    check_new_files,
    format_file_list,
    get_folder_files,
)


async def handle_drive_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/drive 도움말 출력."""

    help_text = (
        "📁 **Google Drive 사용 가이드**\n\n"
        "**명령어**\n"
        "- `/drive` - 이 도움말 보기\n"
        "- `/drivelist` - 기본 폴더 파일 목록 보기\n"
        "- `/driveget <file_id>` - 특정 파일 다운로드\n"
        "- `/drivesync` - 새로 업로드된 파일 확인\n\n"
        "**팁**\n"
        "- 폴더 ID를 알고 있다면 `/drivelist <folder_id>` 로 하위 폴더도 확인할 수 있어요.\n"
        "- 새 파일이 올라왔는지 빠르게 확인하려면 `/drivesync` 를 사용해주세요."
    )

    await update.message.reply_text(help_text)


async def handle_drive_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    args_override: Optional[List[str]] = None,
) -> None:
    """/drivelist 명령 처리."""

    args = args_override if args_override is not None else (getattr(context, "args", []) or [])
    folder_id = args[0] if args else None

    progress = await update.message.reply_text("📁 드라이브 파일 목록을 불러오는 중입니다...")

    try:
        files = await asyncio.to_thread(get_folder_files, folder_id)
        message = await asyncio.to_thread(format_file_list, files)
        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text=message,
            parse_mode="Markdown",
        )
    except Exception as exc:  # pragma: no cover - 방어적 처리
        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text="❌ 드라이브 목록을 불러오지 못했습니다.",
        )
        raise exc


async def handle_drive_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/drivesync 명령 처리."""

    progress = await update.message.reply_text("🔍 드라이브 새 파일을 확인하는 중입니다...")

    try:
        new_files = await asyncio.to_thread(check_new_files)

        if not new_files:
            text = "📭 새로 업로드된 파일이 없습니다."
        else:
            lines = [f"🆕 새 파일 {len(new_files)}개 발견!"]
            for index, file in enumerate(new_files, 1):
                name = file.get("name", "이름 없음")
                file_id = file.get("id", "-")
                mime_type = file.get("mimeType", "-")
                lines.append(f"{index}. {name} ({mime_type})\n   ID: `{file_id}`")
            text = "\n".join(lines)

        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as exc:  # pragma: no cover - 방어적 처리
        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text="❌ 드라이브 새 파일 확인 중 오류가 발생했습니다.",
        )
        raise exc
