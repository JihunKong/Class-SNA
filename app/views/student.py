"""
학생 참여 뷰
학급 코드 입력 → 이름 선택 → 설문 참여
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from app.models import db, Classroom, Student, SurveyResponse

student_bp = Blueprint('student', __name__)


@student_bp.route('/join', methods=['GET', 'POST'])
def join():
    """학급 참여 - 코드 입력 페이지"""
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()

        if not code:
            flash('학급 코드를 입력해주세요.', 'warning')
            return redirect(url_for('student.join'))

        # 학급 확인
        classroom = Classroom.query.filter_by(code=code, is_active=True).first()

        if not classroom:
            flash('유효하지 않은 학급 코드입니다.', 'error')
            return redirect(url_for('student.join'))

        if not classroom.survey_active:
            flash('현재 설문이 진행 중이 아닙니다. 선생님께 문의해주세요.', 'warning')
            return redirect(url_for('student.join'))

        # 이름 선택 페이지로 이동
        return redirect(url_for('student.select_name', code=code))

    return render_template('pages/join.html')


@student_bp.route('/join/<code>', methods=['GET'])
def select_name(code):
    """이름 선택 페이지"""
    classroom = Classroom.query.filter_by(code=code.upper(), is_active=True).first()

    if not classroom:
        flash('유효하지 않은 학급 코드입니다.', 'error')
        return redirect(url_for('student.join'))

    if not classroom.survey_active:
        flash('현재 설문이 진행 중이 아닙니다.', 'warning')
        return redirect(url_for('student.join'))

    # 아직 응답하지 않은 학생 목록
    students = classroom.students.order_by(Student.student_number, Student.name).all()
    available_students = [s for s in students if not s.has_responded]

    return render_template(
        'pages/select_name.html',
        classroom=classroom,
        students=available_students
    )


@student_bp.route('/join/<code>/select', methods=['POST'])
def confirm_selection(code):
    """이름 선택 확인 및 세션 설정"""
    classroom = Classroom.query.filter_by(code=code.upper(), is_active=True).first()

    if not classroom:
        return jsonify({'error': '유효하지 않은 학급 코드입니다.'}), 404

    student_id = request.form.get('student_id') or request.json.get('student_id')

    if not student_id:
        flash('이름을 선택해주세요.', 'warning')
        return redirect(url_for('student.select_name', code=code))

    student = Student.query.get(student_id)

    if not student or student.classroom_id != classroom.id:
        flash('유효하지 않은 선택입니다.', 'error')
        return redirect(url_for('student.select_name', code=code))

    if student.has_responded:
        flash('이미 응답을 완료한 학생입니다.', 'warning')
        return redirect(url_for('student.select_name', code=code))

    # 세션에 학생 정보 저장
    session['student_id'] = student.id
    session['student_name'] = student.name
    session['classroom_id'] = classroom.id
    session['classroom_code'] = classroom.code
    session['is_student'] = True

    flash(f'{student.name}님, 환영합니다!', 'success')

    # 설문 페이지로 이동
    return redirect(url_for('student.survey', code=code))


@student_bp.route('/join/<code>/survey', methods=['GET'])
def survey(code):
    """설문 페이지"""
    # 학생 세션 확인
    if not session.get('is_student') or session.get('classroom_code') != code.upper():
        flash('먼저 이름을 선택해주세요.', 'warning')
        return redirect(url_for('student.select_name', code=code))

    classroom = Classroom.query.filter_by(code=code.upper()).first()
    if not classroom:
        return redirect(url_for('student.join'))

    student = Student.query.get(session.get('student_id'))
    if not student:
        session.clear()
        return redirect(url_for('student.join'))

    # 이미 응답했는지 확인
    if student.has_responded:
        flash('이미 설문에 응답하셨습니다.', 'info')
        return redirect(url_for('student.complete', code=code))

    # 같은 학급의 다른 학생 목록 (자신 제외)
    other_students = classroom.students.filter(Student.id != student.id).order_by(
        Student.student_number, Student.name
    ).all()

    return render_template(
        'pages/survey.html',
        classroom=classroom,
        student=student,
        other_students=other_students
    )


@student_bp.route('/join/<code>/survey', methods=['POST'])
def submit_survey(code):
    """설문 제출"""
    # 학생 세션 확인
    if not session.get('is_student') or session.get('classroom_code') != code.upper():
        return jsonify({'error': '권한이 없습니다.'}), 403

    classroom = Classroom.query.filter_by(code=code.upper()).first()
    student = Student.query.get(session.get('student_id'))

    if not classroom or not student:
        return jsonify({'error': '잘못된 요청입니다.'}), 400

    # 이미 응답했는지 확인
    if student.has_responded:
        return jsonify({'error': '이미 응답하셨습니다.'}), 400

    # 응답 데이터 저장
    data = request.get_json() or request.form.to_dict(flat=False)

    response = SurveyResponse(
        classroom_id=classroom.id,
        student_id=student.id,
        responses=data,
        is_complete=True
    )
    db.session.add(response)
    db.session.commit()

    flash('설문이 완료되었습니다. 감사합니다!', 'success')

    # JSON 요청인 경우
    if request.is_json:
        return jsonify({
            'success': True,
            'message': '설문이 완료되었습니다.',
            'redirect': url_for('student.complete', code=code)
        })

    return redirect(url_for('student.complete', code=code))


@student_bp.route('/join/<code>/complete')
def complete(code):
    """설문 완료 페이지"""
    student_name = session.get('student_name', '학생')

    # 세션 정리
    session.pop('student_id', None)
    session.pop('student_name', None)
    session.pop('classroom_id', None)
    session.pop('classroom_code', None)
    session.pop('is_student', None)

    return render_template('pages/survey_complete.html', student_name=student_name)


@student_bp.route('/leave')
def leave():
    """학생 세션 종료"""
    session.pop('student_id', None)
    session.pop('student_name', None)
    session.pop('classroom_id', None)
    session.pop('classroom_code', None)
    session.pop('is_student', None)

    flash('종료되었습니다.', 'info')
    return redirect(url_for('views.index'))
