import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import logging
import streamlit as st
import base64
from io import BytesIO
import platform
import re
import warnings
import subprocess

# matplotlib 경고 메시지 필터링 강화 - 모든 폰트 관련 경고 필터링
warnings.filterwarnings("ignore", "Glyph .* missing from current font")
warnings.filterwarnings("ignore", "findfont: Font family .* not found")
warnings.filterwarnings("ignore", category=UserWarning, module='matplotlib')
warnings.filterwarnings("ignore", category=UserWarning, module='plotly')
warnings.filterwarnings("ignore", category=UserWarning, module='pyvis')

# 로깅 설정 - 파일 핸들러 추가하여 로그를 화면에 출력하지 않고 파일로 저장
logging.basicConfig(level=logging.INFO, filename='network_analysis.log', filemode='w')
logger = logging.getLogger(__name__)
# 스트림 핸들러를 제거하여 콘솔에 출력되지 않도록 설정
logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]

# Streamlit Cloud 환경인지 확인하는 함수 - 전역 함수로 정의
def is_streamlit_cloud():
    """Streamlit Cloud 환경인지 확인"""
    return os.getenv("STREAMLIT_RUNTIME") is not None or os.getenv("STREAMLIT_RUN_ON_SAVE") is not None

# 한글 폰트 설정 함수
def set_korean_font():
    """matplotlib에서 한글 폰트를 사용하도록 설정"""
    try:
        # 이미 캐시된 한글 폰트 확인 (세션 상태 활용)
        if 'korean_font_set' in st.session_state and st.session_state['korean_font_set']:
            return
            
        # Streamlit Cloud 환경 또는 로컬 환경에서 사용 가능한 폰트 찾기
        if is_streamlit_cloud():
            # Streamlit Cloud에서는 폰트 설치 안내 메시지 표시
            st.sidebar.markdown("""
            ### 💡 한글 폰트 안내
            **리눅스 환경인 경우:** `sudo apt-get install fonts-nanum` 명령으로 나눔 폰트를 설치할 수 있습니다.
            **한글이 보이지 않을 경우:** 자동으로 영문으로 변환되어 표시됩니다.
            """)
        else:
            # 로컬 환경에서 한글 폰트 설치 안내
            system = platform.system()
            if system == 'Linux':
                try:
                    # 리눅스 환경에서 나눔 폰트 설치 여부 확인
                    nanum_installed = False
                    try:
                        # fc-list 명령어로 나눔 폰트 존재 확인
                        result = subprocess.run(['fc-list', ':lang=ko'], capture_output=True, text=True)
                        nanum_installed = 'Nanum' in result.stdout or '나눔' in result.stdout
                    except:
                        pass
                        
                    if not nanum_installed:
                        # 설치 안내 메시지
                        st.sidebar.markdown("""
                        ### 💡 한글 폰트 설치 필요
                        다음 명령어로 나눔 폰트를 설치하세요:
                        ```bash
                        sudo apt-get update
                        sudo apt-get install fonts-nanum
                        sudo fc-cache -fv
                        ```
                        """)
                except:
                    pass
        
        # 사용 가능한 폰트 목록 확인
        font_list = [f.name for f in fm.fontManager.ttflist]
        
        # 한글 지원 가능한 폰트 후보 목록 (우선순위 순서)
        korean_fonts = [
            'NanumGothicCoding', 'NanumGothic', 'Nanum Gothic', 'Nanum Gothic Coding',
            'NanumBarunGothic', 'Nanum Barun Gothic', 'Malgun Gothic', 'Gulim', 'Batang',
            'AppleGothic', 'Noto Sans KR', 'Noto Sans CJK KR', 'UnDotum', 'Dotum'
        ]
        
        # 시스템에 설치된 한글 폰트 찾기
        found_font = None
        for font in korean_fonts:
            if any(font.lower() == f.lower() for f in font_list):
                found_font = font
                break
            
        # 정확한 이름 매칭이 안 되면 일부 매칭 시도
        if not found_font:
            for font in korean_fonts:
                matching_fonts = [f for f in font_list if font.lower() in f.lower()]
                if matching_fonts:
                    found_font = matching_fonts[0]
                    break
        
        # 폰트 설정
        if found_font:
            plt.rc('font', family=found_font)
            st.session_state['korean_font_set'] = True
            logger.info(f"한글 폰트 설정 완료: {found_font}")
        else:
            plt.rc('font', family='sans-serif')
            logger.warning("한글 폰트를 찾을 수 없습니다.")
        
        # 폰트 설정 확인
        plt.rc('axes', unicode_minus=False)  # 마이너스 기호 깨짐 방지
        
    except Exception as e:
        # 오류 발생 시 기본 폰트 설정
        plt.rc('font', family='sans-serif')
        logger.warning(f"폰트 설정 중 오류 발생: {str(e)}")

