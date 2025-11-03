"""
Telegram Bot API 키 검증 서비스
Telegram Bot Token의 유효성을 확인합니다.
"""
import requests


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
            return {
                'valid': False,
                'error': f'HTTP {response.status_code}: {response.text[:100]}'
            }
        
        # JSON 파싱
        data = response.json()
        
        # API 응답 확인
        if not data.get('ok'):
            return {
                'valid': False,
                'error': data.get('description', 'Unknown Telegram API error')
            }
        
        # Bot 정보 추출
        bot_info = data.get('result', {})
        
        # 필수 필드 검증
        if not bot_info.get('id') or not bot_info.get('username'):
            return {
                'valid': False,
                'error': 'Invalid bot info format'
            }
        
        # 성공 응답
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
        return {
            'valid': False,
            'error': 'Request timeout (10s)'
        }
        
    except requests.exceptions.ConnectionError:
        return {
            'valid': False,
            'error': 'Connection error - please check your internet connection'
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'valid': False,
            'error': f'Request error: {str(e)}'
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f'Unexpected error: {str(e)}'
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
        return result['bot_info']
    else:
        return None
