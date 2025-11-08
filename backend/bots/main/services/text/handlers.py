"""Text-centric handlers extracted from the monolithic runtime."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:  # pragma: no cover - hints only
    from telegram import Update
    from telegram.ext import ContextTypes


async def handle_start(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Greet the user and surface primary capabilities."""
    reply_text = runtime.reply_text
    ENABLE_DRIVE_MONITORING = runtime.ENABLE_DRIVE_MONITORING

    name = update.effective_user.first_name or "사용자"
    monitoring_status = "🔄 Drive 자동 모니터링" if ENABLE_DRIVE_MONITORING else "📋 Manual Drive 체크"
    await reply_text(
        update,
        (
            f"안녕하세요 {name}님! 👋\n\n"
            "이 봇은 Gemini 2.5 Flash 기반 \"올인원\"입니다.\n"
            "- 자유 대화 (메모리 포함)\n"
            "- 문서/이미지/음성 멀티모달 처리\n"
            "- Google Drive 양방향 동기화\n"
            "- Gmail 실시간 감시 및 AI 요약\n"
            f"- {monitoring_status}\n\n"
            "📂 **Drive 명령어**: /drive\n"
            "📧 **Gmail 명령어**: /gmail_on, /gmail_off"
        ),
    )


async def handle_mode(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Placeholder mode handler (kept for backward compatibility)."""
    reply_text = runtime.reply_text
    await reply_text(
        update,
        (
            "현재는 기본 대화 모드만 지원합니다.\n"
            "필요한 모드가 있다면 요청해 주세요!"
        ),
    )


async def handle_text(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Main chat handler that routes user text to Gemini while using memory."""
    GEMINI_API_KEY = runtime.GEMINI_API_KEY
    gemini_chat_model = getattr(runtime, "gemini_chat_model", None)
    reply_text = runtime.reply_text
    fetch_memory = runtime.fetch_memory
    save_memory = runtime.save_memory
    ActionIndicator = runtime.ActionIndicator
    ChatAction = runtime.ChatAction
    format_plain = runtime.format_plain
    logger = runtime.logger

    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return

    if not GEMINI_API_KEY or not gemini_chat_model:
        await reply_text(update, "Gemini 설정이 없어 대화가 비활성화되어 있어요.")
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "사용자"

    memory: List[dict] = await fetch_memory(user_id)
    context_lines: List[str] = []
    if memory:
        context_lines.append("[이전 대화 맥락]")
        for item in memory:
            context_lines.append(f"User: {item['message']}")
            context_lines.append(f"Assistant: {item['response']}")
        context_lines.append("")

    short_keywords = ["요약", "간단히", "짧게", "요약", "간단"]
    long_keywords = ["자세히", "구체적으로", "설명", "상세히", "자세한"]
    is_short_question = any(keyword in text for keyword in short_keywords)
    is_long_question = any(keyword in text for keyword in long_keywords)

    if is_long_question:
        prompt_style = "자세하고 구체적으로 설명해 주세요."
    elif is_short_question:
        prompt_style = "간단히 요약해 주세요."
    else:
        prompt_style = "간단히 요약해 주세요. 더 자세히 필요하면 추가 요청해 주세요."

    prompt = "\n".join(
        context_lines
        + [
            f"현재 사용자 메시지: {text}",
            f"답변 스타일: {prompt_style}",
            "항상 한국어로만 답변하고, Markdown 표/코드블록 없이 간결한 문장으로 답하세요.",
        ]
    )

    progress_messages = []
    progress_messages.append(await update.message.reply_text("💬 답변 생성 중… [10%]"))

    indicator = ActionIndicator(context, update.effective_chat.id, ChatAction.TYPING)
    await indicator.__aenter__()

    progress_messages.append(await update.message.reply_text("🧠 Gemini 2.5 Flash-Lite 분석 중… [50%]"))

    try:
        def _call_gemini():
            response = gemini_chat_model.generate_content(prompt)
            return response.text.strip()

        raw = await asyncio.to_thread(_call_gemini)
        answer = format_plain(raw)
        logger.info("Bot replied (%s chars): %s...", len(answer), answer[:100])
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Gemini error: %s", exc)
        answer = "죄송해요, 지금은 답변을 생성할 수 없어요."
    finally:
        await indicator.__aexit__(None, None, None)

    progress_messages.append(await update.message.reply_text("✅ 답변 완성! [100%]"))

    await reply_text(update, answer)
    await save_memory(user_id, username, text, answer)


async def handle_list(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Show recent document history for the user."""
    reply_text = runtime.reply_text
    recent_documents = runtime.recent_documents

    user_id = update.effective_user.id
    docs = recent_documents.get(user_id, [])[-5:]
    if not docs:
        await reply_text(update, "저장된 최근 문서가 없어요.")
        return

    lines = [f"{index + 1}. {doc['file_name']} ({doc['text_length']}자)" for index, doc in enumerate(docs)]
    await reply_text(update, "최근 문서 목록:\n" + "\n".join(lines))
