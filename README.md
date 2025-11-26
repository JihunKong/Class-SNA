# 학급 관계 네트워크 분석 시스템 (Class-SNA) v2.0

학급 관계 네트워크 분석 시스템(Class-SNA)은 교사가 수집한 학생 간 관계 설문조사 데이터를 소셜 네트워크 분석(SNA) 그래프로 자동 변환하여 시각화하는 웹 애플리케이션입니다.

## v2.0 주요 변경사항

- **Flask + Tailwind CSS** 기반으로 완전 재구축
- **글라스모피즘 디자인** 적용 (반투명 유리 효과)
- **AWS EC2 + Docker** 프로덕션 배포
- **Redis** 기반 세션/캐싱 시스템
- **REST API** 아키텍처

## 주요 기능

- 구글 시트 공유 링크 또는 CSV 파일을 통한 설문 데이터 가져오기
- Google Gemini AI를 활용한 자동 데이터 구조 분석 및 변환
- 향상된 물리 엔진을 활용한 대화형 네트워크 그래프 시각화
- 노드 클릭 시 시각적 효과 강화로 관계망 탐색 용이성 개선
- 중심성 지표 계산 및 하위 그룹(커뮤니티) 자동 식별
- 한글 이름 지원 및 최적화된 레이아웃 알고리즘
- 고립 학생 자동 감지 및 통계 분석

## 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Flask, Python 3.11+ |
| 프론트엔드 | Jinja2, Tailwind CSS, Vanilla JS |
| 디자인 | 글라스모피즘 (Glassmorphism) |
| 데이터 분석 | NetworkX, Pandas, NumPy |
| 시각화 | Plotly.js, Vis.js |
| AI | Google Gemini API |
| 캐싱 | Redis |
| 배포 | Docker, Nginx, AWS EC2 |
| SSL | Let's Encrypt |

## 설치 및 실행 방법

### 사전 요구사항

- Python 3.11+
- Node.js 18+ (Tailwind CSS 빌드용)
- Docker & Docker Compose
- Redis (Docker로 실행 가능)

### 로컬 개발 환경

1. **저장소 클론**:
   ```bash
   git clone https://github.com/techkwon/Class-SNA.git
   cd Class-SNA
   ```

2. **Python 가상환경 설정**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Node.js 의존성 설치** (Tailwind CSS):
   ```bash
   npm install
   npm run build:css
   ```

4. **환경 변수 설정**:
   ```bash
   cp .env.example .env
   # .env 파일을 열어 API 키 등 설정
   ```

   필수 환경 변수:
   ```
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   GOOGLE_API_KEYS=key1,key2,key3
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Redis 실행** (Docker 사용):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

6. **앱 실행**:
   ```bash
   flask run --debug
   ```
   또는
   ```bash
   python wsgi.py
   ```

7. 브라우저에서 `http://localhost:5000` 접속

### Docker로 로컬 실행

```bash
# 개발 환경
docker-compose -f docker/docker-compose.yml up --build

# 브라우저에서 http://localhost:5000 접속
```

## AWS EC2 배포 가이드

### 1. EC2 인스턴스 준비

**권장 사양:**
- 인스턴스 타입: t3.small 이상
- OS: Ubuntu 22.04 LTS
- 스토리지: 30GB gp3 SSD
- 리전: ap-northeast-2 (서울)

**보안 그룹 설정:**
- SSH (22): 관리자 IP만
- HTTP (80): 0.0.0.0/0
- HTTPS (443): 0.0.0.0/0

### 2. Elastic IP 할당

1. AWS 콘솔 > EC2 > 네트워크 및 보안 > 탄력적 IP
2. 탄력적 IP 주소 할당
3. 작업 > 탄력적 IP 주소 연결 > 인스턴스 선택

### 3. 서버 초기 설정

```bash
# SSH 접속
ssh -i your-key.pem ubuntu@your-elastic-ip

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 재로그인 (docker 그룹 적용)
exit
ssh -i your-key.pem ubuntu@your-elastic-ip
```

### 4. 프로젝트 배포

```bash
# 프로젝트 클론
git clone https://github.com/techkwon/Class-SNA.git
cd Class-SNA

# 환경 변수 설정
cp .env.example .env
nano .env  # API 키 등 설정

# 프로덕션 배포
docker-compose -f docker/docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker/docker-compose.prod.yml logs -f
```

### 5. SSL 인증서 설정 (Let's Encrypt)

도메인이 있는 경우:
```bash
# Certbot으로 SSL 인증서 발급
./scripts/setup-ssl.sh your-domain.com your-email@example.com
```

Elastic IP만 사용하는 경우:
- 자체 서명 인증서 사용 또는 HTTP로만 접속

### 6. 배포 업데이트

```bash
cd ~/Class-SNA
git pull origin main
docker-compose -f docker/docker-compose.prod.yml up -d --build
```

## 프로젝트 구조

```
Class-SNA/
├── app/                         # Flask 애플리케이션
│   ├── __init__.py              # 앱 팩토리
│   ├── config.py                # 설정
│   ├── api/                     # REST API
│   ├── views/                   # 페이지 라우트
│   ├── services/                # 비즈니스 로직
│   ├── templates/               # Jinja2 템플릿
│   └── static/                  # CSS, JS, 이미지
├── docker/                      # Docker 설정
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
├── scripts/                     # 배포 스크립트
├── data/                        # 샘플 데이터
├── tests/                       # 테스트
├── requirements.txt
├── package.json
└── wsgi.py
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/upload` | 파일 업로드 |
| POST | `/api/v1/analyze` | 분석 시작 |
| GET | `/api/v1/network` | 네트워크 데이터 |
| GET | `/api/v1/centrality/<metric>` | 중심성 지표 |
| GET | `/api/v1/communities` | 커뮤니티 정보 |
| GET | `/api/v1/students/<name>` | 학생 분석 |
| GET | `/api/v1/isolated` | 고립 학생 |
| GET | `/api/v1/export/<format>` | 내보내기 |

## 환경 변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `FLASK_ENV` | 환경 모드 | `production` |
| `SECRET_KEY` | 세션 암호화 키 | `your-secret-key` |
| `GOOGLE_API_KEYS` | Gemini API 키 (쉼표 구분) | `key1,key2,key3` |
| `REDIS_URL` | Redis 연결 URL | `redis://redis:6379/0` |
| `MAX_CONTENT_LENGTH` | 업로드 제한 (바이트) | `16777216` |

## 사용 방법

1. 웹 애플리케이션 접속
2. 구글 시트 공유 링크 입력 또는 CSV 파일 업로드
3. AI가 자동으로 데이터 구조 분석 및 매핑 제안
4. 네트워크 그래프 생성 및 인터랙티브 시각화 확인
5. 다양한 탭에서 분석 결과 탐색:
   - 📊 학생 분석: 개별 학생의 관계 통계
   - 🌐 대화형 네트워크: 인터랙티브 그래프
   - 📈 중심성 분석: 학생 영향력 및 역할 분석
   - 👥 그룹 분석: 커뮤니티 구성 확인
   - ⚠️ 고립 학생: 관계망에서 소외된 학생 식별
6. 결과 내보내기 (CSV, Excel, PDF)

## 기여하기

프로젝트에 기여하고 싶으시다면 다음 단계를 따라주세요:

1. 이 저장소를 포크합니다
2. 새로운 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

*Made by G.E.N.I.U.S 연구회*
