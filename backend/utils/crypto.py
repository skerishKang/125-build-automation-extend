"""
AES256 암호화/복호화 유틸리티
API 키를 안전하게 저장하기 위해 AES256 암호화를 사용합니다.
"""
from cryptography.fernet import Fernet
import base64
import os


class CryptoManager:
    """API 키 암호화/복호화 관리 클래스"""

    def __init__(self, key: str):
        """
        CryptoManager 초기화

        Args:
            key: 32바이트 AES 암호화 키
        """
        # 키를 32바이트로 맞추고 base64로 인코딩
        key_bytes = key.encode()[:32].ljust(32, b'0')
        self.key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(self.key)

    def encrypt(self, text: str) -> str:
        """
        텍스트를 AES256으로 암호화

        Args:
            text: 암호화할 텍스트

        Returns:
            암호화된 텍스트 (base64 인코딩된 문자열)
        """
        encrypted = self.cipher.encrypt(text.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        AES256으로 암호화된 텍스트를 복호화

        Args:
            encrypted_text: 암호화된 텍스트

        Returns:
            복호화된 원본 텍스트
        """
        decrypted = self.cipher.decrypt(encrypted_text.encode())
        return decrypted.decode()

    @staticmethod
    def generate_key() -> str:
        """
        새로운 AES256 키 생성

        Returns:
            랜덤으로 생성된 32바이트 키 (base64 인코딩)
        """
        return Fernet.generate_key().decode()


# 전역 CryptoManager 인스턴스 (앱 시작시 환경변수에서 키 로드)
def get_crypto_manager():
    """
    CryptoManager 인스턴스를 반환합니다.
    환경변수 AES_KEY에서 키를 읽어옵니다.

    Returns:
        설정된 CryptoManager 인스턴스
    """
    key = os.getenv("AES_KEY")
    if not key:
        raise ValueError("AES_KEY environment variable is not set")
    return CryptoManager(key)
