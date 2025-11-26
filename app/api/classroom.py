"""
학급 관리 API
교사가 학급 생성, 학생 명단 관리
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import pandas as pd
import io

from app.models import db, Classroom, Student, SurveyResponse

classroom_bp = Blueprint('classroom', __name__)


@classroom_bp.route('', methods=['GET'])
@login_required
def list_classrooms():
    """교사의 학급 목록 조회"""
    classrooms = current_user.classrooms.order_by(Classroom.created_at.desc()).all()
    return jsonify({
        'classrooms': [c.to_dict() for c in classrooms]
    })


@classroom_bp.route('', methods=['POST'])
@login_required
def create_classroom():
    """새 학급 생성"""
    data = request.get_json()

    name = data.get('name')
    if not name:
        return jsonify({'error': '학급 이름을 입력해주세요.'}), 400

    # 학급 코드 생성 (혼동 문자 제외)
    code = Classroom.generate_code()

    classroom = Classroom(
        code=code,
        name=name,
        description=data.get('description', ''),
        teacher_id=current_user.id
    )
    db.session.add(classroom)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '학급이 생성되었습니다.',
        'classroom': classroom.to_dict()
    }), 201


@classroom_bp.route('/<code>', methods=['GET'])
def get_classroom(code):
    """학급 정보 조회 (공개 - 학생 참여용)"""
    classroom = Classroom.query.filter_by(code=code.upper(), is_active=True).first()

    if not classroom:
        return jsonify({'error': '학급을 찾을 수 없습니다.'}), 404

    return jsonify({
        'id': classroom.id,
        'code': classroom.code,
        'name': classroom.name,
        'survey_active': classroom.survey_active
    })


@classroom_bp.route('/<int:classroom_id>', methods=['PUT'])
@login_required
def update_classroom(classroom_id):
    """학급 정보 수정"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    data = request.get_json()

    if 'name' in data:
        classroom.name = data['name']
    if 'description' in data:
        classroom.description = data['description']
    if 'is_active' in data:
        classroom.is_active = data['is_active']
    if 'survey_active' in data:
        classroom.survey_active = data['survey_active']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '학급 정보가 수정되었습니다.',
        'classroom': classroom.to_dict()
    })


@classroom_bp.route('/<int:classroom_id>', methods=['DELETE'])
@login_required
def delete_classroom(classroom_id):
    """학급 삭제"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    db.session.delete(classroom)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '학급이 삭제되었습니다.'
    })


@classroom_bp.route('/<int:classroom_id>/students', methods=['GET'])
@login_required
def list_students(classroom_id):
    """학급 학생 목록 조회"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    students = classroom.students.order_by(Student.student_number, Student.name).all()

    return jsonify({
        'students': [s.to_dict() for s in students],
        'total': len(students)
    })


@classroom_bp.route('/<int:classroom_id>/students', methods=['POST'])
@login_required
def add_students(classroom_id):
    """학생 명단 추가 (단일 또는 다수)"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    data = request.get_json()
    students_data = data.get('students', [])

    if not students_data:
        return jsonify({'error': '학생 정보가 없습니다.'}), 400

    added = 0
    skipped = 0

    for student_info in students_data:
        name = student_info.get('name', '').strip()
        if not name:
            continue

        # 중복 확인
        existing = Student.query.filter_by(
            classroom_id=classroom_id,
            name=name
        ).first()

        if existing:
            skipped += 1
            continue

        student = Student(
            name=name,
            student_number=student_info.get('student_number'),
            classroom_id=classroom_id
        )
        db.session.add(student)
        added += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{added}명의 학생이 추가되었습니다. (중복 {skipped}명 제외)',
        'added': added,
        'skipped': skipped
    })


@classroom_bp.route('/<int:classroom_id>/students/upload', methods=['POST'])
@login_required
def upload_students(classroom_id):
    """학생 명단 파일 업로드 (CSV/Excel)"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    filename = file.filename.lower()
    file_content = file.read()

    try:
        # 파일 형식에 따라 읽기
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_content), encoding='cp949')
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            return jsonify({'error': 'CSV 또는 Excel 파일만 지원합니다.'}), 400

        # 열 이름 찾기
        name_col = None
        number_col = None

        for col in df.columns:
            col_lower = str(col).lower()
            if '이름' in col_lower or 'name' in col_lower:
                name_col = col
            elif '번호' in col_lower or 'number' in col_lower:
                number_col = col

        # 이름 열이 없으면 첫 번째 열 사용
        if name_col is None:
            name_col = df.columns[0]

        added = 0
        skipped = 0

        for idx, row in df.iterrows():
            name = str(row[name_col]).strip()
            if not name or name == 'nan':
                continue

            # 중복 확인
            existing = Student.query.filter_by(
                classroom_id=classroom_id,
                name=name
            ).first()

            if existing:
                skipped += 1
                continue

            student_number = None
            if number_col and pd.notna(row.get(number_col)):
                try:
                    student_number = int(row[number_col])
                except (ValueError, TypeError):
                    pass

            student = Student(
                name=name,
                student_number=student_number,
                classroom_id=classroom_id
            )
            db.session.add(student)
            added += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{added}명의 학생이 추가되었습니다. (중복 {skipped}명 제외)',
            'added': added,
            'skipped': skipped
        })

    except Exception as e:
        return jsonify({'error': f'파일 처리 중 오류: {str(e)}'}), 400


@classroom_bp.route('/<int:classroom_id>/students/<int:student_id>', methods=['DELETE'])
@login_required
def delete_student(classroom_id, student_id):
    """학생 삭제"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    student = Student.query.get_or_404(student_id)
    if student.classroom_id != classroom_id:
        return jsonify({'error': '해당 학급의 학생이 아닙니다.'}), 400

    db.session.delete(student)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '학생이 삭제되었습니다.'
    })


@classroom_bp.route('/<code>/students/available', methods=['GET'])
def get_available_students(code):
    """학급 코드로 응답 가능한 학생 목록 조회 (학생 참여용)"""
    classroom = Classroom.query.filter_by(code=code.upper(), is_active=True).first()

    if not classroom:
        return jsonify({'error': '학급을 찾을 수 없습니다.'}), 404

    if not classroom.survey_active:
        return jsonify({'error': '현재 설문이 비활성화되어 있습니다.'}), 400

    # 아직 응답하지 않은 학생 목록
    students = classroom.students.order_by(Student.student_number, Student.name).all()
    available = [s.to_dict() for s in students if not s.has_responded]

    return jsonify({
        'classroom_name': classroom.name,
        'students': available,
        'total': len(available)
    })


@classroom_bp.route('/<int:classroom_id>/survey/toggle', methods=['POST'])
@login_required
def toggle_survey(classroom_id):
    """설문 활성화/비활성화 토글"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    classroom.survey_active = not classroom.survey_active
    db.session.commit()

    status = '활성화' if classroom.survey_active else '비활성화'
    return jsonify({
        'success': True,
        'message': f'설문이 {status}되었습니다.',
        'survey_active': classroom.survey_active
    })
