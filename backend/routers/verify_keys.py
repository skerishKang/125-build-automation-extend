"""
API 키 검증 라우터 (단순 검증 버전)
Telegram, Slack API 키를 검증합니다.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel


router = APIRouter()


# API 키 검증 요청 스키마
class VerifyKeyRequest(BaseModel):
    """API 키 검증 요청 데이터"""
    api_key: str


@router.post('/{service_name}')
async def verify_api_key(
    service_name: str,
    request_data: VerifyKeyRequest
):
    """
    API 키 검증 (단순 검증, 저장 없음)
    
    Args:
        service_name: 서비스명 (telegram, slack)
        request_data: API 키가 포함된 요청 데이터
    
    Returns:
        검증 결과
    """
    # API 키 검증 실행
    verification_result = await _verify_service_key(service_name, request_data.api_key)

    if not verification_result['valid']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {service_name} API key: {verification_result.get('error', 'Unknown error')}"
        )

    return {
        'status': 'success',
        'service': service_name,
        'verified': True,
        'valid': True,
        'message': f'{service_name} API key is valid!'
    }


async def _verify_service_key(service_name: str, api_key: str) -> dict:
    """
    서비스별 API 키 검증 실행
    
    Args:
        service_name: 서비스명
        api_key: API 키
    
    Returns:
        {'valid': bool, 'error': str}
    """
    from backend.services import telegram, slack

    # 서비스별 검증 실행
    if service_name == 'telegram':
        return telegram.verify_telegram_token(api_key)
    elif service_name == 'slack':
        return slack.verify_slack_token(api_key)
    else:
        return {'valid': False, 'error': f'Only telegram and slack are supported'}



