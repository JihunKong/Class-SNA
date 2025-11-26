"""
메인 페이지 라우트
"""
from flask import render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

from app.views import views_bp


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
