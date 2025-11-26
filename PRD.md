# PRD: 학급 관계 네트워크 분석 시스템 (Class-SNA) v2.0

## 1. 개요 및 목적

**Class-SNA**는 교사가 수집한 학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 자동 변환하여 시각화하는 웹 애플리케이션입니다. 본 시스템은 **AWS EC2 + Docker** 기반으로 배포되며, Google Gemini AI를 활용하여 다양한 형태의 설문조사 데이터를 자동으로 분석하고 적절한 네트워크 그래프로 변환합니다.

**v2.0 주요 변경사항:**
- Streamlit에서 Flask + Tailwind CSS로 프레임워크 전환
- 글라스모피즘(Glassmorphism) 디자인 시스템 적용
- AWS EC2 + Docker 기반 프로덕션 배포
- Redis 기반 세션/캐싱 시스템

**주요 목적:**
- 교사가 학급 내 학생 관계를 시각적으로 파악할 수 있는 도구 제공
- 복잡한 데이터 가공 과정 없이 설문조사 결과를 즉시 네트워크 그래프로 변환
- 학급 내 사회적 관계, 학습 그룹, 소외 학생 등을 식별하여 교육 환경 개선에 활용

## 2. 사용자 프로필

- **주요 사용자**: K-12 중등 교사
- **기술 수준**: 기본적인 컴퓨터 활용 능력을 갖추었으나, 데이터 분석이나 프로그래밍 지식은 제한적
- **사용 목적**: 학급 내 학생 관계 파악, 소그룹 활동 구성, 학생 지원 전략 수립

## 3. 주요 기능

### 3.1 데이터 입력
- 구글 시트 공유 링크 입력을 통한 데이터 가져오기
- CSV/Excel 파일 직접 업로드
- 다양한 형식의 설문조사 데이터 지원 (체크박스, 드롭다운, 단답형 등)

### 3.2 AI 기반 데이터 가공
- Gemini-2.0-flash 모델을 활용한 설문조사 데이터 구조 자동 인식
- 설문 응답을 From-To 관계형 데이터로 자동 변환
- 누락되거나 불일치하는 학생 이름 자동 수정 및 통합

### 3.3 네트워크 시각화
- 학생 간 관계를 나타내는 대화형 네트워크 그래프 생성
- 다양한 레이아웃 알고리즘 선택 옵션 (ForceAtlas2, Fruchterman-Reingold 등)
- 노드(학생) 크기, 색상 등 시각화 요소 커스터마이징
- 관계 강도에 따른 엣지(연결선) 두께 조정
- 노드 클릭 시 관련 관계망 하이라이트

### 3.4 분석 기능
- 중심성 지표(연결 중심성, 근접 중심성, 매개 중심성 등) 자동 계산
- 주요 하위 그룹(클러스터) 자동 식별 (Louvain 알고리즘)
- 소외 학생(연결이 적은 노드) 강조 표시
- 주요 지표 요약 통계 제공

### 3.5 결과 내보내기
- 생성된 그래프 이미지(PNG, SVG) 다운로드
- 가공된 데이터 및 분석 결과 CSV/Excel 형식 내보내기
- 분석 보고서 PDF 생성

## 4. 사용자 흐름

1. 사용자가 웹 애플리케이션에 접속
2. 구글 시트 공유 링크 입력 또는 CSV 파일 업로드
3. 설문조사 형식 확인 및 데이터 매핑 설정 (AI가 자동으로 제안)
4. 네트워크 그래프 시각화 옵션 선택
5. 그래프 생성 및 표시
6. 분석 결과 확인 (탭 네비게이션)
7. 결과 다운로드 또는 공유

## 5. 기술 요구사항

### 5.1 기본 프레임워크
- **백엔드**: Flask (Python 3.11+)
- **프론트엔드**: Jinja2 템플릿 + Tailwind CSS + Vanilla JavaScript
- **디자인 시스템**: 글라스모피즘 (Glassmorphism)
- **배포**: AWS EC2 + Docker + Nginx
- **버전 관리**: GitHub
- **인공지능**: Google Gemini API (gemini-2.0-flash 모델)

### 5.2 주요 라이브러리

