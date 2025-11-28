"""
회피 관계 분석 및 경고 시스템
상호 회피, 집단 회피 등 갈등 패턴 감지
"""
import networkx as nx
import logging
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class AvoidanceWarningSystem:
    """회피 패턴 감지 및 경고 생성 시스템"""

    WARNING_LEVELS = {
        'CRITICAL': {
            'color': '#dc2626',
            'bg_color': '#fef2f2',
            'icon': 'exclamation-triangle',
            'priority': 1,
            'action_required': True,
            'label': '위험'
        },
        'HIGH': {
            'color': '#f97316',
            'bg_color': '#fff7ed',
            'icon': 'alert-circle',
            'priority': 2,
            'action_required': True,
            'label': '주의'
        },
        'MODERATE': {
            'color': '#eab308',
            'bg_color': '#fefce8',
            'icon': 'info',
            'priority': 3,
            'action_required': False,
            'label': '관찰'
        },
        'LOW': {
            'color': '#3b82f6',
            'bg_color': '#eff6ff',
            'icon': 'eye',
            'priority': 4,
            'action_required': False,
            'label': '참고'
        }
    }

    WARNING_TYPES = {
        'MUTUAL_AVOIDANCE': {
            'level': 'CRITICAL',
            'title': '상호 회피 관계',
            'description_template': '{student_a}와(과) {student_b}가 서로를 회피 선택했습니다.',
            'recommendation': '두 학생 간 갈등 가능성이 있습니다. 개별 면담을 통해 관계를 파악하고 중재가 필요할 수 있습니다.'
        },
        'AVOIDANCE_TARGET': {
            'level': 'HIGH',
            'title': '집단 회피 대상',
            'description_template': '{student}을(를) {count}명의 학생이 회피 선택했습니다.',
            'recommendation': '해당 학생의 교우 관계에 문제가 있을 수 있습니다. 담임교사의 관심과 개입이 필요합니다.'
        },
        'AVOIDANCE_INITIATOR': {
            'level': 'MODERATE',
            'title': '회피 성향 학생',
            'description_template': '{student}이(가) {count}명의 학생을 회피 선택했습니다.',
            'recommendation': '학급 적응에 어려움을 겪고 있을 수 있습니다. 또래 관계 형성을 돕는 활동을 고려해주세요.'
        },
        'ISOLATED_WITH_AVOIDANCE': {
            'level': 'HIGH',
            'title': '복합적 고립',
            'description_template': '{student}이(가) 긍정적 관계가 적고 회피 관계도 존재합니다.',
            'recommendation': '학급에서 소외되어 있을 가능성이 높습니다. 자연스러운 또래 연결 기회를 제공해주세요.'
        },
        'AVOIDANCE_CLUSTER': {
            'level': 'MODERATE',
            'title': '그룹 간 갈등',
            'description_template': '두 그룹 사이에 회피 관계가 집중되어 있습니다.',
            'recommendation': '그룹 간 교류를 촉진하는 활동을 통해 관계 개선을 시도해보세요.'
        },
        'ONE_WAY_AVOIDANCE': {
            'level': 'LOW',
            'title': '일방적 회피',
            'description_template': '{student_a}이(가) {student_b}을(를) 회피 선택했습니다.',
            'recommendation': '지속적으로 관찰하며 양자 관계 변화를 모니터링해주세요.'
        }
    }

    def __init__(self, avoidance_graph: nx.DiGraph, positive_layers: Dict[str, nx.DiGraph] = None):
        """
        Args:
            avoidance_graph: 회피 관계 DiGraph
            positive_layers: 긍정적 관계 레이어들 (고립 분석용)
        """
        self.avoidance_graph = avoidance_graph
        self.positive_layers = positive_layers or {}
        self.warnings: List[Dict] = []

    def analyze(self) -> Dict:
        """전체 회피 패턴 분석 실행"""
        self.warnings = []

        # 1. 상호 회피 감지 (CRITICAL)
        mutual_avoidance = self._find_mutual_avoidance()

        # 2. 집단 회피 대상 감지 (HIGH)
        avoidance_targets = self._find_avoidance_targets(threshold=2)

        # 3. 회피 성향 학생 감지 (MODERATE)
        avoidance_initiators = self._find_avoidance_initiators(threshold=2)

        # 4. 복합적 고립 감지 (HIGH)
        isolated_with_avoidance = self._find_isolated_with_avoidance()

        # 5. 그룹 간 갈등 감지 (MODERATE)
        avoidance_clusters = self._detect_avoidance_clusters()

        # 6. 일방적 회피 (LOW) - 다른 경고에 포함되지 않은 것만
        one_way = self._find_remaining_one_way()

        # 결과 정리
        patterns = {
            'mutual_avoidance': mutual_avoidance,
            'avoidance_targets': avoidance_targets,
            'avoidance_initiators': avoidance_initiators,
            'isolated_with_avoidance': isolated_with_avoidance,
            'avoidance_clusters': avoidance_clusters,
            'one_way_avoidance': one_way
        }

        # 경고 정렬 (심각도 순)
        self.warnings.sort(key=lambda w: self.WARNING_LEVELS[w['level']]['priority'])

        # 요약 생성
        summary = self._generate_summary()

        return {
            'warnings': self.warnings,
            'patterns': patterns,
            'summary': summary,
            'analyzed_at': datetime.utcnow().isoformat()
        }

    def _find_mutual_avoidance(self) -> List[Tuple[str, str]]:
        """상호 회피 관계 찾기 (A↔B)"""
        mutual_pairs = []
        seen = set()

        for u, v in self.avoidance_graph.edges():
            if (v, u) not in seen and self.avoidance_graph.has_edge(v, u):
                mutual_pairs.append((u, v))
                seen.add((u, v))

                # 경고 생성
                warning_type = self.WARNING_TYPES['MUTUAL_AVOIDANCE']
                self.warnings.append({
                    'id': f"mutual_{u}_{v}",
                    'type': 'MUTUAL_AVOIDANCE',
                    'level': warning_type['level'],
                    'title': warning_type['title'],
                    'description': warning_type['description_template'].format(
                        student_a=u, student_b=v
                    ),
                    'recommendation': warning_type['recommendation'],
                    'students': [u, v],
                    'data': {'student_a': u, 'student_b': v}
                })

        return mutual_pairs

    def _find_avoidance_targets(self, threshold: int = 2) -> Dict[str, List[str]]:
        """집단 회피 대상 찾기 (N명 이상에게 회피당하는 학생)"""
        targets = {}

        for node in self.avoidance_graph.nodes():
            avoiders = list(self.avoidance_graph.predecessors(node))
            if len(avoiders) >= threshold:
                targets[node] = avoiders

                # 경고 생성
                warning_type = self.WARNING_TYPES['AVOIDANCE_TARGET']
                self.warnings.append({
                    'id': f"target_{node}",
                    'type': 'AVOIDANCE_TARGET',
                    'level': warning_type['level'],
                    'title': warning_type['title'],
                    'description': warning_type['description_template'].format(
                        student=node, count=len(avoiders)
                    ),
                    'recommendation': warning_type['recommendation'],
                    'students': [node],
                    'data': {'student': node, 'avoiders': avoiders, 'count': len(avoiders)}
                })

        return targets

    def _find_avoidance_initiators(self, threshold: int = 2) -> Dict[str, List[str]]:
        """회피 성향이 강한 학생 찾기 (N명 이상을 회피하는 학생)"""
        initiators = {}

        for node in self.avoidance_graph.nodes():
            avoided = list(self.avoidance_graph.successors(node))
            if len(avoided) >= threshold:
                initiators[node] = avoided

                # 경고 생성
                warning_type = self.WARNING_TYPES['AVOIDANCE_INITIATOR']
                self.warnings.append({
                    'id': f"initiator_{node}",
                    'type': 'AVOIDANCE_INITIATOR',
                    'level': warning_type['level'],
                    'title': warning_type['title'],
                    'description': warning_type['description_template'].format(
                        student=node, count=len(avoided)
                    ),
                    'recommendation': warning_type['recommendation'],
                    'students': [node],
                    'data': {'student': node, 'avoided': avoided, 'count': len(avoided)}
                })

        return initiators

    def _find_isolated_with_avoidance(self) -> List[str]:
        """긍정적 관계가 적으면서 회피 관계가 있는 학생"""
        isolated = []

        if not self.positive_layers:
            return isolated

        for node in self.avoidance_graph.nodes():
            # 회피 관계 존재 여부
            avoidance_in = self.avoidance_graph.in_degree(node)
            avoidance_out = self.avoidance_graph.out_degree(node)

            if avoidance_in == 0 and avoidance_out == 0:
                continue

            # 긍정적 관계 총합
            positive_in = 0
            positive_out = 0

            for layer_name, G in self.positive_layers.items():
                if node in G:
                    positive_in += G.in_degree(node)
                    positive_out += G.out_degree(node)

            # 긍정적 관계가 적으면서 회피 관계가 있는 경우
            if positive_in <= 2 and avoidance_in > 0:
                isolated.append(node)

                # 경고 생성
                warning_type = self.WARNING_TYPES['ISOLATED_WITH_AVOIDANCE']
                self.warnings.append({
                    'id': f"isolated_{node}",
                    'type': 'ISOLATED_WITH_AVOIDANCE',
                    'level': warning_type['level'],
                    'title': warning_type['title'],
                    'description': warning_type['description_template'].format(student=node),
                    'recommendation': warning_type['recommendation'],
                    'students': [node],
                    'data': {
                        'student': node,
                        'positive_in': positive_in,
                        'avoidance_in': avoidance_in
                    }
                })

        return isolated

    def _detect_avoidance_clusters(self) -> List[Dict]:
        """그룹 간 회피 패턴 감지"""
        clusters = []

        # 회피 그래프가 너무 작으면 스킵
        if self.avoidance_graph.number_of_edges() < 3:
            return clusters

        try:
            import community as community_louvain

            # 무방향 그래프로 변환하여 커뮤니티 탐지
            undirected = self.avoidance_graph.to_undirected()
            if undirected.number_of_edges() == 0:
                return clusters

            communities = community_louvain.best_partition(undirected)

            # 커뮤니티가 2개 이상인 경우 그룹 간 관계 분석
            community_groups = defaultdict(list)
            for node, comm_id in communities.items():
                community_groups[comm_id].append(node)

            if len(community_groups) >= 2:
                # 그룹 간 회피 엣지 수 계산
                for comm1 in community_groups:
                    for comm2 in community_groups:
                        if comm1 >= comm2:
                            continue

                        cross_edges = 0
                        for node1 in community_groups[comm1]:
                            for node2 in community_groups[comm2]:
                                if self.avoidance_graph.has_edge(node1, node2):
                                    cross_edges += 1
                                if self.avoidance_graph.has_edge(node2, node1):
                                    cross_edges += 1

                        # 양방향 회피가 많은 경우 클러스터로 간주
                        if cross_edges >= 3:
                            clusters.append({
                                'group1': community_groups[comm1],
                                'group2': community_groups[comm2],
                                'cross_edges': cross_edges
                            })

                            # 경고 생성
                            warning_type = self.WARNING_TYPES['AVOIDANCE_CLUSTER']
                            self.warnings.append({
                                'id': f"cluster_{comm1}_{comm2}",
                                'type': 'AVOIDANCE_CLUSTER',
                                'level': warning_type['level'],
                                'title': warning_type['title'],
                                'description': warning_type['description_template'],
                                'recommendation': warning_type['recommendation'],
                                'students': community_groups[comm1] + community_groups[comm2],
                                'data': {
                                    'group1': community_groups[comm1],
                                    'group2': community_groups[comm2],
                                    'cross_edges': cross_edges
                                }
                            })

        except Exception as e:
            logger.warning(f"클러스터 감지 오류: {e}")

        return clusters

    def _find_remaining_one_way(self) -> List[Tuple[str, str]]:
        """다른 경고에 포함되지 않은 일방적 회피 관계"""
        one_way = []

        # 이미 경고에 포함된 학생들
        warned_students = set()
        for w in self.warnings:
            warned_students.update(w.get('students', []))

        for u, v in self.avoidance_graph.edges():
            # 상호 회피가 아닌 경우
            if self.avoidance_graph.has_edge(v, u):
                continue

            # 이미 다른 경고에 포함된 경우 스킵
            if u in warned_students or v in warned_students:
                continue

            one_way.append((u, v))

            # 경고 생성 (많으면 처음 5개만)
            if len(one_way) <= 5:
                warning_type = self.WARNING_TYPES['ONE_WAY_AVOIDANCE']
                self.warnings.append({
                    'id': f"oneway_{u}_{v}",
                    'type': 'ONE_WAY_AVOIDANCE',
                    'level': warning_type['level'],
                    'title': warning_type['title'],
                    'description': warning_type['description_template'].format(
                        student_a=u, student_b=v
                    ),
                    'recommendation': warning_type['recommendation'],
                    'students': [u, v],
                    'data': {'student_a': u, 'student_b': v}
                })

        return one_way

    def _generate_summary(self) -> Dict:
        """경고 요약 생성"""
        level_counts = defaultdict(int)
        type_counts = defaultdict(int)

        for w in self.warnings:
            level_counts[w['level']] += 1
            type_counts[w['type']] += 1

        total_edges = self.avoidance_graph.number_of_edges()
        total_nodes_with_avoidance = len([
            n for n in self.avoidance_graph.nodes()
            if self.avoidance_graph.in_degree(n) > 0 or
               self.avoidance_graph.out_degree(n) > 0
        ])

        requires_attention = level_counts['CRITICAL'] + level_counts['HIGH'] > 0

        return {
            'total_warnings': len(self.warnings),
            'critical_count': level_counts['CRITICAL'],
            'high_count': level_counts['HIGH'],
            'moderate_count': level_counts['MODERATE'],
            'low_count': level_counts['LOW'],
            'type_counts': dict(type_counts),
            'total_avoidance_edges': total_edges,
            'students_with_avoidance': total_nodes_with_avoidance,
            'requires_attention': requires_attention,
            'overall_risk': self._calculate_overall_risk(level_counts)
        }

    def _calculate_overall_risk(self, level_counts: Dict) -> str:
        """전체 위험도 계산"""
        if level_counts['CRITICAL'] >= 2:
            return 'HIGH'
        elif level_counts['CRITICAL'] >= 1 or level_counts['HIGH'] >= 3:
            return 'MODERATE'
        elif level_counts['HIGH'] >= 1:
            return 'LOW'
        else:
            return 'NONE'

    def get_warnings_by_level(self, level: str) -> List[Dict]:
        """특정 심각도의 경고만 반환"""
        return [w for w in self.warnings if w['level'] == level]

    def get_warnings_for_student(self, student_name: str) -> List[Dict]:
        """특정 학생과 관련된 경고 반환"""
        return [w for w in self.warnings if student_name in w.get('students', [])]

    def get_actionable_warnings(self) -> List[Dict]:
        """조치가 필요한 경고만 반환"""
        return [
            w for w in self.warnings
            if self.WARNING_LEVELS[w['level']]['action_required']
        ]

    @staticmethod
    def get_warning_level_info(level: str) -> Dict:
        """경고 레벨 정보 반환"""
        return AvoidanceWarningSystem.WARNING_LEVELS.get(level, {})
