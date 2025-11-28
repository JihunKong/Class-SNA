"""
Flask Application Factory
Class-SNA v2.0 - 학급 관계 네트워크 분석 시스템
"""
import os
from flask import Flask, request
from flask_cors import CORS
from flask_session import Session
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_babel import Babel, get_locale as babel_get_locale

from app.config import config_by_name
from app.models import db, Teacher

# Flask-Login 초기화
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '로그인이 필요합니다.'
login_manager.login_message_category = 'warning'

# Flask-Migrate 초기화
migrate = Migrate()

# Flask-Babel 초기화
babel = Babel()


def get_locale():
    """사용자 언어 설정 결정"""
    # 1. 쿠키에서 언어 확인
    locale = request.cookies.get('locale')
    if locale in ['ko', 'en']:
        return locale
    # 2. 브라우저 언어 감지
    return request.accept_languages.best_match(['ko', 'en'], default='ko')


@login_manager.user_loader
def load_user(user_id):
    """세션에서 사용자 로드"""
    return Teacher.query.get(int(user_id))


def create_app(config_name=None):
    """Flask 애플리케이션 팩토리"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # 확장 초기화
    init_extensions(app)

    # Blueprint 등록
    register_blueprints(app)

    # 에러 핸들러 등록
    register_error_handlers(app)

    # 데이터베이스 테이블 생성
    with app.app_context():
        db.create_all()

    return app


def init_extensions(app):
    """Flask 확장 초기화"""
    # 데이터베이스 초기화
    db.init_app(app)
    migrate.init_app(app, db)

    # 로그인 매니저 초기화
    login_manager.init_app(app)

    # i18n (Flask-Babel) 초기화
    babel.init_app(app, locale_selector=get_locale)

    # 템플릿에 get_locale 함수 제공
    @app.context_processor
    def inject_locale():
        return {'get_locale': babel_get_locale}

    # OAuth 초기화
    from app.views.auth import init_oauth
    init_oauth(app)

    # CORS 설정
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "DELETE", "PUT", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Redis 세션 설정
    if app.config.get('SESSION_TYPE') == 'redis':
        import redis
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        app.config['SESSION_REDIS'] = redis.from_url(redis_url)

    # 세션 설정
    Session(app)


def register_blueprints(app):
    """Blueprint 등록"""
    from app.views import views_bp
    from app.views.auth import auth_bp
    from app.views.student import student_bp
    from app.views.admin import admin_bp
    from app.api import api_bp
    from app.api.classroom import classroom_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(classroom_bp, url_prefix='/api/v1/classroom')


def register_error_handlers(app):
    """에러 핸들러 등록"""
    from flask import jsonify, render_template

    @app.errorhandler(404)
    def not_found_error(error):
        if _wants_json_response():
            return jsonify({'error': 'Not found'}), 404
        return render_template('pages/errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        if _wants_json_response():
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('pages/errors/500.html'), 500


def _wants_json_response():
    """JSON 응답이 필요한지 확인"""
    from flask import request
    return request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
