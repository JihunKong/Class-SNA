"""
Google OAuth 2.0 인증 모듈
교사 로그인용
"""
import json
import requests
from flask import Blueprint, redirect, url_for, session, flash, current_app, request, render_template
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import _
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import MismatchingStateError

from datetime import datetime
from app.models import db, Teacher

auth_bp = Blueprint('auth', __name__)

# OAuth 클라이언트
oauth = OAuth()

# 교사 가입 코드
TEACHER_REGISTRATION_CODE = 'classapphub.com'


def init_oauth(app):
    """OAuth 초기화 - app context에서 호출"""
    oauth.init_app(app)

    # Google OAuth 등록
    if app.config.get('GOOGLE_CLIENT_ID'):
        oauth.register(
            name='google',
            client_id=app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
            server_metadata_url=app.config.get('GOOGLE_DISCOVERY_URL'),
            client_kwargs={
                'scope': 'openid email profile'
            }
        )


def _start_oauth():
    """OAuth 인증 시작 (내부 헬퍼 함수)"""
    # OAuth 콜백 URL - 프로덕션에서는 도메인 사용
    if not current_app.debug:
        # 도메인 기반 콜백 URL (프로덕션)
        redirect_uri = 'https://class-sna.com/auth/callback'
    else:
        redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/login')
def login():
    """Google OAuth 로그인 시작"""
    if current_user.is_authenticated:
        return redirect(url_for('views.teacher_dashboard'))

    # 이전에 성공적으로 로그인한 적이 있으면 코드 검증 스킵
    if request.cookies.get('teacher_verified') == 'true':
        return _start_oauth()

    # 이미 코드 검증을 완료했으면 바로 OAuth로
    if session.get('teacher_code_verified'):
        return _start_oauth()

    # 코드 검증 페이지로 이동
    return render_template('pages/teacher_verify.html')


@auth_bp.route('/verify-code', methods=['POST'])
def verify_code():
    """교사 가입 코드 검증"""
    code = request.form.get('code', '').strip()

    if code != TEACHER_REGISTRATION_CODE:
        flash(_('유효하지 않은 가입 코드입니다.'), 'error')
        return redirect(url_for('auth.login'))

    # 코드 검증 성공 - 세션에 저장
    session['teacher_code_verified'] = True

    # OAuth 로그인 시작
    return _start_oauth()


@auth_bp.route('/callback')
def callback():
    """Google OAuth 콜백 처리"""
    try:
        # 토큰 교환
        token = oauth.google.authorize_access_token()

        # 사용자 정보 가져오기
        user_info = token.get('userinfo')
        if not user_info:
            # userinfo가 없으면 직접 요청
            resp = oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo')
            user_info = resp.json()

        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        if not google_id or not email:
            flash(_('Google 계정 정보를 가져올 수 없습니다.'), 'error')
            return redirect(url_for('views.index'))

        # 기존 사용자 확인 또는 새 사용자 생성
        teacher = Teacher.query.filter_by(google_id=google_id).first()

        if not teacher:
            # 새 교사 등록
            teacher = Teacher(
                google_id=google_id,
                email=email,
                name=name,
                profile_picture=picture,
                last_login=datetime.utcnow()
            )
            db.session.add(teacher)
            db.session.commit()
            flash(_('환영합니다, %(name)s님! 계정이 생성되었습니다.', name=name), 'success')
        else:
            # 기존 사용자 정보 업데이트
            teacher.name = name
            teacher.profile_picture = picture
            teacher.last_login = datetime.utcnow()
            db.session.commit()
            flash(_('안녕하세요, %(name)s님!', name=name), 'success')

        # Flask-Login으로 로그인
        login_user(teacher, remember=True)

        # 인증 세션 정리
        session.pop('teacher_code_verified', None)

        # 쿠키와 함께 리다이렉트 (로그인 성공 표시)
        next_page = session.pop('next', None)
        target = next_page if next_page else url_for('views.teacher_dashboard')
        response = redirect(target)
        response.set_cookie('teacher_verified', 'true', max_age=365*24*60*60, httponly=True, secure=True, samesite='Lax')
        return response

    except MismatchingStateError:
        # OAuth state 불일치 - 자동으로 로그인 재시도
        current_app.logger.warning('OAuth state mismatch - 로그인 재시도')
        return redirect(url_for('auth.login'))

    except Exception as e:
        current_app.logger.error(f'OAuth 콜백 오류: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(_('로그인 중 오류가 발생했습니다.'), 'error')
        return redirect(url_for('views.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    """로그아웃"""
    logout_user()
    flash(_('로그아웃되었습니다.'), 'info')
    return redirect(url_for('views.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """현재 로그인한 사용자 정보"""
    return {
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'profile_picture': current_user.profile_picture
    }
