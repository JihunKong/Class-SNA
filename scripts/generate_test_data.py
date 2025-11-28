#!/usr/bin/env python3
"""
테스트 데이터 생성 스크립트
22명 학생의 설문 응답을 포함한 테스트 학급 생성
"""
import random
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Teacher, Classroom, Student, SurveyResponse


def generate_test_data(num_students=22):
    """테스트 학급 생성 (22명 학생 + 설문 응답)"""

    # 환경 변수로 production/development 결정
    env = os.environ.get('FLASK_ENV', 'production')
    app = create_app(env)

    with app.app_context():
        # 기존 테스트 교사 찾기 또는 생성
        teacher = Teacher.query.filter_by(email='test@example.com').first()
        if not teacher:
            teacher = Teacher(
                google_id=f'test-{random.randint(10000, 99999)}',
                email='test@example.com',
                name='테스트 교사'
            )
            db.session.add(teacher)
            db.session.flush()
            print(f"새 교사 생성: {teacher.name} (ID: {teacher.id})")
        else:
            print(f"기존 교사 사용: {teacher.name} (ID: {teacher.id})")

        # 학급 생성
        classroom = Classroom(
            code=Classroom.generate_code(),
            name='테스트 학급 (22명)',
            description='SNA 분석 테스트용 - 회피 관계 포함',
            teacher_id=teacher.id,
            is_active=True,
            survey_active=True
        )
        db.session.add(classroom)
        db.session.flush()
        print(f"학급 생성: {classroom.name} (ID: {classroom.id}, 코드: {classroom.code})")

        # 22명 학생 생성 (한국식 이름)
        names = [
            '김철수', '이영희', '박민호', '정수진', '이준호',
            '최지은', '강민지', '신동준', '윤미영', '임준석',
            '홍기철', '서진희', '김솔미', '박준표', '이경호',
            '정원석', '최은정', '강준영', '신윤희', '윤태원',
            '임수연', '홍서영'
        ][:num_students]

        students = []
        for idx, name in enumerate(names, 1):
            student = Student(
                name=name,
                student_number=idx,
                classroom_id=classroom.id
            )
            students.append(student)
            db.session.add(student)

        db.session.flush()
        print(f"학생 {len(students)}명 생성 완료")

        # 설문 응답 생성 (22명 전원)
        avoidance_count = 0
        for respondent in students:
            peers = [s for s in students if s.id != respondent.id]

            # 무작위로 관계 선택 (현실적인 분포)
            num_friends = random.randint(3, 5)
            num_helpers = random.randint(1, 3)
            num_teammates = random.randint(1, 3)
            num_leaders = random.randint(1, 3)
            num_trust = random.randint(1, 3)
            num_comm = random.randint(1, 3)
            num_avoid = random.randint(0, 2)  # 0~2명 회피

            responses = {
                'friends': [str(s.id) for s in random.sample(peers, num_friends)],
                'helpers': [str(s.id) for s in random.sample(peers, num_helpers)],
                'teammates': [str(s.id) for s in random.sample(peers, num_teammates)],
                'leaders': [str(s.id) for s in random.sample(peers, num_leaders)],
                'trust': [str(s.id) for s in random.sample(peers, num_trust)],
                'communication': [str(s.id) for s in random.sample(peers, num_comm)],
                'avoidance': [str(s.id) for s in random.sample(peers, num_avoid)]
            }

            if num_avoid > 0:
                avoidance_count += num_avoid

            survey = SurveyResponse(
                classroom_id=classroom.id,
                student_id=respondent.id,
                responses=responses,
                is_complete=True
            )
            db.session.add(survey)

        db.session.commit()

        print()
        print("=" * 50)
        print("테스트 데이터 생성 완료!")
        print("=" * 50)
        print(f"  학급 ID: {classroom.id}")
        print(f"  학급 코드: {classroom.code}")
        print(f"  학생 수: {len(students)}명")
        print(f"  설문 응답: {len(students)}건")
        print(f"  회피 관계: {avoidance_count}건 (음수 가중치 테스트)")
        print("=" * 50)
        print()
        print("분석 테스트 방법:")
        print(f"  curl -X POST https://xn--989ale.xn--oj4b21j.com/api/v1/classroom/{classroom.id}/analyze")
        print()

        return classroom.id


if __name__ == '__main__':
    classroom_id = generate_test_data()
