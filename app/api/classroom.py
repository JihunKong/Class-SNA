"""
학급 관리 API
교사가 학급 생성, 학생 명단 관리
"""
from flask import Blueprint, request, jsonify, Response, current_app
from flask_login import login_required, current_user
import pandas as pd
import numpy as np
import io
import json

from sqlalchemy.exc import IntegrityError
from app.models import db, Classroom, Student, SurveyResponse


class NumpyEncoder(json.JSONEncoder):
    """numpy 타입을 JSON 직렬화 가능하게 변환"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def json_response(data, status=200):
    """UTF-8 인코딩이 보장된 JSON 응답 생성"""
    return Response(
        json.dumps(data, ensure_ascii=False, cls=NumpyEncoder),
        status=status,
        mimetype='application/json; charset=utf-8'
    )

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
    try:
        classroom = Classroom.query.get_or_404(classroom_id)

        # 권한 확인
        if classroom.teacher_id != current_user.id:
            return json_response({'error': '권한이 없습니다.'}, 403)

        # 학생 목록 조회 (서브쿼리로 응답 여부 확인 - N+1 문제 해결)
        from sqlalchemy import exists

        responded_subquery = db.session.query(SurveyResponse.student_id).filter(
            SurveyResponse.is_complete == True
        ).subquery()

        students = db.session.query(
            Student.id,
            Student.name,
            Student.student_number,
            exists().where(Student.id == responded_subquery.c.student_id).label('has_responded')
        ).filter(
            Student.classroom_id == classroom_id
        ).order_by(
            Student.student_number.nulls_last(),
            Student.name
        ).all()

        # 결과 변환
        student_list = [{
            'id': s.id,
            'name': s.name,
            'student_number': s.student_number,
            'has_responded': s.has_responded
        } for s in students]

        return json_response({
            'students': student_list,
            'total': len(student_list)
        })

    except Exception as e:
        current_app.logger.error(f'학생 목록 조회 오류: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return json_response({'error': '학생 목록을 불러오는 중 오류가 발생했습니다.', 'detail': str(e)}, 500)


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

    try:
        db.session.delete(student)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '학생이 삭제되었습니다.'
        })
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': '학생 데이터 삭제 중 오류가 발생했습니다.'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'학생 삭제 오류: {str(e)}')
        return jsonify({'error': '학생 삭제 중 오류가 발생했습니다.'}), 500


@classroom_bp.route('/<int:classroom_id>/students/<int:student_id>/reset-response', methods=['POST'])
@login_required
def reset_student_response(classroom_id, student_id):
    """학생 설문 응답 초기화"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403

    student = Student.query.get_or_404(student_id)
    if student.classroom_id != classroom_id:
        return jsonify({'error': '해당 학급의 학생이 아닙니다.'}), 400

    try:
        # 학생의 설문 응답 삭제
        deleted_count = SurveyResponse.query.filter_by(
            classroom_id=classroom_id,
            student_id=student_id
        ).delete()

        db.session.commit()

        if deleted_count > 0:
            return jsonify({
                'success': True,
                'message': f'{student.name} 학생의 응답이 초기화되었습니다.'
            })
        else:
            return jsonify({
                'success': True,
                'message': '초기화할 응답이 없습니다.'
            })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'응답 초기화 오류: {str(e)}')
        return jsonify({'error': '응답 초기화 중 오류가 발생했습니다.'}), 500