# PyVis에 한글 폰트 적용 함수
def apply_korean_font_to_pyvis(net):
    """PyVis 네트워크에 한글 폰트 설정을 적용합니다."""
    try:
        # HTML 헤더에 Google Fonts CDN을 통한 웹폰트 추가
        net.html = net.html.replace("<head>", """<head>
        <link href="https://fonts.googleapis.com/css2?family=Nanum+Gothic&display=swap" rel="stylesheet">
        <style>
        body, html, .vis-network, .vis-label {
            font-family: 'Nanum Gothic', 'Malgun Gothic', sans-serif !important;
        }
        .vis-network div.vis-network-tooltip {
            font-family: 'Nanum Gothic', 'Malgun Gothic', sans-serif !important;
            background-color: rgba(255, 255, 255, 0.9) !important;
            border: 1px solid #ccc !important;
            border-radius: 4px !important;
            padding: 8px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        </style>
        """)
        
        # 네트워크 초기화 후 노드 폰트 설정을 위한 JavaScript 추가
        font_options_script = """
        <script>
        document.addEventListener("DOMContentLoaded", function() {
            // 네트워크가 이미 초기화된 후에 실행
            setTimeout(function() {
                try {
                    // 노드 폰트 옵션 설정
                    var options = {
                        nodes: {
                            font: {
                                face: "'Nanum Gothic', 'Malgun Gothic', sans-serif",
                                size: 14,
                                color: '#000000'
                            }
                        },
                        edges: {
                            font: {
                                face: "'Nanum Gothic', 'Malgun Gothic', sans-serif",
                                size: 12
                            }
                        }
                    };
                    
                    // 네트워크 객체에 옵션 적용
                    if (typeof network !== 'undefined') {
                        network.setOptions(options);
                    }
                } catch(e) {
                    console.error("폰트 설정 중 오류 발생:", e);
                }
            }, 1000); // 충분한 시간을 두고 실행
        });
        </script>
        """
        
        # 스크립트를 HTML 본문 끝에 추가
        if "</body>" in net.html:
            net.html = net.html.replace("</body>", font_options_script + "</body>")
        else:
            net.html += font_options_script
        
        return net
    except Exception as e:
        logger.warning(f"PyVis 한글 폰트 적용 실패: {str(e)}")
        return net

# 한글을 영문으로 변환하는 함수 (폰트 문제 대비)
def romanize_korean(text):
    """한글 이름을 영문으로 변환. 매핑 테이블은 가장 일반적인 발음 변환 규칙 사용"""
    # 한글 문자가 포함되지 않은 경우 원본 그대로 반환
    if not any(ord('가') <= ord(char) <= ord('힣') for char in text):
        return text
        
    # 공백으로 나누어진 경우(이름과 정보가 함께 있는 경우)
    if ' ' in text:
        parts = text.split(' ', 1)
        name = parts[0]
        info = ' ' + parts[1] if len(parts) > 1 else ''
        return romanize_korean(name) + info
        
    # 성씨 딕셔너리 - 한글 성씨를 로마자 표기로 변환 (대표적인 성씨만 포함)
    surnames = {
        '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung', 
        '강': 'Kang', '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim',
        '오': 'Oh', '한': 'Han', '신': 'Shin', '서': 'Seo', '권': 'Kwon',
        '황': 'Hwang', '안': 'Ahn', '송': 'Song', '전': 'Jeon', '홍': 'Hong',
        '유': 'Yoo', '고': 'Ko', '문': 'Moon', '양': 'Yang', '손': 'Son',
        '배': 'Bae', '백': 'Baek', '허': 'Heo', '노': 'Noh', '심': 'Shim',
        '하': 'Ha', '전': 'Jeon', '곽': 'Kwak', '성': 'Sung', '차': 'Cha',
        '주': 'Joo', '우': 'Woo', '구': 'Koo', '나': 'Na', '민': 'Min',
        '유': 'Yoo', '진': 'Jin', '지': 'Ji', '엄': 'Uhm', '편': 'Pyeon'
    }
    
    # 이름이 1글자인 경우 (특수한 처리가 필요한 경우)
    if len(text) == 1:
        return f"Student-{hash(text) % 1000:03d}"
    
    # 2글자 이상인 이름 처리
    surname = text[0]  # 성씨는 첫 글자로 가정
    given_name = text[1:]  # 이름은 나머지 부분
    
    # 매핑 테이블에 있는 성씨면 변환, 없으면 첫 글자를 'S'로 표현
    if surname in surnames:
        romanized = f"{surnames[surname]} {given_name}"
    else:
        # 매핑되지 않은 성씨는 간단한 해시값으로 학생 ID 생성
        romanized = f"Student-{hash(text) % 1000:03d}"
    
    return romanized

