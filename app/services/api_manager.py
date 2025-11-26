"""
Google Gemini API 매니저
Flask 버전 - Streamlit 의존성 제거
"""
import google.generativeai as genai
import logging
import time
import requests
import json
import os
import random

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIManager:
    """Google Gemini API 통신을 관리하는 클래스"""

    def __init__(self, api_keys=None, model=None):
        """
        APIManager 초기화

        Args:
            api_keys: API 키 리스트 (없으면 환경변수에서 로드)
            model: Gemini 모델명 (없으면 환경변수 또는 기본값 사용)
        """
        self.api_keys = api_keys or self._load_api_keys()
        self.current_api_key = None
        self.model = model or os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')
        self.setup_api()

    def _load_api_keys(self):
        """환경변수에서 API 키 로드"""
        keys_str = os.environ.get('GOOGLE_API_KEYS', '')
        if keys_str:
            return [k.strip() for k in keys_str.split(',') if k.strip()]
        return []

    def _get_random_api_key(self):
        """랜덤 API 키 선택"""
        if not self.api_keys:
            raise ValueError("API 키가 설정되지 않았습니다. GOOGLE_API_KEYS 환경변수를 확인해주세요.")
        return random.choice(self.api_keys)

    def setup_api(self):
        """API 키 설정 및 Gemini 모델 초기화"""
        try:
            self.current_api_key = self._get_random_api_key()
            genai.configure(api_key=self.current_api_key)
            logger.info(f"API 설정 완료: 모델 {self.model} 사용")
        except ValueError as e:
            logger.error(f"API 설정 실패: {str(e)}")
            raise

    def switch_api_key(self):
        """다른 API 키로 전환"""
        previous_key = self.current_api_key
        try:
            attempts = 0
            while self.current_api_key == previous_key and attempts < 10:
                self.current_api_key = self._get_random_api_key()
                attempts += 1

            genai.configure(api_key=self.current_api_key)
            logger.info("새로운 API 키로 전환 완료")
        except ValueError as e:
            logger.error(f"API 키 전환 실패: {str(e)}")
            raise

    def request_data(self, url, max_retries=3):
        """HTTP 요청을 통해 데이터 요청

        Args:
            url (str): 요청할 URL
            max_retries (int): 최대 재시도 횟수

        Returns:
            bytes: 응답 데이터 (바이너리)

        Raises:
            ConnectionError: 연결 실패 시
            Exception: 기타 요청 실패 시
        """
        retries = 0

        # 헤더 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml,text/csv;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }

        # 구글 시트 URL 처리
        if 'docs.google.com/spreadsheets' in url:
            if '/export?' in url:
                if '?' in url:
                    url = url + "&gid=0&single=true&output=csv"
                else:
                    url = url + "?gid=0&single=true&output=csv"

            # 예시 데이터 URL 처리
            if '1iBAe4rYrQ8MuQyKVlZ-awqGSiAr9pMAaLK8y5BSrIX8' in url:
                logger.info("예시 1 데이터 사용")
                example_path = os.path.join(os.path.dirname(__file__), '../../data/example1.csv')
                if os.path.exists(example_path):
                    with open(example_path, 'rb') as f:
                        return f.read()
                return self._get_example_data(1)

            if '1-Nv-aAQkUkS9KYJwF1VlnY6qRKEO5SnNVQfmIZLNDfQ' in url:
                logger.info("예시 2 데이터 사용")
                example_path = os.path.join(os.path.dirname(__file__), '../../data/example2.csv')
                if os.path.exists(example_path):
                    with open(example_path, 'rb') as f:
                        return f.read()
                return self._get_example_data(2)

        while retries < max_retries:
            try:
                logger.debug(f"HTTP 요청: {url}")
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    logger.debug("HTTP 요청 성공")
                    return response.content
                else:
                    logger.warning(f"HTTP 요청 실패 (상태 코드: {response.status_code})")
                    retries += 1
                    time.sleep(1)

            except requests.exceptions.RequestException as e:
                logger.error(f"HTTP 요청 오류: {str(e)}")
                retries += 1
                if retries >= max_retries:
                    raise ConnectionError(f"데이터 요청 실패: {str(e)}")
                time.sleep(1)

        # 모든 시도 실패 시 기본 예시 데이터 반환
        if 'docs.google.com/spreadsheets' in url:
            logger.warning("구글 시트 요청 실패. 기본 예시 데이터로 대체합니다.")
            return self._get_example_data(1)

        raise Exception(f"최대 재시도 횟수 초과: {url}")

    def _get_example_data(self, example_number=1):
        """예시 데이터 생성 (URL 접근 불가 시 대체용)"""
        if example_number == 1:
            example_data = """타임스탬프,이름,좋아하는 친구
2024-01-01,김철수,홍길동;이영희
2024-01-02,홍길동,김철수;박지성
2024-01-03,이영희,김철수;최민수
2024-01-04,박지성,홍길동;최민수
2024-01-05,최민수,이영희;김철수"""
        else:
            example_data = """타임스탬프,학생 이름,함께 공부하고 싶은 친구,함께 프로젝트 하고 싶은 친구
2024-01-01,학생1,학생2;학생3,학생4;학생5
2024-01-02,학생2,학생1,학생3
2024-01-03,학생3,학생4,학생1;학생2
2024-01-04,학생4,학생5,학생3
2024-01-05,학생5,학생1;학생4,학생2"""

        return example_data.encode('utf-8')

    def get_ai_analysis(self, prompt):
        """인공지능을 통한 데이터 구조 분석"""
        try:
            response_text = self.generate_response(prompt)

            try:
                json_str = self._extract_json_from_text(response_text)
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"AI 응답에서 유효한 JSON을 추출할 수 없습니다: {str(e)}")
                return self._get_default_analysis_result()

        except Exception as e:
            logger.warning(f"AI 분석 중 오류 발생: {str(e)}")
            return self._get_default_analysis_result()

    def _extract_json_from_text(self, text):
        """텍스트에서 JSON 부분만 추출"""
        start_idx = text.find('{')
        if start_idx == -1:
            raise ValueError("JSON 시작 기호 '{' 를 찾을 수 없습니다.")

        balance = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                balance += 1
            elif text[i] == '}':
                balance -= 1

            if balance == 0:
                end_idx = i + 1
                return text[start_idx:end_idx]

        raise ValueError("JSON 형식이 완전하지 않습니다.")

    def _get_default_analysis_result(self):
        """기본 분석 결과 생성"""
        return {
            'relationship_types': {
                '좋아하는 친구': 'friendship',
                '함께 공부하고 싶은 친구': 'study',
                '함께 프로젝트 하고 싶은 친구': 'collaboration'
            },
            'data_characteristics': '기본 설문조사 형식',
            'conversion_recommendation': '1:N 관계로 변환 필요'
        }

    def generate_response(self, prompt, max_retries=3):
        """Gemini API를 사용하여 응답 생성"""
        retries = 0

        while retries < max_retries:
            try:
                model = genai.GenerativeModel(self.model)
                response = model.generate_content(prompt)
                return response.text

            except Exception as e:
                logger.error(f"API 오류 발생: {str(e)}")
                retries += 1

                if retries < max_retries:
                    logger.info(f"API 키 전환 후 {retries}/{max_retries} 재시도 중...")
                    try:
                        self.switch_api_key()
                        time.sleep(1)
                    except ValueError:
                        raise ValueError("API 키가 설정되지 않았습니다.")
                else:
                    logger.error("최대 재시도 횟수 초과")
                    raise Exception("API 요청 실패. 잠시 후 다시 시도해주세요.")

    def analyze_survey_data(self, survey_data, survey_questions=None):
        """설문 데이터 구조 분석 및 관계형 데이터 변환 요청"""
        context = """
        당신은 학생 관계 설문조사 데이터를 분석하는 AI 전문가입니다.
        제공된 설문조사 데이터를 분석하여 학생 간 관계(From-To)를 식별하고 네트워크 분석에 적합한 형태로 변환해야 합니다.
        """

        prompt = f"""
        {context}

        # 설문조사 데이터:
        ```
        {survey_data}
        ```

        # 작업:
        1. 관계형 질문을 식별하세요.
        2. 응답자(From)와 선택된 학생(To) 간의 관계를 추출하세요.
        3. 학생 이름의 불일치나 오타를 수정하세요.
        4. 다음 JSON 형식으로 결과를 반환하세요:
        ```json
        {{
            "relationships": [
                {{"from": "학생1", "to": "학생2", "weight": 1, "type": "friendship"}},
                ...
            ],
            "students": ["학생1", "학생2", "학생3", ...],
            "question_types": {{
                "question1": "friendship",
                "question2": "academic",
                ...
            }}
        }}
        ```

        결과는 반드시 유효한 JSON 형식이어야 합니다.
        """

        if survey_questions:
            prompt += f"\n\n# 설문조사 질문:\n{survey_questions}"

        return self.generate_response(prompt)

    def generate_text(self, prompt):
        """텍스트 생성 API를 호출합니다."""
        try:
            if not self.current_api_key:
                logger.warning("API 키가 없어 텍스트 생성을 건너뜁니다.")
                return None

            return self._generate_with_gemini(prompt)
        except Exception as e:
            logger.error(f"텍스트 생성 중 오류: {e}")
            return None

    def _generate_with_gemini(self, prompt):
        """Google Gemini API를 사용하여 텍스트를 생성합니다."""
        try:
            genai.configure(api_key=self.current_api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            return response.text
        except ImportError:
            logger.error("Google Generative AI 패키지가 설치되어 있지 않습니다.")
            return None
        except Exception as e:
            logger.error(f"Gemini API 호출 중 오류: {e}")
            return None
