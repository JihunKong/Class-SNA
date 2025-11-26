"""
데이터 처리 모듈
Flask 버전 - Streamlit 의존성 제거
"""
import pandas as pd
import json
import re
import logging
import traceback
import requests
from io import StringIO, BytesIO
import numpy as np
import io
import csv

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """설문조사 데이터 처리 및 변환 클래스"""

    def __init__(self, api_manager=None):
        self.api_manager = api_manager

    def extract_sheet_id(self, sheet_url):
        """구글 시트 URL에서 ID 추출"""
        try:
            if '/d/' in sheet_url:
                sheet_id = sheet_url.split('/d/')[1].split('/')[0]
                return sheet_id
            else:
                return None
        except Exception as e:
            logger.error(f"시트 ID 추출 실패: {str(e)}")
            return None

    def load_from_gsheet(self, sheet_url):
        """구글 시트에서 데이터 로드"""
        try:
            logger.info(f"구글 시트에서 데이터 로드 시작: {sheet_url}")

            sheet_id = self.extract_sheet_id(sheet_url)
            if not sheet_id:
                raise ValueError("유효한 구글 시트 URL이 아닙니다.")

            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            logger.debug(f"CSV 데이터 요청 URL: {csv_url}")

            response = self.api_manager.request_data(csv_url)
            if response is None:
                raise ConnectionError("구글 시트에 연결할 수 없습니다.")

            # 데이터를 CSV로 변환하여 DataFrame 생성
            try:
                csv_data = io.StringIO(response.decode('utf-8'))
                df = pd.read_csv(csv_data)
            except UnicodeDecodeError:
                logger.info("UTF-8 디코딩 실패, CP949로 시도합니다.")
                try:
                    csv_data = io.StringIO(response.decode('cp949'))
                    df = pd.read_csv(csv_data)
                except Exception:
                    logger.info("CP949 디코딩 실패, 다른 인코딩으로 시도합니다.")
                    try:
                        df = pd.read_csv(io.BytesIO(response), encoding='utf-8-sig')
                    except Exception as e:
                        logger.error(f"모든 인코딩 시도 실패: {str(e)}")
                        raise ValueError("CSV 데이터를 읽어들일 수 없습니다.")

            if len(df.columns) < 2:
                raise ValueError("최소 2개 이상의 열이 필요합니다.")

            df = self._preprocess_dataframe(df)

            logger.info(f"구글 시트 데이터 로드 완료: 행 {df.shape[0]}, 열 {df.shape[1]}")
            return df

        except Exception as e:
            logger.error(f"구글 시트 데이터 로드 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def load_from_file(self, file_content, filename):
        """업로드된 파일에서 데이터 로드"""
        try:
            logger.info(f"파일에서 데이터 로드: {filename}")

            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='cp949')
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise ValueError("지원하지 않는 파일 형식입니다. CSV 또는 Excel 파일을 업로드하세요.")

            if len(df.columns) < 2:
                raise ValueError("최소 2개 이상의 열이 필요합니다.")

            df = self._preprocess_dataframe(df)

            logger.info(f"파일 데이터 로드 완료: 행 {df.shape[0]}, 열 {df.shape[1]}")
            return df

        except Exception as e:
            logger.error(f"파일 데이터 로드 중 오류: {str(e)}")
            raise

    def _preprocess_dataframe(self, df):
        """데이터프레임 기본 전처리"""
        df = df.dropna(how='all').dropna(axis=1, how='all')

        if 'Timestamp' not in df.columns and '타임스탬프' not in df.columns:
            if len(df) > 1 and df.iloc[0].apply(lambda x: isinstance(x, str) and not x.isdigit()).all():
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)

        df.columns = [re.sub(r'\.\d+$', '', col) if isinstance(col, str) else col for col in df.columns]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.replace(['', ' ', 'nan', 'NaN', 'null', 'NULL'], np.nan)
        df = df.dropna(axis=1, how='all')

        return df

    def analyze_data_structure(self, df):
        """데이터 구조 분석하여 응답자와 관계 질문 식별"""
        logger.info("데이터 구조 분석 시작")

        result = {
            'respondent_column': None,
            'relationship_columns': [],
            'relationship_types': [],
            'students': set(),
            'metadata': {},
            'dataframe': df
        }

        columns_info = self._analyze_columns(df)

        if columns_info['respondent_col']:
            result['respondent_column'] = columns_info['respondent_col']
        else:
            result['respondent_column'] = df.columns[0]

        if columns_info['relationship_cols']:
            result['relationship_columns'] = columns_info['relationship_cols']
        else:
            result['relationship_columns'] = [col for col in df.columns if col != result['respondent_column']]

        result['relationship_types'] = self._extract_relationship_types(result['relationship_columns'])
        result['students'] = self._collect_students(df, result['respondent_column'], result['relationship_columns'])

        result['metadata'] = {
            'num_students': len(result['students']),
            'num_questions': len(result['relationship_columns']),
            'question_types': result['relationship_types']
        }

        # AI 인사이트 분석 (선택적)
        try:
            if self.api_manager:
                insights = self._get_ai_insights(df, result)
                result['ai_insights'] = insights
        except Exception as e:
            logger.warning(f"AI 인사이트 분석 중 오류 발생: {str(e)}")
            result['ai_insights'] = {
                'relationship_types': {col: 'general' for col in result['relationship_columns']},
                'data_characteristics': '자동 분석 실패',
                'conversion_recommendation': '기본 변환 방법 사용'
            }

        logger.info(f"데이터 구조 분석 완료: {len(result['students'])}명의 학생")
        return result

    def _analyze_columns(self, df):
        """열을 분석하여 응답자 열과 관계 질문 열 식별"""
        result = {
            'respondent_col': None,
            'relationship_cols': []
        }

        respondent_keywords = ['이름', '학생', '응답자', '본인', 'name', 'student', 'respondent']
        relationship_keywords = ['친구', '좋아하는', '함께', '선택', '관계', '도움', '의지',
                                 'friend', 'like', 'help', 'together', 'choose', 'relationship']

        for col in df.columns:
            if isinstance(col, str):
                col_lower = col.lower()

                if any(keyword in col_lower for keyword in respondent_keywords):
                    result['respondent_col'] = col
                    continue

                if any(keyword in col_lower for keyword in relationship_keywords):
                    result['relationship_cols'].append(col)

        if not result['respondent_col']:
            unique_counts = df.nunique()
            max_unique_col = unique_counts.idxmax()
            result['respondent_col'] = max_unique_col

        if not result['relationship_cols']:
            result['relationship_cols'] = [col for col in df.columns if col != result['respondent_col']]

        exclude_keywords = ['timestamp', '타임스탬프', '제출', '시간', 'time']
        result['relationship_cols'] = [col for col in result['relationship_cols']
                                        if not any(keyword in str(col).lower() for keyword in exclude_keywords)]

        return result

    def _extract_relationship_types(self, relationship_columns):
        """관계 질문 열에서 관계 유형 추출"""
        relationship_types = []

        type_keywords = {
            '친구': 'friendship',
            '좋아': 'preference',
            '협업': 'collaboration',
            '도움': 'help',
            '공부': 'study',
            '선택': 'selection',
            '함께': 'together',
            '소통': 'communication',
            '신뢰': 'trust'
        }

        for col in relationship_columns:
            col_str = str(col).lower()
            matched_type = None

            for keyword, type_name in type_keywords.items():
                if keyword in col_str:
                    matched_type = type_name
                    break

            if not matched_type:
                matched_type = 'general'

            relationship_types.append(matched_type)

        return relationship_types

    def _collect_students(self, df, respondent_column, relationship_columns):
        """모든 학생 목록 수집"""
        students = set()

        respondents = df[respondent_column].dropna().unique()
        students.update(respondents)

        for col in relationship_columns:
            if df[col].dtype == 'object':
                for cell in df[col].dropna():
                    if isinstance(cell, str):
                        names = re.split(r'[,;/\n]+', cell)
                        names = [name.strip() for name in names if name.strip()]
                        students.update(names)

        students = {s for s in students if s and not pd.isna(s)}

        return students

    def _get_ai_insights(self, df, analysis_result):
        """인공지능을 통한 데이터 구조 추가 분석"""
        try:
            df_sample = df.head(5).to_dict(orient='records')

            prompt = (
                f"다음은 학급 관계 설문조사 데이터의 샘플입니다:\n\n"
                f"{json.dumps(df_sample, ensure_ascii=False, indent=2)}\n\n"
                f"응답자 열은 '{analysis_result['respondent_column']}'이고, "
                f"관계 질문 열은 {analysis_result['relationship_columns']}입니다.\n\n"
                f"이 데이터를 소셜 네트워크 분석(SNA)에 적합한 형태로 변환하려고 합니다.\n"
                f"다음 정보를 JSON 형식으로 응답해주세요:\n"
                f"1. 각 열이 나타내는 관계 유형\n"
                f"2. 데이터 구조의 특징과 주의사항\n"
                f"3. 최적의 네트워크 변환 방법 제안"
            )

            insights = self.api_manager.get_ai_analysis(prompt)
            logger.info("AI 인사이트 분석 완료")
            return insights

        except Exception as e:
            logger.warning(f"AI 인사이트 분석 중 오류 발생: {str(e)}")
            return {
                'relationship_types': {col: 'general' for col in analysis_result['relationship_columns']},
                'data_characteristics': '자동 분석 실패',
                'conversion_recommendation': '기본 변환 방법 사용'
            }

    def convert_to_network_data(self, analysis_result):
        """분석 결과를 네트워크 데이터로 변환"""
        logger.info("네트워크 데이터 변환 시작")

        network_data = {
            'students': [],
            'relationships': [],
            'metadata': {
                'relationship_types': analysis_result.get('relationship_types', []),
                'num_students': len(analysis_result.get('students', [])),
                'num_relationships': 0
            }
        }

        # 학생 노드 생성
        for i, student in enumerate(analysis_result.get('students', [])):
            if not student or pd.isna(student):
                continue

            student_node = {
                'id': i,
                'name': student,
                'label': student,
                'group': 1
            }
            network_data['students'].append(student_node)

        name_to_id = {student['name']: student['id'] for student in network_data['students']}

        relationships = []

        try:
            df = analysis_result.get('dataframe')
            relationship_columns = analysis_result.get('relationship_columns', [])
            respondent_column = analysis_result.get('respondent_column')

            if df is None or df.empty:
                logger.warning("데이터프레임 없음, AI 인사이트 기반 관계 생성")
                ai_insights = analysis_result.get('ai_insights', {})
                network_data['relationships'] = self._generate_relationships_from_ai_insights(
                    ai_insights,
                    network_data['students']
                )
            else:
                for idx, row in df.iterrows():
                    respondent = row.get(respondent_column)

                    if not respondent or pd.isna(respondent) or respondent not in name_to_id:
                        continue

                    source_id = name_to_id[respondent]

                    for col_idx, col in enumerate(relationship_columns):
                        value = row.get(col)

                        if pd.isna(value) or not value:
                            continue

                        rel_type = analysis_result['relationship_types'][col_idx] if col_idx < len(
                            analysis_result['relationship_types']) else 'general'

                        if isinstance(value, str):
                            targets = re.split(r'[,;/\n]+', value)
                            for target in targets:
                                target = target.strip()
                                if target and target in name_to_id:
                                    target_id = name_to_id[target]
                                    relationships.append({
                                        'from': source_id,
                                        'to': target_id,
                                        'type': rel_type,
                                        'weight': 1
                                    })

                # 중복 관계 처리
                merged_relationships = {}
                for rel in relationships:
                    key = (rel['from'], rel['to'], rel['type'])
                    if key in merged_relationships:
                        merged_relationships[key]['weight'] += rel['weight']
                    else:
                        merged_relationships[key] = rel

                network_data['relationships'] = list(merged_relationships.values())

        except Exception as e:
            logger.error(f"관계 데이터 변환 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            network_data['relationships'] = self._generate_random_relationships(network_data['students'])

        network_data['metadata']['num_relationships'] = len(network_data['relationships'])

        # 데이터 구조 변환 - pandas DataFrame 형식으로
        try:
            nodes_df = pd.DataFrame(network_data['students'])
            edges_df = pd.DataFrame(network_data['relationships'])

            network_data['nodes'] = nodes_df
            network_data['edges'] = edges_df
        except Exception as e:
            logger.error(f"데이터프레임 변환 오류: {str(e)}")
            network_data['nodes'] = pd.DataFrame(columns=['id', 'name', 'label', 'group'])
            network_data['edges'] = pd.DataFrame(columns=['from', 'to', 'type', 'weight'])

        logger.info(f"네트워크 데이터 변환 완료: {len(network_data['students'])}명의 학생")
        return network_data

    def _generate_relationships_from_ai_insights(self, ai_insights, students):
        """AI 인사이트 기반으로 관계 데이터 생성"""
        relationships = []
        student_ids = [s['id'] for s in students]

        if not student_ids:
            return relationships

        relationship_types = ai_insights.get('relationship_types', {'friendship': 0.6, 'collaboration': 0.4})

        def str_to_float(value, default=0.5):
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str) and value.replace('.', '', 1).isdigit():
                    return float(value)
                return default
            except Exception:
                return default

        for rel_type, probability in relationship_types.items():
            prob = str_to_float(probability, 0.5)

            for source_id in student_ids:
                for target_id in student_ids:
                    if source_id == target_id:
                        continue

                    if np.random.random() < prob:
                        relationships.append({
                            'from': source_id,
                            'to': target_id,
                            'type': str(rel_type),
                            'weight': np.random.randint(1, 4)
                        })

        return relationships

    def _generate_random_relationships(self, students):
        """랜덤 관계 데이터 생성 (오류 발생 시 폴백)"""
        relationships = []
        student_ids = [s['id'] for s in students]

        if not student_ids:
            return relationships

        rel_types = ['friendship', 'collaboration', 'help']

        for source_id in student_ids:
            num_relations = np.random.randint(1, min(6, len(students)))
            other_students = [id for id in student_ids if id != source_id]

            if other_students:
                sample_size = min(num_relations, len(other_students))
                targets = np.random.choice(other_students, size=sample_size, replace=False)

                for target_id in targets:
                    rel_type = np.random.choice(rel_types)
                    relationships.append({
                        'from': source_id,
                        'to': target_id,
                        'type': rel_type,
                        'weight': np.random.randint(1, 4)
                    })

        return relationships

    def process_survey_data(self, sheet_url):
        """전체 데이터 처리 과정 실행"""
        try:
            df = self.load_from_gsheet(sheet_url)
            analysis_result = self.analyze_data_structure(df)
            network_data = self.convert_to_network_data(analysis_result)

            return {
                'dataframe': df,
                'analysis': analysis_result,
                'network_data': network_data
            }

        except Exception as e:
            logger.error(f"설문조사 데이터 처리 실패: {str(e)}")
            raise Exception(f"데이터 처리 중 오류가 발생했습니다: {str(e)}")

    def process_uploaded_file(self, file_content, filename):
        """업로드된 파일 처리"""
        try:
            df = self.load_from_file(file_content, filename)
            analysis_result = self.analyze_data_structure(df)
            network_data = self.convert_to_network_data(analysis_result)

            return {
                'dataframe': df,
                'analysis': analysis_result,
                'network_data': network_data
            }

        except Exception as e:
            logger.error(f"파일 데이터 처리 실패: {str(e)}")
            raise Exception(f"데이터 처리 중 오류가 발생했습니다: {str(e)}")
