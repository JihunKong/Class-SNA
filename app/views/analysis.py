"""
분석 결과 페이지 라우트
"""
from flask import render_template, session, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask_babel import _

from app.views import views_bp
from app.models import Classroom, AnalysisResult


@views_bp.route('/analysis/classroom/<int:classroom_id>')
@login_required
def classroom_analysis(classroom_id):
    """학급 분석 결과 페이지 (새 DB 기반)"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        flash(_('권한이 없습니다.'), 'error')
        return redirect(url_for('views.teacher_dashboard'))

    # 분석 결과 조회
    result = AnalysisResult.query.filter_by(
        classroom_id=classroom_id
    ).order_by(AnalysisResult.created_at.desc()).first()

    if not result:
        flash(_('분석 결과가 없습니다. 먼저 분석을 실행해주세요.'), 'warning')
        return redirect(url_for('views.teacher_dashboard'))

    return render_template(
        'pages/analysis/classroom_result.html',
        classroom=classroom,
        result=result
    )


@views_bp.route('/analysis')
def analysis_dashboard():
    """분석 대시보드 (개요) - 레거시 지원"""
    if not session.get('analyzed'):
        flash(_('먼저 데이터를 업로드해주세요.'), 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/dashboard.html')


@views_bp.route('/analysis/network')
def analysis_network():
    """대화형 네트워크 시각화"""
    if not session.get('analyzed'):
        flash(_('먼저 데이터를 업로드해주세요.'), 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/network.html')


@views_bp.route('/analysis/centrality')
def analysis_centrality():
    """중심성 분석"""
    if not session.get('analyzed'):
        flash(_('먼저 데이터를 업로드해주세요.'), 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/centrality.html')


@views_bp.route('/analysis/groups')
def analysis_groups():
    """그룹(커뮤니티) 분석"""
    if not session.get('analyzed'):
        flash(_('먼저 데이터를 업로드해주세요.'), 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/groups.html')


@views_bp.route('/analysis/students')
def analysis_students():
    """학생별 분석"""
    if not session.get('analyzed'):
        flash(_('먼저 데이터를 업로드해주세요.'), 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/students.html')


@views_bp.route('/analysis/isolated')
def analysis_isolated():
    """고립 학생 분석"""
    if not session.get('analyzed'):
        flash(_('먼저 데이터를 업로드해주세요.'), 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/isolated.html')
