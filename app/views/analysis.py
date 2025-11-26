"""
분석 결과 페이지 라우트
"""
from flask import render_template, session, redirect, url_for, flash

from app.views import views_bp


@views_bp.route('/analysis')
def analysis_dashboard():
    """분석 대시보드 (개요)"""
    if not session.get('analyzed'):
        flash('먼저 데이터를 업로드해주세요.', 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/dashboard.html')


@views_bp.route('/analysis/network')
def analysis_network():
    """대화형 네트워크 시각화"""
    if not session.get('analyzed'):
        flash('먼저 데이터를 업로드해주세요.', 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/network.html')


@views_bp.route('/analysis/centrality')
def analysis_centrality():
    """중심성 분석"""
    if not session.get('analyzed'):
        flash('먼저 데이터를 업로드해주세요.', 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/centrality.html')


@views_bp.route('/analysis/groups')
def analysis_groups():
    """그룹(커뮤니티) 분석"""
    if not session.get('analyzed'):
        flash('먼저 데이터를 업로드해주세요.', 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/groups.html')


@views_bp.route('/analysis/students')
def analysis_students():
    """학생별 분석"""
    if not session.get('analyzed'):
        flash('먼저 데이터를 업로드해주세요.', 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/students.html')


@views_bp.route('/analysis/isolated')
def analysis_isolated():
    """고립 학생 분석"""
    if not session.get('analyzed'):
        flash('먼저 데이터를 업로드해주세요.', 'warning')
        return redirect(url_for('views.upload'))
    return render_template('pages/analysis/isolated.html')
