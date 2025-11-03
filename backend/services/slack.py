"""
Slack API 키 검증 서비스
Slack Bot Token의 유효성을 확인합니다.
"""
import requests


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
            return {
                'valid': False,
                'error': f'HTTP {response.status_code}: {response.text[:100]}'
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
            
            return {
                'valid': False,
                'error': error_msg
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
        return {
            'valid': True,
            'team_info': team_info
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
        return result['team_info']
    else:
        return None
