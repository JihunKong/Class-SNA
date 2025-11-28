"""
관리자 대시보드 뷰
Admin Dashboard for Class-SNA
"""
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, abort, jsonify, current_app
from flask_login import login_required, current_user
from flask_babel import _

from app.models import db, Teacher, Classroom, Student, SurveyResponse, AnalysisResult

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """관리자 권한 필요 데코레이터"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    """관리자 대시보드 메인 페이지"""
    now = datetime.utcnow()

    # 기본 통계
    stats = {
        'total_teachers': Teacher.query.count(),
        'active_teachers_7d': Teacher.query.filter(
            Teacher.last_login >= now - timedelta(days=7)
        ).count(),
        'active_teachers_30d': Teacher.query.filter(
            Teacher.last_login >= now - timedelta(days=30)
        ).count(),
        'total_classrooms': Classroom.query.count(),
        'active_classrooms': Classroom.query.filter_by(is_active=True).count(),
        'total_students': Student.query.count(),
        'total_responses': SurveyResponse.query.filter_by(is_complete=True).count(),
        'total_analyses': AnalysisResult.query.count(),
    }

    # 설문 완료율
    if stats['total_students'] > 0:
        stats['response_rate'] = round(
            (stats['total_responses'] / stats['total_students']) * 100, 1
        )
    else:
        stats['response_rate'] = 0

    # 학급당 평균 학생 수
    if stats['total_classrooms'] > 0:
        stats['avg_students_per_class'] = round(
            stats['total_students'] / stats['total_classrooms'], 1
        )
    else:
        stats['avg_students_per_class'] = 0

    # 최근 가입 교사 목록 (최근 20명)
    recent_teachers = Teacher.query.order_by(
        Teacher.created_at.desc()
    ).limit(20).all()

    # 일별 가입자 수 (최근 30일)
    daily_signups = []
    for i in range(30):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        count = Teacher.query.filter(
            Teacher.created_at >= date_start,
            Teacher.created_at < date_end
        ).count()
        daily_signups.append({
            'date': date_start.strftime('%Y-%m-%d'),
            'count': count
        })
    daily_signups.reverse()

    # 일별 활성 사용자 (최근 30일)
    daily_active = []
    for i in range(30):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        count = Teacher.query.filter(
            Teacher.last_login >= date_start,
            Teacher.last_login < date_end
        ).count()
        daily_active.append({
            'date': date_start.strftime('%Y-%m-%d'),
            'count': count
        })
    daily_active.reverse()

    return render_template('pages/admin/dashboard.html',
                           stats=stats,
                           teachers=recent_teachers,
                           daily_signups=daily_signups,
                           daily_active=daily_active)


@admin_bp.route('/teachers')
@admin_required
def teachers_list():
    """전체 교사 목록"""
    now = datetime.utcnow()
    teachers = Teacher.query.order_by(Teacher.created_at.desc()).all()
    return render_template('pages/admin/teachers.html', teachers=teachers, now=now)


@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """통계 API (JSON)"""
    now = datetime.utcnow()

    stats = {
        'total_teachers': Teacher.query.count(),
        'active_teachers_7d': Teacher.query.filter(
            Teacher.last_login >= now - timedelta(days=7)
        ).count(),
        'total_classrooms': Classroom.query.count(),
        'total_students': Student.query.count(),
        'total_responses': SurveyResponse.query.filter_by(is_complete=True).count(),
    }

    return jsonify(stats)
