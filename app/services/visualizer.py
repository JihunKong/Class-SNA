"""
네트워크 시각화 모듈
Flask 버전 - Streamlit 의존성 제거
"""
import networkx as nx
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import logging
import base64
from io import BytesIO
import json
import warnings

# 경고 비활성화
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# 로깅 설정
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# 한글 로마자 변환 함수
SURNAMES = {
    '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung',
    '강': 'Kang', '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim',
    '한': 'Han', '오': 'Oh', '서': 'Seo', '신': 'Shin', '권': 'Kwon',
    '황': 'Hwang', '안': 'An', '송': 'Song', '전': 'Jeon', '홍': 'Hong',
    '유': 'Yoo', '고': 'Ko', '문': 'Moon', '양': 'Yang', '손': 'Son',
    '배': 'Bae', '백': 'Baek', '남': 'Nam', '하': 'Ha'
}


def romanize_korean(text):
    """한글 텍스트를 로마자로 변환"""
    if not text or not isinstance(text, str):
        return "Unknown"

    if not any(c for c in text if ord('가') <= ord(c) <= ord('힣')):
        return text

    korean_to_roman = {
        '가': 'ga', '나': 'na', '다': 'da', '라': 'ra', '마': 'ma', '바': 'ba', '사': 'sa',
        '아': 'a', '자': 'ja', '차': 'cha', '카': 'ka', '타': 'ta', '파': 'pa', '하': 'ha',
        **SURNAMES
    }

    result = ""
    for char in text:
        if '가' <= char <= '힣':
            if char in korean_to_roman:
                result += korean_to_roman[char]
            else:
                result += 'x'
        else:
            result += char

    return result


