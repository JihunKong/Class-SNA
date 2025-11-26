"""
Google OAuth 2.0 인증 모듈
교사 로그인용
"""
import json
import requests
from flask import Blueprint, redirect, url_for, session, flash, current_app, request
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth

from app.models import db, Teacher

auth_bp = Blueprint('auth', __name__)

# OAuth 클라이언트
oauth = OAuth()


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


@auth_bp.route('/login')
def login():
    """Google OAuth 로그인 시작"""
    if current_user.is_authenticated:
        return redirect(url_for('views.teacher_dashboard'))

    # OAuth 콜백 URL
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


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
            flash('Google 계정 정보를 가져올 수 없습니다.', 'error')
            return redirect(url_for('views.index'))

        # 기존 사용자 확인 또는 새 사용자 생성
        teacher = Teacher.query.filter_by(google_id=google_id).first()

        if not teacher:
            # 새 교사 등록
            teacher = Teacher(
                google_id=google_id,
                email=email,
                name=name,
                profile_picture=picture
            )
            db.session.add(teacher)
            db.session.commit()
            flash(f'환영합니다, {name}님! 계정이 생성되었습니다.', 'success')
        else:
            # 기존 사용자 정보 업데이트
            teacher.name = name
            teacher.profile_picture = picture
            db.session.commit()
            flash(f'안녕하세요, {name}님!', 'success')

        # Flask-Login으로 로그인
        login_user(teacher, remember=True)

        # 원래 가려던 페이지로 리다이렉트
        next_page = session.pop('next', None)
        if next_page:
            return redirect(next_page)

        return redirect(url_for('views.teacher_dashboard'))

    except Exception as e:
        current_app.logger.error(f'OAuth 콜백 오류: {str(e)}')
        flash('로그인 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('views.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    """로그아웃"""
    logout_user()
    flash('로그아웃되었습니다.', 'info')
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
