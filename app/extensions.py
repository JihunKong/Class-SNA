"""
Flask 확장 초기화
Class-SNA v2.0
"""
import os
import redis
from flask_caching import Cache

# 캐시 인스턴스
cache = Cache()


def get_redis_client():
    """Redis 클라이언트 반환"""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url)


def init_cache(app):
    """캐시 초기화"""
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'simple'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 3600)
    }

    if cache_config['CACHE_TYPE'] == 'redis':
        cache_config['CACHE_REDIS_URL'] = app.config.get('REDIS_URL')

    cache.init_app(app, config=cache_config)
