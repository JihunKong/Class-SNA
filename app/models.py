"""
데이터베이스 모델
Class-SNA 학급 관계 분석 시스템
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import secrets

db = SQLAlchemy()

# 학급 코드 생성용 문자 (혼동되기 쉬운 문자 제외: 0, O, 1, l, I)
CLASSROOM_CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


class Teacher(UserMixin, db.Model):
    """교사 모델 - Google OAuth로 인증"""
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(500))
    is_admin = db.Column(db.Boolean, default=False)  # 관리자 여부
    last_login = db.Column(db.DateTime)  # 마지막 로그인 시간
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    classrooms = db.relationship('Classroom', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Teacher {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'profile_picture': self.profile_picture,
            'is_admin': self.is_admin,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'classroom_count': self.classrooms.count()
        }


class Classroom(db.Model):
    """학급 모델"""
    __tablename__ = 'classrooms'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    survey_active = db.Column(db.Boolean, default=False)  # 설문 활성화 여부

    # 관계
    students = db.relationship('Student', backref='classroom', lazy='dynamic', cascade='all, delete-orphan')
    surveys = db.relationship('SurveyResponse', backref='classroom', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Classroom {self.name} ({self.code})>'

    @staticmethod
    def generate_code():
        """6자리 학급 코드 생성 (혼동되기 쉬운 문자 제외)"""
        while True:
            code = ''.join(secrets.choice(CLASSROOM_CODE_CHARS) for _ in range(6))
            # 중복 확인
            if not Classroom.query.filter_by(code=code).first():
                return code

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'survey_active': self.survey_active,
            'student_count': self.students.count(),
            'response_count': self.surveys.filter_by(is_complete=True).count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Student(db.Model):
    """학생 모델 - 교사가 등록한 학생 명단"""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_number = db.Column(db.Integer)  # 번호 (선택)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 설문 응답 관계 (학생 삭제 시 응답도 함께 삭제)
    responses = db.relationship('SurveyResponse', backref='student', lazy='dynamic',
                                foreign_keys='SurveyResponse.student_id',
                                cascade='all, delete-orphan')

    # 복합 유니크 제약 (같은 학급 내 이름 중복 방지)
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'name', name='uq_classroom_student_name'),
    )

    def __repr__(self):
        return f'<Student {self.name}>'

    @property
    def has_responded(self):
        """설문 응답 완료 여부"""
        return self.responses.filter_by(is_complete=True).first() is not None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'student_number': self.student_number,
            'has_responded': self.has_responded
        }


class SurveyResponse(db.Model):
    """설문 응답 모델"""
    __tablename__ = 'survey_responses'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    responses = db.Column(db.JSON)  # 설문 응답 데이터 (JSON)
    is_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 복합 유니크 제약 (학생당 하나의 응답)
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'student_id', name='uq_classroom_student_response'),
    )

    def __repr__(self):
        return f'<SurveyResponse student_id={self.student_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'is_complete': self.is_complete,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AnalysisResult(db.Model):
    """분석 결과 저장 모델"""
    __tablename__ = 'analysis_results'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    network_data = db.Column(db.JSON)  # 네트워크 데이터
    metrics = db.Column(db.JSON)  # 중심성 지표 등
    communities = db.Column(db.JSON)  # 커뮤니티 탐지 결과
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 관계
    classroom = db.relationship('Classroom', backref=db.backref('analysis_results', lazy='dynamic'))

    def __repr__(self):
        return f'<AnalysisResult classroom_id={self.classroom_id}>'
