"""Notion API 연동 유틸리티."""
from __future__ import annotations

import logging
import os
from typing import Dict, Any, List

import requests

logger = logging.getLogger("notion_service")

def _notion_headers() -> Dict[str, str]:
    token = os.getenv("NOTION_API_TOKEN")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def create_page(title: str, content_blocks: List[Dict[str, Any]]) -> bool:
    """노션 데이터베이스에 새 페이지를 생성합니다."""
    database_id = os.getenv("NOTION_DATABASE_ID")
    headers = _notion_headers()

    if not database_id or not headers:
        logger.warning("Notion 통합이 비활성화되어 있어 페이지를 생성할 수 없습니다.")
        return False

    payload: Dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {"content": title[:2000] or "자동 기록"}
                    }
                ]
            }
        },
        "children": content_blocks,
    }

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if response.status_code >= 400:
            logger.error("Failed to create Notion page: %s", response.text)
            return False
        return True
    except requests.RequestException as exc:  # pragma: no cover - 네트워크 장애 대비
        logger.error("Notion page creation request failed: %s", exc)
        return False


def build_paragraph_block(text: str) -> Dict[str, Any]:
    """단락 블록을 생성합니다."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text[:2000]},
                }
            ],
        },
    }