class NetworkVisualizer:
    """네트워크 그래프 시각화 클래스"""
    
    def __init__(self, analyzer):
        """NetworkAnalyzer 객체를 받아 초기화"""
        self.analyzer = analyzer
        self.graph = analyzer.graph
        
        # 한글 폰트 설정 및 확인
        set_korean_font()
        self.has_korean_font = self._check_korean_font()
        
        # Streamlit Cloud 환경에서는 자동으로 로마자화 사용
        if is_streamlit_cloud():
            self.has_korean_font = False
            
        # 노드 이름 매핑 (원래 이름 -> 로마자화된 이름)
        self.name_mapping = {}
        if not self.has_korean_font:
            for node in self.graph.nodes():
                self.name_mapping[node] = romanize_korean(node)
        
        self.communities = analyzer.communities
        self.metrics = analyzer.metrics
    
    def _check_korean_font(self):
        """한글 폰트 사용 가능 여부 확인"""
        # Streamlit Cloud 환경에서는 자동으로 False 반환
        if is_streamlit_cloud() or "STREAMLIT" in os.environ:
            logger.warning("Streamlit 환경에서는 한글 폰트를 사용할 수 없습니다. 영문 표기로 대체합니다.")
            return False
        
        try:
            # 한글 문자로 실제 렌더링 테스트
            test_str = "한글"
            fig, ax = plt.subplots(figsize=(1, 1))
            
            # 경고 캡처를 위한 설정
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                ax.text(0.5, 0.5, test_str, fontsize=12)
                plt.savefig(BytesIO())  # 실제 렌더링 강제
                plt.close(fig)
                
                # 폰트 관련 경고가 있는지 확인
                for warning in w:
                    warning_msg = str(warning.message)
                    if "missing from current font" in warning_msg or "not found" in warning_msg:
                        logger.warning("한글 폰트 렌더링 중 문제 발생: 한글 폰트를 찾을 수 없습니다.")
                        logger.warning("노드 레이블을 영문으로 변환합니다.")
                        return False
            
            # 경고가 없으면 한글 폰트 사용 가능으로 판단
            logger.info("한글 폰트 사용 가능 확인됨")
            return True
            
        except Exception as e:
            logger.warning(f"한글 폰트 확인 실패: {str(e)}")
            logger.warning("한글 폰트를 찾을 수 없습니다. 노드 레이블을 영문으로 변환합니다.")
            return False
    
    def _get_display_label(self, node_name, use_romanized=False):
        """표시할 노드 레이블 생성 (한글 폰트 문제시 로마자 변환)"""
        if use_romanized and re.search(r'[가-힣]', node_name):
            return romanize_korean(node_name)
        return node_name
    
    def create_plotly_network(self, layout="fruchterman", width=900, height=700):
        """Plotly를 사용한 네트워크 그래프 생성"""
        try:
            # 노드 정보 준비
            node_x = []
            node_y = []
            node_text = []  # 노드 텍스트 (한글 이름 또는 로마자화된 이름)
            node_size = []  # 노드 크기
            node_color = []  # 노드 색상
            
            # 그래프 레이아웃 계산 - 파라미터 조정하여 노드 간격 최적화
            if layout == "spring":
                pos = nx.spring_layout(self.graph, k=0.5, iterations=50)
            elif layout == "circular":
                pos = nx.circular_layout(self.graph)
            elif layout == "kamada":
                pos = nx.kamada_kawai_layout(self.graph)
            else:  # fruchterman
                pos = nx.fruchterman_reingold_layout(self.graph, k=0.3)
            
            # 노드 중심성 및 커뮤니티 값 가져오기
            in_degree = self.metrics.get('in_degree', {})
            communities = self.communities
            
            # 노드 색상 팔레트 설정 (색약자를 위한 색상)
            color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            # 노드 데이터 구성
            for node in self.graph.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                # 노드 텍스트 (이름) 설정
                display_name = self._get_display_label(node)
                degree_in = in_degree.get(node, 0)
                degree_out = self.metrics.get('out_degree', {}).get(node, 0)
                betweenness = self.metrics.get('betweenness', {}).get(node, 0)
                
                node_text.append(f"이름: {display_name}<br>인기도: {degree_in}<br>친밀도: {degree_out}<br>중재자 역할: {betweenness:.3f}")
                
                # 노드 크기 설정: 연결 중심성(In)에 비례
                size = in_degree.get(node, 0) * 15 + 15  # 크기 증가하여 더 잘 보이게 함
                node_size.append(size)
                
                # 노드 색상 설정: 커뮤니티에 따라
                if node in communities:
                    node_color.append(color_palette[communities[node] % len(color_palette)])
                else:
                    node_color.append('#7f7f7f')  # 기본 회색
            
            # 에지(연결선) 정보 준비
            edge_x = []
            edge_y = []
            edge_width = []
            
            # 에지 데이터 구성
            for edge in self.graph.edges(data=True):
                source, target = edge[0], edge[1]
                x0, y0 = pos[source]
                x1, y1 = pos[target]
                
                # 곡선 에지를 위한 중간점 계산
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)  # 선 구분을 위한 None
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)  # 선 구분을 위한 None
                
                # 에지 두께 설정: 가중치에 비례
                weight = edge[2].get('weight', 1)
                edge_width.append(weight)
            
            # 에지 트레이스 생성
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.5, color='#888'),
                hoverinfo='none',
                mode='lines',
                showlegend=False
            )
            
            # 노드 트레이스 생성
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                hoverinfo='text',
                text=node_text,
                marker=dict(
                    color=node_color,
                    size=node_size,
                    line=dict(width=1.5, color='#444')
                ),
                showlegend=False
            )
            
            # 레이아웃 및 그래프 생성
            layout_config = dict(
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=60),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                width=width,
                height=height,
                title='학급 관계 네트워크 그래프<br><span style="font-size:12px;">크기: 인기도(선택받은 횟수) | 색상: 같은 그룹</span>'
            )
            
            fig = go.Figure(data=[edge_trace, node_trace], layout=layout_config)
            
            return fig
            
        except Exception as e:
            st.error(f"네트워크 그래프 생성 중 오류가 발생했습니다: {str(e)}")
            return None
    
    def create_pyvis_network(self, height="600px", width="100%"):
        """PyVis를 사용한 인터랙티브 네트워크 생성"""
        try:
            # PyVis Network 객체 생성
            net = Network(height=height, width=width, notebook=False, directed=True, 
                         cdn_resources='remote')
            
            # 배경색과 글자색 설정
            net.bgcolor = "#ffffff"
            net.font_color = "black"
            
            # 물리 레이아웃 설정 (더 잘 보이도록 파라미터 조정)
            physics_options = {
                "barnesHut": {
                    "gravitationalConstant": -10000,
                    "centralGravity": 0.4,
                    "springLength": 180,
                    "springConstant": 0.05,
                    "damping": 0.09
                },
                "maxVelocity": 50,
                "minVelocity": 0.75
            }
            
            # 노드와 엣지 인터랙션 설정
            net.set_options("""
            {
                "nodes": {
                    "font": {
                        "size": 14,
                        "face": "Arial"
                    },
                    "borderWidth": 2,
                    "borderWidthSelected": 4,
                    "scaling": {
                        "min": 20,
                        "max": 60
                    }
                },
                "edges": {
                    "arrows": {
                        "to": {
                            "enabled": true,
                            "scaleFactor": 0.5
                        }
                    },
                    "color": {
                        "inherit": false,
                        "color": "#999999",
                        "highlight": "#FF0000",
                        "hover": "#007bff"
                    },
                    "smooth": {
                        "enabled": true,
                        "type": "dynamic"
                    },
                    "width": 1.5,
                    "hoverWidth": 2.5,
                    "selectionWidth": 2.5
                },
                "interaction": {
                    "hover": true,
                    "navigationButtons": true,
                    "multiselect": true,
                    "keyboard": {
                        "enabled": true
                    }
                },
                "physics": {
                    "enabled": true,
                    "barnesHut": {
                        "gravitationalConstant": -10000,
                        "centralGravity": 0.4,
                        "springLength": 180,
                        "springConstant": 0.05,
                        "damping": 0.09
                    },
                    "maxVelocity": 50,
                    "minVelocity": 0.75
                }
            }
            """)
            
            # 중심성 지표 가져오기
            in_degree = self.metrics.get('in_degree', {})
            out_degree = self.metrics.get('out_degree', {})
            betweenness = self.metrics.get('betweenness', {})
            
            # 커뮤니티 정보 가져오기
            communities = self.communities
            
            # 색상 팔레트
            color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            # 노드 추가
            for node in self.graph.nodes:
                # 노드 크기 계산
                size = in_degree.get(node, 0) * 15 + 20  # 크기 증가
                
                # 커뮤니티 기반 색상 할당
                comm_id = communities.get(node, 0)
                color = color_palette[comm_id % len(color_palette)]
                
                # 표시할 이름(라벨) 설정 - 한글 폰트 없을 경우 로마자화
                display_label = self._get_display_label(node)
                
                # 툴팁(hover) 텍스트 설정 - 더 상세한 정보
                title = f"<div style='font-size:14px; font-weight:bold;'>{node}</div>"
                title += f"<hr style='margin:2px'>"
                title += f"<div><b>인기도(In)</b>: {in_degree.get(node, 0)}</div>"
                title += f"<div><b>친밀도(Out)</b>: {out_degree.get(node, 0)}</div>"
                title += f"<div><b>중재자 역할</b>: {betweenness.get(node, 0):.3f}</div>"
                title += f"<div><b>그룹번호</b>: {comm_id}</div>"
                
                # 노드 추가
                net.add_node(
                    node,
                    label=display_label,
                    title=title,
                    size=size,
                    color=color,
                    borderWidth=2,
                    borderWidthSelected=4,
                    font={'color': 'black', 'size': 14}
                )
            
            # 엣지 추가
            for source, target, data in self.graph.edges(data=True):
                weight = data.get('weight', 1)
                edge_type = data.get('type', 'relationship')
                
                # 엣지 색상 설정 - 기본은 회색, 선택 시 빨간색, 호버 시 파란색
                net.add_edge(
                    source, target,
                    width=weight * 1.5,  # 굵기 증가
                    title=f"{source} → {target} ({edge_type})",
                    arrowStrikethrough=True,
                    color={'color': '#999999', 'highlight': '#FF0000', 'hover': '#007bff'}
                )
            
            # 한글 폰트 적용
            net = apply_korean_font_to_pyvis(net)
            
            # 임시 파일로 저장
            temp_dir = tempfile.gettempdir()
            html_path = os.path.join(temp_dir, "network.html")
            net.save_graph(html_path)
            
            # 한글 지원 여부에 따른 안내 메시지
            if not self.has_korean_font:
                st.info("한글 폰트를 사용할 수 없어 이름이 영문으로 표시됩니다. 원래 이름은 도구 팁에서 확인할 수 있습니다.")
                
                # 이름 매핑 테이블 생성 및 표시
                if self.name_mapping:
                    with st.expander("📋 이름 매핑 테이블", expanded=False):
                        mapping_data = {
                            "표시 이름": list(self.name_mapping.values()),
                            "원래 이름": list(self.name_mapping.keys())
                        }
                        mapping_df = pd.DataFrame(mapping_data)
                        st.dataframe(mapping_df)
            
            return html_path
            
        except Exception as e:
            st.error(f"인터랙티브 네트워크 생성 중 오류가 발생했습니다: {str(e)}")
            return None
    
    def create_centrality_plot(self, metric="in_degree", top_n=10):
        """중심성 지표 시각화"""
        try:
            # 지표 선택
            if metric not in self.metrics:
                st.error(f"요청한 중심성 지표({metric})가 존재하지 않습니다.")
                return None
            
            # 선택된 지표 값 가져오기
            metric_values = self.metrics[metric]
            
            # 데이터프레임 변환 및 정렬
            df = pd.DataFrame(metric_values.items(), columns=['이름', '값'])
            df = df.sort_values('값', ascending=False).head(top_n)
            
            # 표시 이름 변환
            if not self.has_korean_font:
                df['표시이름'] = df['이름'].apply(lambda x: self._get_display_label(x))
            else:
                df['표시이름'] = df['이름']
            
            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(df['표시이름'], df['값'], color='skyblue')
            
            # 그래프 스타일링
            ax.set_xlabel('중심성 지표 값')
            
            # 중심성 지표별 적절한 제목 설정
            metric_titles = {
                'in_degree': '인기도 (선택받은 횟수)',
                'out_degree': '친밀도 (선택한 횟수)',
                'betweenness': '중재자 역할',
                'closeness': '정보 접근성'
            }
            title = metric_titles.get(metric, metric)
            ax.set_title(f'상위 {top_n}명 학생의 {title}')
            
            # 값 주석 추가
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                        f'{width:.2f}', va='center')
            
            # 범례 추가 - 원본 이름과 표시 이름을 표시
            if not self.has_korean_font and len(df) > 0:
                legend_text = "학생 이름 참조표:\n"
                for _, row in df.iterrows():
                    orig_name = row['이름']
                    disp_name = row['표시이름']
                    if orig_name != disp_name:
                        legend_text += f"{disp_name} = {orig_name}\n"
                plt.figtext(0.5, 0.01, legend_text, ha="center", fontsize=9, 
                           bbox={"facecolor":"lightgrey", "alpha":0.5, "pad":5})
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            st.error(f"중심성 지표 시각화 중 오류가 발생했습니다: {str(e)}")
            return None
    
    def create_community_table(self):
        """커뮤니티별 학생 목록 생성"""
        try:
            if not self.communities:
                self.analyzer.detect_communities()
            
            # 커뮤니티별 학생 그룹화
            community_groups = {}
            for node, community_id in self.communities.items():
                if community_id not in community_groups:
                    community_groups[community_id] = []
                community_groups[community_id].append(node)
            
            # 한글 폰트 문제 확인 및 대응
            use_romanized = not self.has_korean_font
            
            # 커뮤니티별 데이터 준비
            data = []
            for comm_id, members in community_groups.items():
                # 중심성 지표가 높은 학생 식별
                if self.metrics:
                    # in_degree 기준 중심 학생 식별
                    central_student = max(members, key=lambda x: self.metrics["in_degree"].get(x, 0))
                    central_value = self.metrics["in_degree"].get(central_student, 0)
                else:
                    central_student = ""
                    central_value = 0
                
                # 한글 폰트 문제가 있으면 로마자 변환
                if use_romanized:
                    # 중심 학생 이름 변환
                    central_student_display = self._get_display_label(central_student, use_romanized=True)
                    
                    # 소속 학생 목록 변환
                    members_display = [self._get_display_label(m, use_romanized=True) for m in members]
                    members_str = ", ".join(members_display)
                    
                    # 원본 이름과 로마자 매핑 정보 표시
                    member_mapping = {self._get_display_label(m, use_romanized=True): m for m in members}
                    
                    data.append({
                        "커뮤니티 ID": comm_id,
                        "학생 수": len(members),
                        "소속 학생": members_str,
                        "중심 학생": central_student_display,
                        "중심 학생 연결성": f"{central_value:.3f}",
                        # 원본 이름 정보 저장
                        "학생 매핑": member_mapping
                    })
                else:
                    data.append({
                        "커뮤니티 ID": comm_id,
                        "학생 수": len(members),
                        "소속 학생": ", ".join(members),
                        "중심 학생": central_student,
                        "중심 학생 연결성": f"{central_value:.3f}"
                    })
            
            # 데이터프레임 생성
            df = pd.DataFrame(data)
            
            # 한글 폰트 문제가 있는 경우 매핑 테이블 표시
            if use_romanized:
                st.info("한글 폰트 문제로 인해 학생 이름이 영문으로 표시됩니다.")
                
                # 매핑 정보 표시
                with st.expander("학생 이름 매핑 테이블", expanded=False):
                    all_mappings = {}
                    for row in data:
                        all_mappings.update(row.get("학생 매핑", {}))
                    
                    mapping_df = pd.DataFrame({
                        "영문 표시": list(all_mappings.keys()),
                        "원래 이름": list(all_mappings.values())
                    })
                    st.dataframe(mapping_df)
                
                # 매핑 정보는 테이블에서 제거
                if "학생 매핑" in df.columns:
                    df = df.drop(columns=["학생 매핑"])
            
            return df
            
        except Exception as e:
            logger.error(f"커뮤니티 테이블 생성 실패: {str(e)}")
            st.error(f"커뮤니티 테이블 생성 중 오류가 발생했습니다: {str(e)}")
            return pd.DataFrame(columns=["커뮤니티 ID", "학생 수", "소속 학생", "중심 학생", "중심 학생 연결성"]) 