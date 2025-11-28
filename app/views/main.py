"""
메인 페이지 라우트
"""
from flask import render_template, redirect, url_for, request, session, flash, make_response, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

from app.views import views_bp


@views_bp.route('/set-language/<lang>')
def set_language(lang):
    """언어 설정 변경"""
    supported = current_app.config.get('BABEL_SUPPORTED_LOCALES', ['ko', 'en'])
    if lang not in supported:
        lang = 'ko'

    # 이전 페이지로 리다이렉트
    referrer = request.referrer or url_for('views.index')
    response = make_response(redirect(referrer))
    # 1년간 쿠키 유지
    response.set_cookie('locale', lang, max_age=365*24*60*60, httponly=False, samesite='Lax')
    return response


@views_bp.route('/')
def index():
    """메인 페이지 (랜딩)"""
    return render_template('pages/index.html')


@views_bp.route('/teacher')
@login_required
def teacher_dashboard():
    """교사 대시보드 - 학급 관리"""
    classrooms = current_user.classrooms.order_by_field('-created_at').all() if hasattr(current_user.classrooms, 'order_by_field') else current_user.classrooms.all()
    return render_template('pages/teacher_dashboard.html', classrooms=classrooms)


@views_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """데이터 업로드 페이지"""
    if request.method == 'POST':
        # 파일 업로드 처리
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # 파일 저장 로직은 API에서 처리
                return redirect(url_for('api.data.upload_file'))

        # Google Sheets URL 처리
        sheet_url = request.form.get('sheet_url')
        if sheet_url:
            session['sheet_url'] = sheet_url
            return redirect(url_for('views.analysis_dashboard'))

    return render_template('pages/upload.html')


@views_bp.route('/health')
def health_check():
    """헬스 체크 엔드포인트"""
    return {'status': 'healthy', 'version': '2.0.0'}


# ===== Legal 페이지 =====
@views_bp.route('/legal/privacy')
def privacy_policy():
    """개인정보 처리방침"""
    return render_template('pages/legal/privacy.html')


@views_bp.route('/legal/terms')
def terms_of_service():
    """이용약관"""
    return render_template('pages/legal/terms.html')


@views_bp.route('/legal/consent')
def consent_form():
    """동의서 다운로드"""
    return render_template('pages/legal/consent.html')