@classroom_bp.route('/<code>/students/available', methods=['GET'])
def get_available_students(code):
    """학급 코드로 응답 가능한 학생 목록 조회 (학생 참여용)"""
    classroom = Classroom.query.filter_by(code=code.upper(), is_active=True).first()

    if not classroom:
        return json_response({'error': '학급을 찾을 수 없습니다.'}, 404)

    if not classroom.survey_active:
        return json_response({'error': '현재 설문이 비활성화되어 있습니다.'}, 400)

    # 아직 응답하지 않은 학생 목록
    students = classroom.students.order_by(Student.student_number, Student.name).all()
    available = [s.to_dict() for s in students if not s.has_responded]

    return json_response({
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


@classroom_bp.route('/<int:classroom_id>/analyze', methods=['POST'])
@login_required
def analyze_classroom(classroom_id):
    """학급 설문 응답 분석 실행"""
    from app.services.classroom_analyzer import ClassroomAnalyzer
    from app.services.api_manager import APIManager

    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return json_response({'error': '권한이 없습니다.'}, 403)

    try:
        # API 매니저 초기화 (AI 해석용)
        api_manager = None
        try:
            api_manager = APIManager()
        except Exception as e:
            current_app.logger.warning(f"API 매니저 초기화 실패, 기본 해석 사용: {str(e)}")

        # 분석 실행
        result = ClassroomAnalyzer.run_analysis(classroom_id, api_manager)

        return json_response({
            'success': True,
            'message': '분석이 완료되었습니다.',
            **result
        })

    except ValueError as e:
        return json_response({'error': str(e)}, 400)
    except Exception as e:
        current_app.logger.error(f"분석 오류: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return json_response({'error': f'분석 중 오류가 발생했습니다: {str(e)}'}, 500)


@classroom_bp.route('/<int:classroom_id>/analysis', methods=['GET'])
@login_required
def get_analysis_result(classroom_id):
    """저장된 분석 결과 조회"""
    from app.models import AnalysisResult

    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return json_response({'error': '권한이 없습니다.'}, 403)

    # 최신 분석 결과 조회
    result = AnalysisResult.query.filter_by(
        classroom_id=classroom_id
    ).order_by(AnalysisResult.created_at.desc()).first()

    if not result:
        return json_response({
            'exists': False,
            'message': '분석 결과가 없습니다. 먼저 분석을 실행해주세요.'
        })

    return json_response({
        'exists': True,
        'classroom_id': classroom_id,
        'classroom_name': classroom.name,
        'network_data': result.network_data,
        'metrics': result.metrics,
        'communities': result.communities,
        'created_at': result.created_at.isoformat() if result.created_at else None
    })


@classroom_bp.route('/<int:classroom_id>/analysis/layer/<layer_type>', methods=['GET'])
@login_required
def get_layer_analysis(classroom_id, layer_type):
    """특정 레이어의 분석 결과 조회"""
    from app.services.classroom_analyzer import ClassroomAnalyzer

    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return json_response({'error': '권한이 없습니다.'}, 403)

    try:
        result = ClassroomAnalyzer.get_layer_analysis(classroom_id, layer_type)
        return json_response({
            'success': True,
            'layer_type': layer_type,
            **result
        })
    except ValueError as e:
        return json_response({'error': str(e)}, 400)
    except Exception as e:
        current_app.logger.error(f"레이어 분석 오류: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return json_response({'error': f'분석 중 오류가 발생했습니다: {str(e)}'}, 500)


@classroom_bp.route('/<int:classroom_id>/warnings/avoidance', methods=['GET'])
@login_required
def get_avoidance_warnings(classroom_id):
    """회피 관계 경고 조회"""
    from app.services.classroom_analyzer import ClassroomAnalyzer

    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return json_response({'error': '권한이 없습니다.'}, 403)

    try:
        result = ClassroomAnalyzer.get_avoidance_warnings(classroom_id)
        return json_response({
            'success': True,
            'classroom_id': classroom_id,
            'classroom_name': classroom.name,
            **result
        })
    except ValueError as e:
        return json_response({'error': str(e)}, 400)
    except Exception as e:
        current_app.logger.error(f"회피 경고 분석 오류: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return json_response({'error': f'분석 중 오류가 발생했습니다: {str(e)}'}, 500)


@classroom_bp.route('/<int:classroom_id>/student/<name>/profile', methods=['GET'])
@login_required
def get_student_multilayer_profile(classroom_id, name):
    """학생의 다층 네트워크 프로필 조회"""
    from app.services.classroom_analyzer import ClassroomAnalyzer
    from urllib.parse import unquote

    classroom = Classroom.query.get_or_404(classroom_id)

    # 권한 확인
    if classroom.teacher_id != current_user.id:
        return json_response({'error': '권한이 없습니다.'}, 403)

    try:
        # URL 디코딩
        student_name = unquote(name)
        result = ClassroomAnalyzer.get_student_profile(classroom_id, student_name)
        return json_response({
            'success': True,
            'classroom_id': classroom_id,
            'student_name': student_name,
            **result
        })
    except ValueError as e:
        return json_response({'error': str(e)}, 400)
    except Exception as e:
        current_app.logger.error(f"학생 프로필 조회 오류: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return json_response({'error': f'프로필 조회 중 오류가 발생했습니다: {str(e)}'}, 500)