class NetworkVisualizer:
    """인터랙티브 네트워크 시각화를 담당하는 클래스"""

    def __init__(self, network_data=None, metrics=None, communities=None):
        """NetworkVisualizer 초기화

        Args:
            network_data: 네트워크 데이터 (nodes, edges)
            metrics: 중심성 지표 딕셔너리
            communities: 커뮤니티 정보 딕셔너리
        """
        self.network_data = network_data or {}
        self.metrics = metrics or {}
        self.communities = communities or {}
        self.G = self._build_graph()

    def _build_graph(self):
        """네트워크 데이터에서 NetworkX 그래프 생성"""
        G = nx.DiGraph()

        if not self.network_data:
            return G

        # 노드 추가
        nodes = self.network_data.get('nodes', [])
        if isinstance(nodes, pd.DataFrame):
            nodes = nodes.to_dict('records')

        for node in nodes:
            if isinstance(node, dict):
                node_id = node.get('name', node.get('id', str(node)))
                G.add_node(node_id, **node)
            else:
                G.add_node(str(node))

        # 엣지 추가
        edges = self.network_data.get('edges', [])
        if isinstance(edges, pd.DataFrame):
            edges = edges.to_dict('records')

        for edge in edges:
            if isinstance(edge, dict):
                source = edge.get('source', edge.get('from'))
                target = edge.get('target', edge.get('to'))
                weight = edge.get('weight', 1)

                # ID를 이름으로 변환
                if isinstance(source, int):
                    source = self._get_node_name(source)
                if isinstance(target, int):
                    target = self._get_node_name(target)

                if source and target:
                    G.add_edge(source, target, weight=weight)

        return G

    def _get_node_name(self, node_id):
        """노드 ID로 이름 조회"""
        nodes = self.network_data.get('nodes', [])
        if isinstance(nodes, pd.DataFrame):
            nodes = nodes.to_dict('records')

        for node in nodes:
            if isinstance(node, dict):
                if node.get('id') == node_id:
                    return node.get('name', str(node_id))
        return str(node_id)

    def generate_pyvis_html(self, height="600px", width="100%", layout="barnes_hut"):
        """PyVis 기반 대화형 네트워크 HTML 생성

        Returns:
            str: HTML 문자열
        """
        try:
            net = Network(height=height, width=width, directed=True, notebook=False)

            # 물리 엔진 설정
            if layout == "barnes_hut":
                physics_options = {
                    "barnesHut": {
                        "gravitationalConstant": -6000,
                        "centralGravity": 0.2,
                        "springLength": 160,
                        "springConstant": 0.05,
                        "damping": 0.09,
                        "avoidOverlap": 1.0
                    }
                }
            else:
                physics_options = {
                    "forceAtlas2Based": {
                        "gravitationalConstant": -60,
                        "centralGravity": 0.015,
                        "springLength": 120,
                        "springConstant": 0.1,
                        "damping": 0.4,
                    }
                }

            # 네트워크 옵션 설정
            options = {
                "nodes": {
                    "font": {
                        "size": 16,
                        "face": "Noto Sans KR, sans-serif",
                        "color": "#000000",
                        "strokeWidth": 3,
                        "strokeColor": "#ffffff"
                    },
                    "borderWidth": 3,
                    "shadow": True,
                    "shape": "dot"
                },
                "edges": {
                    "color": {"color": "#444444", "inherit": False},
                    "smooth": {"enabled": True, "type": "dynamic"},
                    "width": 2,
                    "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}
                },
                "interaction": {
                    "dragNodes": True,
                    "hover": True,
                    "navigationButtons": True,
                    "zoomView": True
                },
                "physics": {
                    "enabled": True,
                    "stabilization": {"enabled": True, "iterations": 1000},
                    **physics_options
                }
            }

            net.options = options

            # 커뮤니티 색상 맵
            color_map = ["#3F51B5", "#E91E63", "#FFC107", "#009688", "#9C27B0",
                         "#03A9F4", "#F44336", "#4CAF50", "#673AB7", "#FF5722"]

            # 노드 추가
            for node in self.G.nodes():
                size = 20
                color = "#97C2FC"

                # 크기 계산 (인기도 기반)
                if 'in_degree' in self.metrics and node in self.metrics['in_degree']:
                    size = 25 + min(20, self.metrics['in_degree'][node] * 35)

                # 색상 계산 (커뮤니티 기반)
                if self.communities and node in self.communities:
                    comm = self.communities[node]
                    if isinstance(comm, (int, float)) and 0 <= comm < len(color_map):
                        color = color_map[int(comm)]

                # 툴팁 생성
                title = f"{node}\n"
                if 'in_degree' in self.metrics and node in self.metrics['in_degree']:
                    title += f"인기도: {self.metrics['in_degree'][node]:.3f}\n"
                if 'out_degree' in self.metrics and node in self.metrics['out_degree']:
                    title += f"활동성: {self.metrics['out_degree'][node]:.3f}\n"
                if 'betweenness' in self.metrics and node in self.metrics['betweenness']:
                    title += f"매개성: {self.metrics['betweenness'][node]:.3f}\n"

                title += f"받은 선택: {self.G.in_degree(node)}명\n"
                title += f"한 선택: {self.G.out_degree(node)}명"

                if self.communities and node in self.communities:
                    title += f"\n그룹: {self.communities[node]}"

                net.add_node(node, label=str(node), title=title, color=color, size=size)

            # 엣지 추가
            for u, v, data in self.G.edges(data=True):
                width = data.get('weight', 1) * 2
                title = f"{u} → {v}"
                if 'weight' in data and data['weight'] > 1:
                    title += f"\n가중치: {data['weight']}"

                net.add_edge(u, v, title=title, width=width)

            # HTML 생성
            html = net.generate_html()

            # 커스텀 스타일 추가
            custom_style = """
            <style>
                #mynetwork {
                    width: 100%;
                    height: 100%;
                    border: none;
                    background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
                    border-radius: 16px;
                }
                .vis-tooltip {
                    font-family: 'Noto Sans KR', sans-serif;
                    font-size: 14px;
                    background: rgba(255,255,255,0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 8px;
                    padding: 10px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                }
            </style>
            """

            html = html.replace("</head>", custom_style + "</head>")

            return html

        except Exception as e:
            logger.error(f"PyVis 네트워크 생성 중 오류: {str(e)}")
            return f"<div class='error'>네트워크 시각화 오류: {str(e)}</div>"

    def generate_plotly_json(self, layout="fruchterman", width=900, height=700):
        """Plotly 네트워크 그래프를 JSON으로 생성

        Returns:
            dict: Plotly JSON 데이터
        """
        try:
            G = self.G

            if G.number_of_nodes() == 0:
                return {"error": "네트워크 데이터가 없습니다"}

            # 레이아웃 알고리즘 적용
            if layout == "circular":
                pos = nx.circular_layout(G)
            elif layout == "spring":
                pos = nx.spring_layout(G, seed=42, k=0.3)
            elif layout == "kamada":
                pos = nx.kamada_kawai_layout(G)
            else:
                pos = nx.fruchterman_reingold_layout(G, seed=42)

            # 노드 데이터 준비
            node_x, node_y, node_text, node_size, node_color = [], [], [], [], []

            color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(str(node))

                # 크기 계산
                if 'in_degree' in self.metrics and node in self.metrics['in_degree']:
                    size = 15 + self.metrics['in_degree'][node] * 50
                else:
                    size = 15 + G.in_degree(node) * 2
                node_size.append(max(10, min(size, 50)))

                # 색상 계산
                if self.communities and node in self.communities:
                    comm = self.communities[node]
                    color = color_palette[int(comm) % len(color_palette)]
                else:
                    color = '#1f77b4'
                node_color.append(color)

            # 엣지 데이터 준비
            edge_x, edge_y = [], []
            for u, v in G.edges():
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            # Plotly 그래프 구성
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.5, color='rgba(150,150,150,0.6)'),
                hoverinfo='none',
                mode='lines'
            )

            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                text=node_text,
                textposition="top center",
                hoverinfo='text',
                marker=dict(
                    color=node_color,
                    size=node_size,
                    line=dict(color='black', width=1)
                )
            )

            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='학급 관계 네트워크',
                    showlegend=False,
                    hovermode='closest',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    width=width,
                    height=height,
                    plot_bgcolor='rgba(248,249,250,1)',
                    paper_bgcolor='rgba(248,249,250,1)'
                )
            )

            return fig.to_json()

        except Exception as e:
            logger.error(f"Plotly 네트워크 생성 중 오류: {str(e)}")
            return {"error": str(e)}

    def get_centrality_chart_data(self, metric="in_degree", top_n=10):
        """중심성 지표 차트 데이터 반환

        Returns:
            dict: 차트 데이터 (labels, values)
        """
        try:
            if metric not in self.metrics:
                return {"error": f"지표 {metric}이(가) 존재하지 않습니다"}

            metric_values = self.metrics[metric]

            # 값 정제
            processed = {}
            for k, v in metric_values.items():
                if isinstance(v, list):
                    processed[k] = v[0] if v else 0
                elif isinstance(v, (int, float)):
                    processed[k] = v
                else:
                    try:
                        processed[k] = float(v)
                    except (ValueError, TypeError):
                        processed[k] = 0

            # 정렬 및 상위 N개 추출
            sorted_items = sorted(processed.items(), key=lambda x: x[1], reverse=True)[:top_n]

            return {
                'labels': [item[0] for item in sorted_items],
                'values': [round(item[1], 4) for item in sorted_items],
                'metric': metric
            }

        except Exception as e:
            logger.error(f"중심성 차트 데이터 생성 중 오류: {str(e)}")
            return {"error": str(e)}

    def get_community_data(self):
        """커뮤니티 정보 반환

        Returns:
            dict: 커뮤니티별 학생 목록
        """
        try:
            if not self.communities:
                return {"count": 0, "groups": {}}

            # 커뮤니티별 그룹화
            groups = {}
            for node, comm_id in self.communities.items():
                comm_str = str(comm_id)
                if comm_str not in groups:
                    groups[comm_str] = []
                groups[comm_str].append(str(node))

            return {
                "count": len(groups),
                "groups": groups
            }

        except Exception as e:
            logger.error(f"커뮤니티 데이터 생성 중 오류: {str(e)}")
            return {"error": str(e)}

    def get_network_stats(self):
        """네트워크 통계 정보 반환"""
        try:
            G = self.G

            stats = {
                'node_count': G.number_of_nodes(),
                'edge_count': G.number_of_edges(),
                'density': round(nx.density(G), 4) if G.number_of_nodes() > 0 else 0,
                'community_count': len(set(self.communities.values())) if self.communities else 0
            }

            # 연결 요소 수
            if G.number_of_nodes() > 0:
                try:
                    stats['connected_components'] = nx.number_weakly_connected_components(G)
                except Exception:
                    stats['connected_components'] = 1

            return stats

        except Exception as e:
            logger.error(f"네트워크 통계 생성 중 오류: {str(e)}")
            return {"error": str(e)}
