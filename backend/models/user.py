"""
SQLAlchemy 데이터베이스 모델
사용자 정보와 API 키 자격증명을 정의합니다.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os


Base = declarative_base()


class User(Base):
    """
    사용자 테이블
    Google OAuth로 로그인한 사용자 정보를 저장합니다.
    """
    __tablename__ = "users"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)

    # Google OAuth 정보
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=False)
    picture = Column(String)  # Google 프로필 사진 URL

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계설정: 사용자가 가진 모든 자격증명
    credentials = relationship("Credential", back_populates="user", cascade="all, delete-orphan")


class Credential(Base):
    """
    API 키 자격증명 테이블
    각 사용자의 서비스별 API 키를 암호화하여 저장합니다.
    """
    __tablename__ = "credentials"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)

    # 외래키: 사용자 ID
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # 서비스 정보
    service_name = Column(String, index=True, nullable=False)
    # 예: telegram, slack, gmail, drive, notion, n8n, gemini 등

    # 암호화된 API 키
    encrypted_key = Column(String, nullable=False)

    # 검증 상태
    is_verified = Column(Boolean, default=False)
    # API 키가 현재 유효한지 여부

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계설정: 이 자격증명이 속한 사용자
    user = relationship("User", back_populates="credentials")


# 데이터베이스 초기화 유틸리티
def init_db():
    """
    데이터베이스 테이블을 생성합니다.
    애플리케이션 시작시 호출해야 합니다.
    """
    database_url = os.getenv("DATABASE_URL", "sqlite:///./database.db")
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine


def get_db():
    """
    데이터베이스 세션을 반환합니다.
    FastAPI 의존성 주입에 사용됩니다.

    Yields:
        데이터베이스 세션
    """
    database_url = os.getenv("DATABASE_URL", "sqlite:///./database.db")
    engine = create_engine(database_url, connect_args={"check_same_thread": False} if "sqlite" in database_url else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
