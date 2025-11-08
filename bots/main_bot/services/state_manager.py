"""메인 봇 상태 및 후속 작업 관리 모듈."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from bots.main_bot.action_handlers import (  # type: ignore
    ACTION_LABELS,
    FOLLOWUP_ACTIONS,
    execute_followup_action,
)
from bots.main_bot.constants import (  # type: ignore
    PIPELINE_PRESET_LABELS,
    PIPELINE_PRESETS,
    TASK_TYPE_LABELS,
)
from bots.main_bot.utils.text_utils import format_duration  # type: ignore
from bots.shared.user_preferences import DEFAULT_PREFERENCES, preference_store  # type: ignore

logger = logging.getLogger("main_bot.state")

# 전역 상태 저장소
active_tasks: Dict[str, Dict[str, Dict[str, Any]]] = {}
user_sessions: Dict[str, Dict[str, Any]] = {}
pending_results: Dict[str, Dict[str, Any]] = {}
followup_tasks: Dict[str, Dict[str, Any]] = {}
preference_history: Dict[str, List[Dict[str, Any]]] = {}
last_preference_states: Dict[str, Dict[str, Any]] = {}
manual_result_listener_task: Dict[str, Optional[asyncio.Task]] = {"task": None}

MODE_LABELS = {
    "ask": "대화형 모드 (항상 물어보기)",
    "auto": "자동 실행 모드",
    "skip": "요약만 받고 건너뛰기",
}


def estimate_processing_time(task_type: str, file_info: Dict[str, Any]) -> int:
    """업무 유형에 따라 대략적인 처리 시간을 추정."""

    if task_type == "audio":
        duration = file_info.get("duration", 60)
        return int(duration * 2.5) + 30

    if task_type == "document":
        file_name = (file_info.get("file_name") or "").lower()
        file_size = file_info.get("file_size", 0)

        if file_name.endswith(".pdf"):
            estimated_pages = (file_size / 1024 / 1024) * 20
            return int(estimated_pages * 1.5) + 30
        if file_name.endswith(".docx"):
            return 60
        if file_name.endswith(".txt"):
            return 30
        if file_name.endswith(".xlsx") or file_name.endswith(".csv"):
            return 90
        return 60

    if task_type == "image":
        return 30

    return 60


async def send_progress_updates(
    bot: Bot,
    chat_id: int,
    task_id: str,
    task_type: str,
    estimated_time: int,
    cancel_event: asyncio.Event,
) -> None:
    """작업 완료 시까지 주기적으로 진행 상황 메시지를 전송."""

    emoji_map = {"audio": "🎤", "document": "📄", "image": "🖼️"}
    emoji = emoji_map.get(task_type, "⚙️")

    loop = asyncio.get_event_loop()
    start_time = loop.time()
    update_interval = 20
    last_percent = -1

    await bot.send_message(
        chat_id=chat_id,
        text=f"{emoji} 처리 시작! ⏱️ 예상 시간: ~{format_duration(estimated_time)}",
    )

    while not cancel_event.is_set():
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=update_interval)
            break
        except asyncio.TimeoutError:
            elapsed = int(loop.time() - start_time)
            if estimated_time > 0:
                progress_percent = min(99, int((elapsed / estimated_time) * 100))
                if progress_percent > 0:
                    remaining = int((estimated_time * (100 - progress_percent)) / progress_percent)
                else:
                    remaining = estimated_time
            else:
                progress_percent = 50
                remaining = 0

            if progress_percent == last_percent:
                continue

            last_percent = progress_percent

            filled = int(progress_percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress_text = (
                f"{emoji} 처리 중... {progress_percent}%\n"
                f"{bar}\n"
                f"⏱️ 경과: {format_duration(elapsed)}"
            )
            if remaining > 0:
                progress_text += f" / 남은 시간: ~{format_duration(remaining)}"

            try:
                await bot.send_message(chat_id=chat_id, text=progress_text)
            except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
                logger.warning("Failed to update progress message: %s", exc)

    total_elapsed = int(loop.time() - start_time)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"{emoji} 처리 완료! ⏱️ 총 경과: {format_duration(total_elapsed)}",
        )
    except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
        logger.warning("Failed to finalize progress message: %s", exc)


async def wait_for_result(task_id: str, timeout: int = 1800) -> Optional[Dict[str, Any]]:
    """전문 봇 결과를 지정된 시간까지 대기."""

    event = asyncio.Event()
    pending_results[task_id] = {"event": event, "result": None}
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return pending_results.get(task_id, {}).get("result")
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for result for task %s", task_id)
        return None
    finally:
        pending_results.pop(task_id, None)


def register_followup_task(task_id: str, chat_id: str, task_type: str, result: Dict[str, Any], meta: Dict[str, Any]) -> None:
    followup_tasks[task_id] = {
        "chat_id": chat_id,
        "task_type": task_type,
        "result": result,
        "meta": meta,
    }


def get_default_action_for_type(prefs: Dict[str, Any], task_type: str) -> str:
    defaults = prefs.get("default_actions", {})
    if isinstance(defaults, dict):
        return defaults.get(task_type, "none")
    return "none"


def build_default_actions_summary(prefs: Dict[str, Any]) -> Dict[str, str]:
    return {
        task_type: get_default_action_for_type(prefs, task_type)
        for task_type in ("document", "image", "audio")
    }


def set_default_action_for_type(chat_id: str, task_type: str, action: str) -> Dict[str, Any]:
    prefs = preference_store.get_preferences(chat_id)
    defaults = build_default_actions_summary(prefs)
    defaults[task_type] = action
    return preference_store.set_preferences(chat_id, {"default_actions": defaults})


def format_action_label(action_code: str) -> str:
    return ACTION_LABELS.get(action_code, "(설정 없음)")


def get_actions_for_type(task_type: str) -> Dict[str, Dict[str, Any]]:
    return {
        code: data
        for code, data in FOLLOWUP_ACTIONS.items()
        if data.get("task_type") == task_type
    }


def build_settings_message(prefs: Dict[str, Any]) -> str:
    mode_label = MODE_LABELS.get(prefs.get("mode", ""), "미설정")
    defaults = build_default_actions_summary(prefs)
    integrations = prefs.get("integrations", {})
    slack_state = "✅" if integrations.get("slack", True) else "❌"
    notion_state = "✅" if integrations.get("notion", False) else "❌"

    lines = [
        "⚙️ 현재 하이브리드 자동화 설정",
        f"- 기본 모드: {mode_label}",
        "",
        f"문서 자동 작업: {format_action_label(defaults['document'])}",
        "  └ 문서 업로드 후 어떤 후속 작업을 기본 적용할지 선택합니다.",
        f"이미지 자동 작업: {format_action_label(defaults['image'])}",
        "  └ 이미지 업로드 시 OCR/요약/저장 등 기본 동작을 설정합니다.",
        f"오디오 자동 작업: {format_action_label(defaults['audio'])}",
        "  └ 음성 메시지 처리 후 자동으로 실행할 후속 액션을 지정합니다.",
        "",
        "🚀 파이프라인 프리셋",
        f"- 풀: {PIPELINE_PRESET_LABELS['full']} (원본 업로드 + 요약 + 노션/슬랙)",
        f"- 요약: {PIPELINE_PRESET_LABELS['summary']} (요약 위주, 원본 제외)",
        f"- 원본: {PIPELINE_PRESET_LABELS['original']} (파일 보존, 요약 생략)",
        "",
        "🔗 통합 설정",
        f"- Slack 알림: {slack_state} (파일 처리 결과를 Slack에도 발송)",
        f"- Notion 기록: {notion_state} (요약·추출 결과를 자동 기록)",
        "",
        "아래 인라인 버튼으로 모드·자동 작업·통합 설정을 즉시 변경할 수 있어요.",
    ]
    return "\n".join(lines)


def build_settings_keyboard(prefs: Dict[str, Any]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("대화형 모드", callback_data="pref_mode|ask"),
            InlineKeyboardButton("자동 실행", callback_data="pref_mode|auto"),
            InlineKeyboardButton("요약만", callback_data="pref_mode|skip"),
        ]
    ]

    for task_type in ("document", "image", "audio"):
        actions = get_actions_for_type(task_type)
        buttons = [
            InlineKeyboardButton(
                f"{TASK_TYPE_LABELS[task_type]}·{info['label_once']}",
                callback_data=f"pref_action|{task_type}|{code}",
            )
            for code, info in actions.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                f"{TASK_TYPE_LABELS[task_type]}·없음",
                callback_data=f"pref_action|{task_type}|none",
            )
        )
        rows.append(buttons)

    preset_buttons = [
        InlineKeyboardButton("풀 파이프라인", callback_data="pref_pipeline|full"),
        InlineKeyboardButton("요약 파이프라인", callback_data="pref_pipeline|summary"),
        InlineKeyboardButton("원본 파이프라인", callback_data="pref_pipeline|original"),
    ]
    rows.append(preset_buttons)

    integrations = prefs.get("integrations", {})
    slack_label = "Slack 알림 ON" if integrations.get("slack", True) else "Slack 알림 OFF"
    notion_label = "Notion 기록 ON" if integrations.get("notion", False) else "Notion 기록 OFF"
    rows.append([
        InlineKeyboardButton(slack_label, callback_data="pref_integration|slack|toggle"),
        InlineKeyboardButton(notion_label, callback_data="pref_integration|notion|toggle"),
    ])
    rows.append([InlineKeyboardButton("되돌리기", callback_data="pref_undo|")])

    return InlineKeyboardMarkup(rows)


def build_followup_keyboard(task_type: str, task_id: str) -> InlineKeyboardMarkup:
    actions = get_actions_for_type(task_type)

    once_row = [
        InlineKeyboardButton(info["label_once"], callback_data=f"follow|{task_id}|once|{code}")
        for code, info in actions.items()
    ]
    auto_row = [
        InlineKeyboardButton(info["label_auto"], callback_data=f"follow|{task_id}|auto|{code}")
        for code, info in actions.items()
    ]
    preset_row = [
        InlineKeyboardButton("풀 파이프라인", callback_data="pref_pipeline|full"),
        InlineKeyboardButton("요약 파이프라인", callback_data="pref_pipeline|summary"),
        InlineKeyboardButton("원본 파이프라인", callback_data="pref_pipeline|original"),
    ]
    extra_row = [
        InlineKeyboardButton("건너뛰기", callback_data=f"follow|{task_id}|once|none"),
        InlineKeyboardButton("항상 건너뛰기", callback_data=f"follow|{task_id}|skip|none"),
        InlineKeyboardButton("설정 열기", callback_data="pref_open|global"),
    ]

    rows = [once_row, auto_row, preset_row, extra_row]
    return InlineKeyboardMarkup(rows)


async def prompt_followup(bot: Bot, chat_id: str, task_id: str, task_type: str) -> None:
    message = FOLLOWUP_PROMPTS.get(task_type, "후속 작업을 선택해주세요.")
    prefs = preference_store.get_preferences(chat_id)
    defaults = build_default_actions_summary(prefs)
    mode_label = MODE_LABELS.get(prefs.get("mode", ""), "미설정")
    current_default = format_action_label(defaults.get(task_type, "none"))
    message = (
        f"{message}\n\n"
        f"현재 모드: {mode_label}\n"
        f"기본 {TASK_TYPE_LABELS.get(task_type, '')} 작업: {current_default}"
    )

    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=message,
            reply_markup=build_followup_keyboard(task_type, task_id),
        )
    except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
        logger.error("Failed to send follow-up prompt: %s", exc)


async def apply_preferences_to_task(
    bot: Bot,
    chat_id: str,
    task_id: str,
    task_type: str,
    prefs: Dict[str, Any],
) -> None:
    record = followup_tasks.get(task_id)
    if not record:
        return

    last_state = last_preference_states.get(chat_id)
    task_type = task_type or record.get("task_type", "document")

    mode = prefs.get("mode", DEFAULT_PREFERENCES["mode"])
    action = get_default_action_for_type(prefs, task_type)

    if mode == "auto" and action != "none":
        action_label = format_action_label(action)
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"🔁 자동 실행 설정에 따라 \"{action_label}\" 작업을 진행합니다.",
            )
        except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
            logger.error("Failed to announce auto action (settings): %s", exc)
        await execute_followup_action(action, bot, chat_id, record)
        followup_tasks.pop(task_id, None)
        last_preference_states[chat_id] = {"mode": mode, "action": action}
    elif mode == "skip":
        if last_state and last_state.get("mode") == "skip":
            followup_tasks.pop(task_id, None)
            return
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text="결과만 전달하고 후속 작업은 건너뛰겠습니다.",
            )
        except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
            logger.error("Failed to send skip confirmation: %s", exc)
        followup_tasks.pop(task_id, None)
        last_preference_states[chat_id] = {"mode": mode}
    else:
        await prompt_followup(bot, chat_id, task_id, task_type)
        last_preference_states[chat_id] = {"mode": mode, "action": None}


async def apply_preferences_to_pending_tasks(
    bot: Bot,
    chat_id: str,
    task_type: Optional[str],
    prefs: Dict[str, Any],
) -> None:
    for pending_task_id, record in list(followup_tasks.items()):
        if record.get("chat_id") != chat_id:
            continue
        if task_type and record.get("task_type") != task_type:
            continue
        await apply_preferences_to_task(bot, chat_id, pending_task_id, record.get("task_type"), prefs)


def build_followup_record_summary(prefs: Dict[str, Any]) -> str:
    defaults = build_default_actions_summary(prefs)
    return " / ".join(
        f"{TASK_TYPE_LABELS[t]}:{format_action_label(defaults[t])}" for t in ("document", "image", "audio")
    )
*** End Patch