#### 백엔드
- **웹 프레임워크**: Flask, Flask-CORS, Flask-Session
- **데이터 처리**: pandas, numpy
- **네트워크 분석**: networkx, python-louvain, scipy
- **시각화**: plotly, pyvis, matplotlib
- **외부 연동**: gspread, google-auth, google-generativeai
- **캐싱**: Flask-Caching, Redis
- **서버**: Gunicorn

#### 프론트엔드
- **스타일링**: Tailwind CSS 3.x
- **차트**: Plotly.js
- **네트워크**: Vis.js (vis-network)

### 5.3 API 관리
- **사용 모델**: gemini-2.0-flash
- **API 키 관리**: 환경 변수 (.env) 기반 관리
- **API 키 활용 방식**:
  - 랜덤 방식으로 API 키 선택 및 사용
  - API 오류 발생 시 자동으로 다른 API 키로 전환
  - API 사용량 모니터링 및 로깅

### 5.4 시스템 요구사항
- Python 3.11 이상
- Node.js 18+ (Tailwind CSS 빌드용)
- Docker & Docker Compose
- Redis 7+
- AWS EC2 (t3.small 이상 권장)

## 6. 데이터 처리 프로세스

1. **데이터 가져오기**:
   - 구글 시트 API를 통한 데이터 접근
   - CSV/Excel 파일 업로드 처리
   - 기본 데이터 구조 검증 및 전처리

2. **AI 기반 데이터 매핑**:
   - Gemini AI를 통한 설문 문항 분석
   - 관계형 질문 자동 인식
   - 적절한 데이터 변환 방법 추천

3. **네트워크 데이터 생성**:
   - From-To 형식의 엣지 리스트 생성
   - 관계 가중치 계산 (언급 빈도 등)
   - 노드 속성 정의 (학생 이름, 학년 등)

4. **네트워크 분석**:
   - 중심성 지표 계산
   - 커뮤니티 탐지 알고리즘 적용
   - 주요 통계 지표 계산

## 7. UI/UX 요구사항

### 7.1 디자인 시스템 - 글라스모피즘
- **배경**: 그라데이션 배경 (slate-900 → blue-900)
- **카드**: 반투명 유리 효과 (backdrop-filter: blur)
- **색상 팔레트**:
  - Primary: #1E88E5 (Blue)
  - Secondary: #0D47A1 (Dark Blue)
  - Glass White: rgba(255, 255, 255, 0.25)
  - Glass Border: rgba(255, 255, 255, 0.18)

### 7.2 인터페이스 구성
- 글라스 스타일 사이드바 네비게이션
- 반응형 그리드 레이아웃
- 글라스 카드 기반 메트릭 표시
- 탭 기반 분석 결과 네비게이션
- 모바일 기기 호환성 (반응형 디자인)

### 7.3 시각화 옵션
- 다양한 그래프 레이아웃 제공
- 노드/엣지 스타일 커스터마이징 옵션
- 인터랙티브 그래프 (확대/축소, 노드 드래그, 정보 툴팁)
- 커뮤니티별 색상 코딩

### 7.4 사용자 가이드
- 각 단계별 도움말 기능
- 시스템 사용 예시 비디오 또는 이미지
- 자주 묻는 질문(FAQ) 섹션

## 8. 보안 및 개인정보 보호

