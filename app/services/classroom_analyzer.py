"""
학급 설문 응답 기반 네트워크 분석 서비스
DB에 저장된 SurveyResponse를 읽어 NetworkAnalyzer로 분석
"""
import logging
from flask import current_app

from app.models import db, Classroom, Student, SurveyResponse, AnalysisResult
from app.services.network_analyzer import NetworkAnalyzer

logger = logging.getLogger(__name__)


class ClassroomAnalyzer:
    """학급 설문 응답을 네트워크 데이터로 변환하고 분석하는 클래스"""

    # 관계 유형별 가중치
    RELATIONSHIP_WEIGHTS = {
        'friends': {'type': 'friendship', 'weight': 1.0},
        'helpers': {'type': 'help', 'weight': 0.8},
        'teammates': {'type': 'collaboration', 'weight': 0.9},
        'leaders': {'type': 'leadership', 'weight': 0.7},
        'trust': {'type': 'trust', 'weight': 1.0},
        'communication': {'type': 'communication', 'weight': 0.6},
        'avoidance': {'type': 'avoidance', 'weight': -0.5}  # 음수 가중치
    }

    def __init__(self, classroom_id: int):
        """
        Args:
            classroom_id: 분석할 학급 ID
        """
        self.classroom_id = classroom_id
        self.classroom = Classroom.query.get(classroom_id)
        if not self.classroom:
            raise ValueError(f"학급을 찾을 수 없습니다: {classroom_id}")

        self.students = {}  # id -> Student
        self.responses = []  # SurveyResponse 목록
        self.network_data = None
        self.analyzer = None
        self.analysis_result = None

    def load_data(self):
        """DB에서 학생과 설문 응답 데이터 로드"""
        # 학생 목록 로드
        students = self.classroom.students.all()
        self.students = {s.id: s for s in students}

        # 완료된 설문 응답 로드
        self.responses = SurveyResponse.query.filter_by(
            classroom_id=self.classroom_id,
            is_complete=True
        ).all()

        logger.info(f"데이터 로드 완료: 학생 {len(self.students)}명, 응답 {len(self.responses)}개")
        return len(self.responses) > 0

    def convert_to_network_data(self):
        """설문 응답을 네트워크 데이터 형식으로 변환"""
        if not self.students:
            raise ValueError("먼저 load_data()를 호출하세요")

        # 노드 생성 (모든 학생)
        nodes = []
        id_to_idx = {}  # student_id -> node index

        for idx, (student_id, student) in enumerate(self.students.items()):
            nodes.append({
                'id': student.name,  # 이름을 ID로 사용 (시각화용)
                'label': student.name,
                'name': student.name,
                'student_id': student_id,
                'group': 1
            })
            id_to_idx[student_id] = student.name

        # 엣지 생성 (설문 응답 기반)
        edges = []
        edge_counts = {}  # (from, to, type) -> count

        for response in self.responses:
            respondent_id = response.student_id
            if respondent_id not in id_to_idx:
                continue

            source_name = id_to_idx[respondent_id]
            response_data = response.responses or {}

            # 각 관계 유형별 처리
            for rel_key, rel_config in self.RELATIONSHIP_WEIGHTS.items():
                target_ids = response_data.get(rel_key, [])
                if not target_ids:
                    continue

                # 문자열인 경우 리스트로 변환
                if isinstance(target_ids, str):
                    target_ids = [target_ids]

                for target_id in target_ids:
                    # target_id를 정수로 변환
                    try:
                        target_id = int(target_id)
                    except (ValueError, TypeError):
                        continue

                    if target_id not in id_to_idx:
                        continue

                    target_name = id_to_idx[target_id]
                    edge_key = (source_name, target_name, rel_config['type'])

                    if edge_key in edge_counts:
                        edge_counts[edge_key] += rel_config['weight']
                    else:
                        edge_counts[edge_key] = rel_config['weight']

        # 엣지 리스트 생성
        for (source, target, rel_type), weight in edge_counts.items():
            edges.append({
                'from': source,
                'to': target,
                'source': source,
                'target': target,
                'type': rel_type,
                'weight': weight
            })

        self.network_data = {
            'nodes': nodes,
            'edges': edges,
            'question_types': list(self.RELATIONSHIP_WEIGHTS.keys())
        }

        logger.info(f"네트워크 데이터 변환 완료: 노드 {len(nodes)}개, 엣지 {len(edges)}개")
        return self.network_data

    def analyze(self):
        """네트워크 분석 실행"""
        if not self.network_data:
            self.convert_to_network_data()

        if not self.network_data['edges']:
            raise ValueError("분석할 관계 데이터가 없습니다. 설문 응답을 먼저 수집해주세요.")

        # NetworkAnalyzer로 분석
        self.analyzer = NetworkAnalyzer(self.network_data)
        self.analyzer.detect_communities()

        # 분석 결과 구성
        metrics = self.analyzer.get_centrality_metrics()
        communities = self.analyzer.get_communities()

        self.analysis_result = {
            'network_data': {
                'nodes': [{'id': n['id'], 'label': n['label']} for n in self.network_data['nodes']],
                'edges': [{'source': e['source'], 'target': e['target'], 'weight': e['weight']}
                          for e in self.network_data['edges']]
            },
            'metrics': metrics,
            'communities': communities,
            'summary': self.analyzer.generate_summary(),
            'stats': self.analyzer.get_summary_statistics()
        }

        logger.info("네트워크 분석 완료")
        return self.analysis_result

    def save_result(self):
        """분석 결과를 DB에 저장"""
        if not self.analysis_result:
            raise ValueError("먼저 analyze()를 호출하세요")

        # 기존 분석 결과 삭제
        AnalysisResult.query.filter_by(classroom_id=self.classroom_id).delete()

        # 새 분석 결과 저장
        result = AnalysisResult(
            classroom_id=self.classroom_id,
            network_data=self.analysis_result['network_data'],
            metrics=self.analysis_result['metrics'],
            communities=self.analysis_result['communities']
        )
        db.session.add(result)
        db.session.commit()

        logger.info(f"분석 결과 저장 완료: classroom_id={self.classroom_id}")
        return result.id

    def get_ai_interpretation(self, api_manager=None):
        """AI를 사용하여 분석 결과 해석"""
        if not self.analysis_result:
            raise ValueError("먼저 analyze()를 호출하세요")

        # API 매니저가 없으면 기본 해석 반환
        if not api_manager:
            return self._get_default_interpretation()

        try:
            summary = self.analysis_result.get('summary', '')
            stats = self.analysis_result.get('stats', {})
            communities = self.analysis_result.get('communities', {})

            # AI 프롬프트 구성
            prompt = self._build_interpretation_prompt(summary, stats, communities)

            # AI 텍스트 생성 요청 (JSON이 아닌 텍스트)
            interpretation = api_manager.generate_text(prompt)

            if interpretation and isinstance(interpretation, str):
                return interpretation
            else:
                return self._get_default_interpretation()

        except Exception as e:
            logger.error(f"AI 해석 생성 중 오류: {str(e)}")
            return self._get_default_interpretation()

    def _build_interpretation_prompt(self, summary, stats, communities):
        """AI 해석을 위한 프롬프트 생성"""
        num_students = stats.get('nodes_count', 0)
        num_edges = stats.get('edges_count', 0)
        density = stats.get('density', 0)
        num_communities = len(communities) if communities else 0

        # 고립 학생 확인
        isolated_nodes = self.analyzer.find_isolated_nodes(threshold=0.05) if self.analyzer else []

        prompt = f"""당신은 학급 관계 분석 전문가입니다. 다음 학급의 소셜 네트워크 분석 결과를 바탕으로 교사에게 도움이 되는 해석과 조언을 제공해주세요.

## 분석 데이터
- 학급 이름: {self.classroom.name}
- 학생 수: {num_students}명
- 관계 수: {num_edges}개
- 네트워크 밀도: {density:.4f}
- 발견된 그룹 수: {num_communities}개
- 고립 우려 학생 수: {len(isolated_nodes)}명

## 기본 분석 요약
{summary}

## 요청사항
1. 이 학급의 전반적인 관계 특성을 2-3문장으로 요약해주세요.
2. 관계 형성에서 주목할 만한 긍정적인 점을 알려주세요.
3. 교사가 관심을 가져야 할 부분(고립 학생, 그룹 간 연결 부족 등)을 구체적으로 알려주세요.
4. 학급 관계 개선을 위한 구체적인 활동이나 개입 방안을 2-3가지 제안해주세요.

친절하고 전문적인 어조로 작성해주세요. 특정 학생 이름은 언급하지 마세요."""

        return prompt

    def _get_default_interpretation(self):
        """기본 해석 생성 (AI 사용 불가시)"""
        if not self.analysis_result:
            return "분석 결과가 없습니다."

        stats = self.analysis_result.get('stats', {})
        communities = self.analysis_result.get('communities', {})
        isolated_nodes = self.analyzer.find_isolated_nodes(threshold=0.05) if self.analyzer else []

        interpretation = []
        interpretation.append("## 학급 관계 분석 결과\n")

        # 전반적 특성
        density = stats.get('density', 0)
        if density > 0.3:
            interpretation.append("이 학급은 **높은 관계 밀도**를 보이며, 학생들 간의 연결이 활발합니다.")
        elif density > 0.15:
            interpretation.append("이 학급은 **보통 수준의 관계 밀도**를 보입니다.")
        else:
            interpretation.append("이 학급의 관계 밀도가 **다소 낮은 편**입니다. 학생들 간의 교류 기회를 늘려주세요.")

        # 그룹 분석
        num_communities = len(communities) if communities else 0
        if num_communities > 1:
            interpretation.append(f"\n\n학급 내 **{num_communities}개의 친구 그룹**이 발견되었습니다.")
            if num_communities > 4:
                interpretation.append("그룹이 다소 많이 분리되어 있어, 그룹 간 교류 활동을 권장합니다.")

        # 고립 학생
        if isolated_nodes:
            interpretation.append(f"\n\n### 주의가 필요한 부분")
            interpretation.append(f"관계 형성에 어려움을 겪고 있을 수 있는 학생이 **{len(isolated_nodes)}명** 있습니다.")
            interpretation.append("이 학생들에게 자연스럽게 또래와 어울릴 수 있는 기회를 제공해주세요.")

        # 제안
        interpretation.append("\n\n### 추천 활동")
        interpretation.append("1. **모둠 활동 시 의도적 배치**: 서로 다른 그룹의 학생들을 섞어 새로운 관계 형성 기회 제공")
        interpretation.append("2. **협력 게임/프로젝트**: 전체 학급이 함께 참여하는 활동으로 연대감 강화")
        interpretation.append("3. **또래 멘토링**: 관계가 넓은 학생과 고립 우려 학생의 자연스러운 연결")

        return "\n".join(interpretation)

    @classmethod
    def run_analysis(cls, classroom_id: int, api_manager=None):
        """분석 전체 과정 실행 (편의 메서드)"""
        analyzer = cls(classroom_id)

        if not analyzer.load_data():
            raise ValueError("설문 응답이 없습니다. 학생들의 응답을 먼저 수집해주세요.")

        analyzer.convert_to_network_data()
        analyzer.analyze()
        analyzer.save_result()

        interpretation = analyzer.get_ai_interpretation(api_manager)

        # 다층 분석 실행
        multilayer_result = analyzer.run_multilayer_analysis()

        return {
            'success': True,
            'classroom_id': classroom_id,
            'classroom_name': analyzer.classroom.name,
            'network_data': analyzer.analysis_result['network_data'],
            'metrics': analyzer.analysis_result['metrics'],
            'communities': analyzer.analysis_result['communities'],
            'summary': analyzer.analysis_result['summary'],
            'stats': analyzer.analysis_result['stats'],
            'interpretation': interpretation,
            'multilayer': multilayer_result.get('layers', {}),
            'avoidance_warnings': multilayer_result.get('avoidance_warnings', {}),
            'cross_layer': multilayer_result.get('cross_layer', {})
        }

    def run_multilayer_analysis(self):
        """다층 네트워크 분석 실행"""
        from app.services.multilayer_analyzer import MultiLayerNetworkAnalyzer
        from app.services.avoidance_analyzer import AvoidanceWarningSystem

        try:
            # MultiLayerNetworkAnalyzer 실행
            ml_analyzer = MultiLayerNetworkAnalyzer(self.students, self.responses)
            ml_analyzer.build_layers()
            ml_analyzer.analyze_all_layers()

            # 회피 경고 분석
            avoidance_graph = ml_analyzer.layers.get('avoidance')
            positive_layers = {
                k: v for k, v in ml_analyzer.layers.items()
                if k != 'avoidance'
            }

            avoidance_warnings = {}
            if avoidance_graph and avoidance_graph.number_of_edges() > 0:
                warning_system = AvoidanceWarningSystem(avoidance_graph, positive_layers)
                avoidance_warnings = warning_system.analyze()

            return {
                'layers': ml_analyzer.layer_metrics,
                'cross_layer': ml_analyzer.cross_layer_metrics,
                'avoidance_warnings': avoidance_warnings
            }

        except Exception as e:
            logger.error(f"다층 분석 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'layers': {},
                'cross_layer': {},
                'avoidance_warnings': {}
            }

    @classmethod
    def get_layer_analysis(cls, classroom_id: int, layer_type: str):
        """특정 레이어의 분석 결과 반환"""
        from app.services.multilayer_analyzer import MultiLayerNetworkAnalyzer

        analyzer = cls(classroom_id)
        if not analyzer.load_data():
            raise ValueError("설문 응답이 없습니다.")

        ml_analyzer = MultiLayerNetworkAnalyzer(analyzer.students, analyzer.responses)
        ml_analyzer.build_layers()
        ml_analyzer.analyze_all_layers()

        if layer_type not in ml_analyzer.layers and layer_type != 'combined':
            raise ValueError(f"유효하지 않은 레이어 유형: {layer_type}")

        return {
            'layer_type': layer_type,
            'network_data': ml_analyzer.get_layer_network_data(layer_type),
            'metrics': ml_analyzer.layer_metrics.get(layer_type, {}),
            'config': ml_analyzer.RELATIONSHIP_TYPES.get(layer_type, {})
        }

    @classmethod
    def get_avoidance_warnings(cls, classroom_id: int):
        """회피 경고 분석 결과만 반환"""
        from app.services.multilayer_analyzer import MultiLayerNetworkAnalyzer
        from app.services.avoidance_analyzer import AvoidanceWarningSystem

        analyzer = cls(classroom_id)
        if not analyzer.load_data():
            raise ValueError("설문 응답이 없습니다.")

        ml_analyzer = MultiLayerNetworkAnalyzer(analyzer.students, analyzer.responses)
        ml_analyzer.build_layers()

        avoidance_graph = ml_analyzer.layers.get('avoidance')
        positive_layers = {k: v for k, v in ml_analyzer.layers.items() if k != 'avoidance'}

        if not avoidance_graph or avoidance_graph.number_of_edges() == 0:
            return {
                'warnings': [],
                'patterns': {},
                'summary': {
                    'total_warnings': 0,
                    'requires_attention': False,
                    'overall_risk': 'NONE'
                }
            }

        warning_system = AvoidanceWarningSystem(avoidance_graph, positive_layers)
        return warning_system.analyze()

    @classmethod
    def get_student_profile(cls, classroom_id: int, student_name: str):
        """특정 학생의 다층 프로필 반환"""
        from app.services.multilayer_analyzer import MultiLayerNetworkAnalyzer

        analyzer = cls(classroom_id)
        if not analyzer.load_data():
            raise ValueError("설문 응답이 없습니다.")

        ml_analyzer = MultiLayerNetworkAnalyzer(analyzer.students, analyzer.responses)
        ml_analyzer.build_layers()

        return ml_analyzer.get_student_profile(student_name)
