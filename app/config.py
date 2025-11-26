"""
Flask 애플리케이션 설정
Class-SNA v2.0
"""
import os
from datetime import timedelta


class Config:
    """기본 설정"""
    # Flask 기본
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 세션 설정
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'class-sna:'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # 데이터베이스 (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://sna_user:sna_password@localhost:5432/class_sna'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

    # 파일 업로드
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

    # Google API (Gemini 등)
    GOOGLE_API_KEYS = os.environ.get('GOOGLE_API_KEYS', '').split(',')
    GEMINI_MODEL = 'gemini-2.0-flash'

    # 애플리케이션 설정
    APP_NAME = '학급 관계 네트워크 분석 시스템 (Class-SNA)'
    APP_VERSION = '2.0.0'

    # 캐싱
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 3600  # 1시간

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True

    # Redis (로컬)
    SESSION_REDIS = None  # 자동 연결
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # 캐싱 (개발에서는 간단하게)
    CACHE_TYPE = 'simple'


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

    # 데이터베이스 (Docker 환경)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://sna_user:sna_password@db:5432/class_sna'
    )

    # 보안 설정
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CORS (프로덕션에서는 특정 도메인만)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://관계.성장.com')


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    SESSION_TYPE = 'filesystem'
    CACHE_TYPE = 'simple'


# 환경별 설정 매핑
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