- 학생 개인정보 보호를 위한 익명화 옵션
- 데이터 로컬 처리 우선 (가능한 서버에 저장하지 않음)
- 구글 시트 접근은 읽기 전용으로 제한
- HTTPS 적용 (Let's Encrypt SSL)
- API 키 환경 변수 관리
- Rate Limiting 적용

## 9. 파일 구조

```
Class-SNA/
├── app/
│   ├── __init__.py              # Flask 앱 팩토리
│   ├── config.py                # 환경별 설정
│   ├── extensions.py            # Flask 확장 초기화
│   │
│   ├── api/                     # REST API Blueprint
│   │   ├── __init__.py
│   │   ├── data.py              # 데이터 업로드/처리 API
│   │   ├── analysis.py          # 분석 결과 API
│   │   └── export.py            # 내보내기 API
│   │
│   ├── views/                   # 페이지 Blueprint
│   │   ├── __init__.py
│   │   ├── main.py              # 메인/업로드 페이지
│   │   └── analysis.py          # 분석 결과 페이지
│   │
│   ├── services/                # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── api_manager.py       # Gemini API 통신
│   │   ├── data_processor.py    # 데이터 처리
│   │   ├── network_analyzer.py  # 네트워크 분석
│   │   └── visualizer.py        # 시각화 생성
│   │
│   ├── templates/               # Jinja2 템플릿
│   │   ├── base.html
│   │   ├── components/
│   │   │   ├── sidebar.html
│   │   │   ├── navbar.html
│   │   │   └── cards/
│   │   └── pages/
│   │       ├── index.html
│   │       ├── upload.html
│   │       └── analysis/
│   │
│   └── static/                  # 정적 파일
│       ├── css/
│       │   ├── tailwind.css
│       │   └── glassmorphism.css
│       ├── js/
│       │   ├── main.js
│       │   ├── charts.js
│       │   └── network.js
│       └── assets/
│           └── logo.png
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       ├── nginx.conf
│       └── ssl/
│
├── scripts/
│   ├── deploy.sh
│   ├── setup-ssl.sh
│   └── backup.sh
│
├── data/                        # 샘플 데이터
│   ├── example1.csv
│   └── example2.csv
│
├── tests/                       # 테스트
│   ├── __init__.py
│   ├── test_api.py
│   └── test_services.py
│
├── tailwind.config.js           # Tailwind 설정
├── package.json                 # Node 의존성
├── requirements.txt             # Python 의존성
├── wsgi.py                      # Gunicorn 진입점
├── .env.example                 # 환경 변수 템플릿
├── .gitignore
├── README.md
├── PRD.md
└── LICENSE
```

## 10. 배포 아키텍처

### 10.1 AWS EC2 구성
```
┌─────────────────────────────────────────────────────────┐
│                    AWS EC2 Instance                      │
│                  (t3.small / Ubuntu 22.04)              │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Docker Compose                      │   │
│  │                                                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │   │
│  │  │  Nginx  │→ │  Flask  │→ │  Redis  │         │   │
│  │  │ :80/443 │  │  :5000  │  │  :6379  │         │   │
│  │  └─────────┘  └─────────┘  └─────────┘         │   │
│  │       ↓                                          │   │
│  │  Let's Encrypt SSL                               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Elastic IP: xxx.xxx.xxx.xxx                            │
└─────────────────────────────────────────────────────────┘
```

### 10.2 배포 절차
1. EC2 인스턴스 생성 (Ubuntu 22.04 LTS)
2. Elastic IP 할당 및 연결
3. 보안 그룹 설정 (80, 443, 22 포트)
4. Docker & Docker Compose 설치
5. 코드 배포 및 환경 변수 설정
6. `docker-compose -f docker/docker-compose.prod.yml up -d`
7. Let's Encrypt SSL 인증서 발급

### 10.3 도메인 및 SSL
- Elastic IP 기반 접속
- Let's Encrypt (Certbot) SSL 인증서
- HTTP → HTTPS 자동 리다이렉트

## 11. 향후 개선사항

- 시계열 데이터 지원 (학기별 변화 추적)
- 고급 분석 기능 추가 (예측 모델링, 추천 시스템)
- 여러 학급 간 비교 분석 기능
- 모바일 앱 버전 개발
- 실시간 협업 기능
- AI 기반 교사 권장사항 자동 생성

## 12. 구현 일정

- **1단계** (1주): Flask 프로젝트 구조 설정 및 서비스 마이그레이션
- **2단계** (1주): Tailwind CSS + 글라스모피즘 UI 구현
- **3단계** (1주): 전체 분석 페이지 및 API 구현
- **4단계** (1주): Docker 설정 및 AWS EC2 배포
- **5단계** (1주): 테스트, 최적화 및 문서화

---

이 PRD는 Class-SNA v2.0 시스템의 요구사항과 구현 방향을 제시합니다. AWS EC2 기반 프로덕션 환경과 글라스모피즘 디자인을 적용한 현대적인 웹 애플리케이션으로 고도화됩니다.
