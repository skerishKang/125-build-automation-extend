"""
Slack API 유틸리티 - 토큰 검증 및 메시지 전송
"""
import logging
import os
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger("slack_service")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
SLACK_USERNAME = os.getenv("SLACK_USERNAME", "Limone Bot")

def verify_slack_token(token: str) -> dict:
    """
    Slack Bot Token 유효성 검증
    
    Slack API의 auth.test 엔드포인트를 호출하여
    토큰이 유효한지 확인합니다.
    
    Args:
        token: Slack Bot Token (형식: xoxb-...)
    
    Returns:
        {'valid': bool, 'team_info': dict, 'error': str}
    """
    try:
        # Slack API 호출
        url = 'https://slack.com/api/auth.test'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # HTTP 요청 실패
        if response.status_code != 200:
            error_message = f'HTTP {response.status_code}: {response.text[:100]}'
            logger.error(error_message) # Log the error
            return {
                'valid': False,
                'error': error_message
            }
        
        # JSON 파싱
        data = response.json()
        
        # API 응답 확인 (Slack은 'ok' 필드 사용)
        if not data.get('ok'):
            error_code = data.get('error', 'Unknown Slack API error')
            error_msg = {
                'invalid_auth': 'Invalid authentication token',
                'account_inactive': 'Token is for a deleted/inactive workspace',
                'token_revoked': 'Token has been revoked',
                'missing_scope': 'Token is missing required scopes',
                'invalid_client_id': 'Client ID is invalid',
                'invalid_client_secret': 'Client secret is invalid'
            }.get(error_code, error_code)
            
            full_error_message = f"Slack API error: {error_msg} (Code: {error_code})"
            logger.error(full_error_message) # Log the error
            return {
                'valid': False,
                'error': full_error_message
            }
        
        # 팀 정보 추출
        team_info = {
            'team_id': data.get('team_id'),
            'team': data.get('team'),
            'user_id': data.get('user_id'),
            'user': data.get('user'),
            'url': data.get('url')
        }
        
        # 성공 응답
        logger.info(f"Slack token verified successfully for team: {team_info.get('team')}")
        return {
            'valid': True,
            'team_info': team_info
        }
        
    except requests.exceptions.Timeout:
        error_message = 'Request timeout (10s)'
        logger.error(error_message)
        return {
            'valid': False,
            'error': error_message
        }
        
    except requests.exceptions.ConnectionError:
        error_message = 'Connection error - please check your internet connection'
        logger.error(error_message)
        return {
            'valid': False,
            'error': error_message
        }
        
    except requests.exceptions.RequestException as e:
        error_message = f'Request error: {str(e)}'
        logger.error(error_message)
        return {
            'valid': False,
            'error': error_message
        }
        
    except Exception as e:
        error_message = f'Unexpected error: {str(e)}'
        logger.error(error_message)
        return {
            'valid': False,
            'error': error_message
        }


def get_team_info(token: str) -> dict:
    """
    Slack Team 정보 조회
    
    Args:
        token: Slack Bot Token
    
    Returns:
        Team 정보 딕셔너리 (실패시 None)
    """
    result = verify_slack_token(token)
    
    if result['valid']:
        logger.info(f"Successfully retrieved team info for token.")
        return result['team_info']
    else:
        # verify_slack_token에서 이미 로깅되었으므로 여기서는 추가 로깅 불필요
        return None


def _post_webhook(payload: Dict[str, Any]) -> bool:
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code >= 400:
            logger.error("Slack webhook error %s: %s", response.status_code, response.text[:200])
            return False
        return True
    except requests.RequestException as exc:  # pragma: no cover - 네트워크 장애 대비
        logger.error("Slack webhook request failed: %s", exc)
        return False


def _post_chat_message(payload: Dict[str, Any]) -> bool:
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    try:
        response = requests.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers, timeout=10)
        data = response.json()
        if not data.get("ok"):
            logger.error("Slack chat.postMessage error: %s", data.get("error", "unknown"))
            return False
        return True
    except Exception as exc:  # pragma: no cover - 네트워크 장애 대비
        logger.error("Slack chat.postMessage request failed: %s", exc)
        return False


def send_message(text: str, *, blocks: Optional[list] = None, channel: Optional[str] = None) -> bool:
    """Slack 채널/웹훅으로 메시지를 전송합니다."""
    if not text:
        return False

    if SLACK_WEBHOOK_URL:
        payload: Dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        if SLACK_USERNAME:
            payload["username"] = SLACK_USERNAME
        return _post_webhook(payload)

    if SLACK_BOT_TOKEN and (channel or SLACK_CHANNEL):
        payload = {
            "channel": channel or SLACK_CHANNEL,
            "text": text,
        }
        if blocks:
            payload["blocks"] = blocks
        if SLACK_USERNAME:
            payload["username"] = SLACK_USERNAME
        return _post_chat_message(payload)

    logger.debug("Slack integration not configured. Message skipped.")
    return False
