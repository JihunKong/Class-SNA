"""
다층 네트워크 분석기
7가지 관계 유형을 개별 레이어로 분석하는 클래스
"""
import networkx as nx
import community as community_louvain
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class MultiLayerNetworkAnalyzer:
    """7가지 관계 유형을 개별 레이어로 분석하는 클래스"""

    RELATIONSHIP_TYPES = {
        'friends': {
            'color': '#3b82f6',
            'label': '친구',
            'positive': True,
            'weight': 1.0,
            'description': '친하게 지내고 싶은 친구'
        },
        'helpers': {
            'color': '#22c55e',
            'label': '도움',
            'positive': True,
            'weight': 0.8,
            'description': '공부나 과제할 때 도움을 주는 친구'
        },
        'teammates': {
            'color': '#a855f7',
            'label': '협력',
            'positive': True,
            'weight': 0.9,
            'description': '모둠 활동을 함께 하고 싶은 친구'
        },
        'leaders': {
            'color': '#f59e0b',
            'label': '리더',
            'positive': True,
            'weight': 0.7,
            'description': '의견을 잘 이끄는 친구'
        },
        'trust': {
            'color': '#ec4899',
            'label': '신뢰',
            'positive': True,
            'weight': 1.0,
            'description': '비밀을 털어놓을 수 있는 친구'
        },
        'communication': {
            'color': '#14b8a6',
            'label': '소통',
            'positive': True,
            'weight': 0.6,
            'description': '자주 대화하는 친구'
        },
        'avoidance': {
            'color': '#ef4444',
            'label': '회피',
            'positive': False,
            'weight': 1.0,
            'description': '함께 활동하기 어려운 친구'
        }
    }

    def __init__(self, students: Dict[int, Any], responses: List[Any]):
        """
        Args:
            students: {student_id: Student 객체} 딕셔너리
            responses: SurveyResponse 객체 리스트
        """
        self.students = students
        self.responses = responses
        self.layers: Dict[str, nx.DiGraph] = {}
        self.combined_graph: Optional[nx.DiGraph] = None
        self.layer_metrics: Dict[str, Dict] = {}
        self.cross_layer_metrics: Dict = {}

        # ID -> 이름 매핑
        self.id_to_name = {s_id: s.name for s_id, s in students.items()}
        self.name_to_id = {s.name: s_id for s_id, s in students.items()}

    def build_layers(self) -> Dict[str, nx.DiGraph]:
        """각 관계 유형별 DiGraph 생성"""
        # 모든 학생을 노드로 추가할 기본 노드 목록
        all_nodes = list(self.id_to_name.values())

        for rel_type in self.RELATIONSHIP_TYPES:
            G = nx.DiGraph()

            # 모든 학생을 노드로 추가
            for name in all_nodes:
                G.add_node(name, label=name)

            # 해당 관계 유형의 엣지 추가
            for response in self.responses:
                respondent_id = response.student_id
                if respondent_id not in self.id_to_name:
                    continue

                source_name = self.id_to_name[respondent_id]
                response_data = response.responses or {}

                target_ids = response_data.get(rel_type, [])
                if not target_ids:
                    continue

                # 문자열인 경우 리스트로 변환
                if isinstance(target_ids, str):
                    target_ids = [target_ids]

                for target_id in target_ids:
                    try:
                        target_id = int(target_id)
                    except (ValueError, TypeError):
                        continue

                    if target_id not in self.id_to_name:
                        continue

                    target_name = self.id_to_name[target_id]

                    # 기존 엣지가 있으면 가중치 증가
                    if G.has_edge(source_name, target_name):
                        G[source_name][target_name]['weight'] += 1
                    else:
                        G.add_edge(source_name, target_name, weight=1)

            self.layers[rel_type] = G
            logger.info(f"레이어 '{rel_type}' 생성 완료: 노드 {G.number_of_nodes()}개, 엣지 {G.number_of_edges()}개")

        # 통합 그래프 생성
        self._build_combined_graph()

        return self.layers

    def _build_combined_graph(self):
        """모든 레이어를 통합한 그래프 생성 (긍정적 관계만)"""
        self.combined_graph = nx.DiGraph()

        # 모든 노드 추가
        for name in self.id_to_name.values():
            self.combined_graph.add_node(name, label=name)

        # 모든 긍정적 레이어의 엣지 통합
        edge_weights = defaultdict(float)

        for rel_type, G in self.layers.items():
            if not self.RELATIONSHIP_TYPES[rel_type]['positive']:
                continue  # 회피 관계는 제외

            type_weight = self.RELATIONSHIP_TYPES[rel_type]['weight']

            for u, v, data in G.edges(data=True):
                edge_weights[(u, v)] += data.get('weight', 1) * type_weight

        # 통합 엣지 추가
        for (u, v), weight in edge_weights.items():
            self.combined_graph.add_edge(u, v, weight=weight)

        logger.info(f"통합 그래프 생성 완료: 엣지 {self.combined_graph.number_of_edges()}개")

    def analyze_all_layers(self) -> Dict[str, Dict]:
        """모든 레이어 분석"""
        if not self.layers:
            self.build_layers()

        for rel_type, G in self.layers.items():
            self.layer_metrics[rel_type] = self._analyze_single_layer(G, rel_type)

        # 통합 그래프 분석
        if self.combined_graph:
            self.layer_metrics['combined'] = self._analyze_single_layer(
                self.combined_graph, 'combined'
            )

        # 레이어 간 분석
        self.cross_layer_metrics = self._calculate_cross_layer_metrics()

        return self.layer_metrics

    def _analyze_single_layer(self, G: nx.DiGraph, layer_type: str) -> Dict:
        """단일 레이어 분석"""
        if G.number_of_edges() == 0:
            return self._empty_metrics()

        metrics = {
            'basic': self._calculate_basic_metrics(G),
            'advanced': self._calculate_advanced_metrics(G),
            'summary': self._generate_layer_summary(G, layer_type),
            'top_students': self._identify_top_students(G, layer_type)
        }

        return metrics

    def _calculate_basic_metrics(self, G: nx.DiGraph) -> Dict:
        """기본 중심성 지표 계산"""
        metrics = {
            'in_degree_centrality': {},
            'out_degree_centrality': {},
            'betweenness_centrality': {},
            'closeness_centrality': {},
            'eigenvector_centrality': {},
            'pagerank': {}
        }

        try:
            metrics['in_degree_centrality'] = dict(nx.in_degree_centrality(G))
            metrics['out_degree_centrality'] = dict(nx.out_degree_centrality(G))
            metrics['betweenness_centrality'] = dict(nx.betweenness_centrality(G))

            try:
                metrics['closeness_centrality'] = dict(nx.closeness_centrality(G))
            except:
                metrics['closeness_centrality'] = {n: 0 for n in G.nodes()}

            try:
                metrics['eigenvector_centrality'] = dict(
                    nx.eigenvector_centrality(G, max_iter=1000)
                )
            except:
                metrics['eigenvector_centrality'] = {n: 0 for n in G.nodes()}

            try:
                metrics['pagerank'] = dict(nx.pagerank(G))
            except:
                metrics['pagerank'] = {n: 0 for n in G.nodes()}

        except Exception as e:
            logger.error(f"기본 지표 계산 오류: {e}")

        return metrics

    def _calculate_advanced_metrics(self, G: nx.DiGraph) -> Dict:
        """고급 SNA 지표 계산"""
        metrics = {}

        try:
            # 상호성 (Reciprocity)
            metrics['reciprocity'] = self._calculate_reciprocity(G)
            metrics['dyad_census'] = self._dyad_census(G)

            # 무방향 그래프로 변환 (일부 지표용)
            G_undirected = G.to_undirected()

            # 삼자관계 분석 (Transitivity)
            metrics['transitivity'] = nx.transitivity(G_undirected)
            metrics['average_clustering'] = nx.average_clustering(G_undirected)
            metrics['local_clustering'] = dict(nx.clustering(G_undirected))

            # 삼자관계 센서스 (Triadic Census)
            try:
                metrics['triadic_census'] = nx.triadic_census(G)
            except:
                metrics['triadic_census'] = {}

            # 클리크 분석 (Clique Detection)
            cliques = list(nx.find_cliques(G_undirected))
            metrics['cliques'] = cliques
            metrics['max_clique_size'] = max(len(c) for c in cliques) if cliques else 0
            metrics['num_cliques'] = len([c for c in cliques if len(c) >= 3])

            # 핵심-주변부 구조 (Core-Periphery)
            metrics['core_number'] = dict(nx.core_number(G_undirected))

            # 네트워크 밀도 및 연결성
            metrics['density'] = nx.density(G)
            metrics['is_weakly_connected'] = nx.is_weakly_connected(G)

            # 컴포넌트 수
            metrics['num_weakly_connected'] = nx.number_weakly_connected_components(G)
            metrics['num_strongly_connected'] = nx.number_strongly_connected_components(G)

            # 커뮤니티 탐지
            try:
                communities = community_louvain.best_partition(G_undirected)
                metrics['communities'] = self._group_by_community(communities)
                metrics['num_communities'] = len(set(communities.values()))
                metrics['modularity'] = community_louvain.modularity(communities, G_undirected)
            except:
                metrics['communities'] = {}
                metrics['num_communities'] = 0
                metrics['modularity'] = 0

        except Exception as e:
            logger.error(f"고급 지표 계산 오류: {e}")

        return metrics

    def _calculate_reciprocity(self, G: nx.DiGraph) -> Dict:
        """상호성 분석"""
        result = {
            'overall': 0,
            'mutual_edges': [],
            'one_way_edges': []
        }

        try:
            result['overall'] = nx.reciprocity(G)

            # 상호 엣지 및 일방 엣지 식별
            for u, v in G.edges():
                if G.has_edge(v, u):
                    if (v, u) not in [(e[0], e[1]) for e in result['mutual_edges']]:
                        result['mutual_edges'].append((u, v))
                else:
                    result['one_way_edges'].append((u, v))

        except Exception as e:
            logger.warning(f"상호성 계산 오류: {e}")

        return result

    def _dyad_census(self, G: nx.DiGraph) -> Dict:
        """다이애드(2자 관계) 센서스"""
        mutual = 0
        asymmetric = 0
        null = 0

        nodes = list(G.nodes())
        n = len(nodes)

        for i in range(n):
            for j in range(i + 1, n):
                u, v = nodes[i], nodes[j]
                has_uv = G.has_edge(u, v)
                has_vu = G.has_edge(v, u)

                if has_uv and has_vu:
                    mutual += 1
                elif has_uv or has_vu:
                    asymmetric += 1
                else:
                    null += 1

        return {
            'mutual': mutual,
            'asymmetric': asymmetric,
            'null': null,
            'total_possible': n * (n - 1) // 2 if n > 1 else 0
        }

    def _group_by_community(self, communities: Dict) -> Dict[str, List]:
        """커뮤니티별 멤버 그룹화"""
        groups = defaultdict(list)
        for node, comm_id in communities.items():
            groups[str(comm_id)].append(node)
        return dict(groups)

    def _identify_top_students(self, G: nx.DiGraph, layer_type: str) -> Dict:
        """레이어 유형에 따른 주요 학생 식별"""
        result = {}

        if G.number_of_edges() == 0:
            return result

        in_degree = dict(G.in_degree())
        out_degree = dict(G.out_degree())

        # 가장 많이 선택받은 학생 (인기)
        sorted_by_in = sorted(in_degree.items(), key=lambda x: x[1], reverse=True)
        result['most_chosen'] = [
            {'name': name, 'count': count}
            for name, count in sorted_by_in[:5] if count > 0
        ]

        # 가장 많이 선택한 학생 (활동적)
        sorted_by_out = sorted(out_degree.items(), key=lambda x: x[1], reverse=True)
        result['most_active'] = [
            {'name': name, 'count': count}
            for name, count in sorted_by_out[:5] if count > 0
        ]

        # 레이어 유형별 특화 분석
        if layer_type == 'leaders':
            result['perceived_leaders'] = result['most_chosen']
        elif layer_type == 'helpers':
            result['key_helpers'] = result['most_chosen']
        elif layer_type == 'trust':
            result['trusted_students'] = result['most_chosen']

        # 고립 학생 (받은 선택이 없거나 매우 적은 학생)
        isolated = [name for name, count in in_degree.items() if count == 0]
        result['isolated'] = isolated

        return result

    def _generate_layer_summary(self, G: nx.DiGraph, layer_type: str) -> Dict:
        """레이어별 요약 정보 생성"""
        config = self.RELATIONSHIP_TYPES.get(layer_type, {})

        return {
            'layer_type': layer_type,
            'label': config.get('label', layer_type),
            'color': config.get('color', '#888888'),
            'positive': config.get('positive', True),
            'description': config.get('description', ''),
            'nodes_count': G.number_of_nodes(),
            'edges_count': G.number_of_edges(),
            'density': nx.density(G) if G.number_of_nodes() > 0 else 0,
            'avg_in_degree': sum(dict(G.in_degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
            'avg_out_degree': sum(dict(G.out_degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0
        }

    def _calculate_cross_layer_metrics(self) -> Dict:
        """레이어 간 비교 분석"""
        result = {
            'layer_correlation': {},
            'role_consistency': {},
            'multiplex_degree': {}
        }

        try:
            # 레이어 간 엣지 중복 분석 (Jaccard similarity)
            positive_layers = [
                (name, G) for name, G in self.layers.items()
                if self.RELATIONSHIP_TYPES[name]['positive']
            ]

            for i, (name1, G1) in enumerate(positive_layers):
                for name2, G2 in positive_layers[i+1:]:
                    edges1 = set(G1.edges())
                    edges2 = set(G2.edges())

                    if edges1 or edges2:
                        intersection = len(edges1 & edges2)
                        union = len(edges1 | edges2)
                        jaccard = intersection / union if union > 0 else 0

                        result['layer_correlation'][f"{name1}-{name2}"] = {
                            'jaccard': jaccard,
                            'overlap_count': intersection
                        }

            # 다층 연결 정도 (학생이 몇 개 레이어에서 활동적인지)
            for node in self.id_to_name.values():
                active_layers = 0
                for rel_type, G in self.layers.items():
                    if not self.RELATIONSHIP_TYPES[rel_type]['positive']:
                        continue
                    if G.in_degree(node) > 0 or G.out_degree(node) > 0:
                        active_layers += 1
                result['multiplex_degree'][node] = active_layers

        except Exception as e:
            logger.error(f"레이어 간 분석 오류: {e}")

        return result

    def _empty_metrics(self) -> Dict:
        """빈 지표 구조 반환"""
        return {
            'basic': {
                'in_degree_centrality': {},
                'out_degree_centrality': {},
                'betweenness_centrality': {},
                'closeness_centrality': {},
                'eigenvector_centrality': {},
                'pagerank': {}
            },
            'advanced': {
                'reciprocity': {'overall': 0, 'mutual_edges': [], 'one_way_edges': []},
                'transitivity': 0,
                'average_clustering': 0,
                'density': 0,
                'communities': {},
                'num_communities': 0
            },
            'summary': {},
            'top_students': {}
        }

    def get_layer_network_data(self, layer_type: str) -> Dict:
        """특정 레이어의 시각화용 데이터 반환"""
        if layer_type not in self.layers:
            return {'nodes': [], 'edges': []}

        G = self.layers[layer_type]
        config = self.RELATIONSHIP_TYPES.get(layer_type, {})

        nodes = [
            {
                'id': node,
                'label': node,
                'color': config.get('color', '#888888')
            }
            for node in G.nodes()
        ]

        edges = [
            {
                'source': u,
                'target': v,
                'weight': data.get('weight', 1)
            }
            for u, v, data in G.edges(data=True)
        ]

        return {'nodes': nodes, 'edges': edges}

    def get_student_profile(self, student_name: str) -> Dict:
        """특정 학생의 전체 레이어 프로필"""
        if student_name not in self.name_to_id:
            return {}

        profile = {
            'name': student_name,
            'layers': {},
            'overall': {}
        }

        for rel_type, G in self.layers.items():
            config = self.RELATIONSHIP_TYPES[rel_type]

            in_degree = G.in_degree(student_name)
            out_degree = G.out_degree(student_name)

            # 해당 학생을 선택한 사람들
            chosen_by = list(G.predecessors(student_name))
            # 해당 학생이 선택한 사람들
            chose = list(G.successors(student_name))

            profile['layers'][rel_type] = {
                'label': config['label'],
                'color': config['color'],
                'positive': config['positive'],
                'received_count': in_degree,
                'given_count': out_degree,
                'chosen_by': chosen_by,
                'chose': chose
            }

        # 전체 요약
        total_received = sum(
            G.in_degree(student_name)
            for rel_type, G in self.layers.items()
            if self.RELATIONSHIP_TYPES[rel_type]['positive']
        )
        total_given = sum(
            G.out_degree(student_name)
            for rel_type, G in self.layers.items()
            if self.RELATIONSHIP_TYPES[rel_type]['positive']
        )

        profile['overall'] = {
            'total_positive_received': total_received,
            'total_positive_given': total_given,
            'avoidance_received': self.layers['avoidance'].in_degree(student_name),
            'avoidance_given': self.layers['avoidance'].out_degree(student_name)
        }

        return profile

    def get_all_results(self) -> Dict:
        """전체 분석 결과 반환"""
        if not self.layer_metrics:
            self.analyze_all_layers()

        return {
            'layers': {
                rel_type: {
                    'network_data': self.get_layer_network_data(rel_type),
                    'metrics': self.layer_metrics.get(rel_type, {}),
                    'config': self.RELATIONSHIP_TYPES.get(rel_type, {})
                }
                for rel_type in self.RELATIONSHIP_TYPES
            },
            'combined': {
                'network_data': self.get_layer_network_data('combined') if self.combined_graph else {},
                'metrics': self.layer_metrics.get('combined', {})
            },
            'cross_layer': self.cross_layer_metrics
        }
