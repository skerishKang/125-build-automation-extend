"""
Telegram Bot API 키 검증 서비스
Telegram Bot Token의 유효성을 확인합니다.
"""
import requests
import logging # Import the logging module

# Get the logger instance for this module
logger = logging.getLogger("telegram_service")

def verify_telegram_token(token: str) -> dict:
    """
    Telegram Bot Token 유효성 검증
    
    Telegram Bot API의 getMe 엔드포인트를 호출하여
    토큰이 유효한지 확인합니다.
    
    Args:
        token: Telegram Bot Token (형식: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
    
    Returns:
        {'valid': bool, 'bot_info': dict, 'error': str}
    """
    try:
        # Telegram Bot API 호출
        url = f'https://api.telegram.org/bot{token}/getMe'
        response = requests.get(url, timeout=10)
        
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
        
        # API 응답 확인
        if not data.get('ok'):
            error_description = data.get('description', 'Unknown Telegram API error')
            full_error_message = f"Telegram API error: {error_description}"
            logger.error(full_error_message) # Log the error
            return {
                'valid': False,
                'error': full_error_message
            }
        
        # Bot 정보 추출
        bot_info = data.get('result', {})
        
        # 필수 필드 검증
        if not bot_info.get('id') or not bot_info.get('username'):
            error_message = 'Invalid bot info format received from Telegram API'
            logger.error(error_message) # Log the error
            return {
                'valid': False,
                'error': error_message
            }
        
        # 성공 응답
        logger.info(f"Telegram token verified successfully for bot: {bot_info.get('username')}")
        return {
            'valid': True,
            'bot_info': {
                'id': bot_info.get('id'),
                'is_bot': bot_info.get('is_bot'),
                'first_name': bot_info.get('first_name'),
                'username': bot_info.get('username'),
                'can_join_groups': bot_info.get('can_join_groups'),
                'can_read_all_group_messages': bot_info.get('can_read_all_group_messages'),
                'supports_inline_queries': bot_info.get('supports_inline_queries')
            }
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


def get_bot_info(token: str) -> dict:
    """
    Telegram Bot 정보 조회
    
    Args:
        token: Telegram Bot Token
    
    Returns:
        Bot 정보 딕셔너리 (실패시 None)
    """
    result = verify_telegram_token(token)
    
    if result['valid']:
        logger.info(f"Successfully retrieved bot info for token.")
        return result['bot_info']
    else:
        # verify_telegram_token에서 이미 로깅되었으므로 여기서는 추가 로깅 불필요
        return None