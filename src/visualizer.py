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
import json

# 모든 matplotlib, plotly 경고 완전히 비활성화
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", "Glyph .* missing from current font")
warnings.filterwarnings("ignore", "findfont: Font family .* not found")
warnings.filterwarnings("ignore", "Substituting symbol .* form .* font")
warnings.filterwarnings("ignore", "No contour levels were found")
warnings.filterwarnings("ignore", "The PostScript backend does not support transparency")

# 로깅 설정 - 경고 레벨을 ERROR로 상향 조정하여 WARNING 메시지 숨김
logging.basicConfig(level=logging.ERROR, filename='network_analysis.log', filemode='w')
logger = logging.getLogger(__name__)
# 스트림 핸들러를 제거하여 콘솔에 출력되지 않도록 설정
logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]

# Streamlit Cloud 환경인지 확인하는 함수
def is_streamlit_cloud():
    """Streamlit Cloud 환경인지 확인"""
    return os.getenv("STREAMLIT_RUNTIME") is not None or os.getenv("STREAMLIT_RUN_ON_SAVE") is not None

# 전역 변수로 한글 폰트 사용 가능 여부 설정 - 기본값은 False로 설정하여 항상 로마자 사용
HAS_KOREAN_FONT = False

# 시스템에 설치된 한글 폰트 목록 확인
def get_korean_fonts():
    """시스템에 설치된 한글 폰트 목록 확인"""
    global HAS_KOREAN_FONT
    
    korean_fonts = []
    try:
        # Linux 환경에서 fc-list 명령어 사용
        if platform.system() == 'Linux':
            try:
                # 한글 폰트 목록 확인
                result = subprocess.run(['fc-list', ':lang=ko'], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    # 폰트 이름 추출
                    font_name = line.split(':')[1].strip().split(',')[0] if ':' in line else ''
                    if font_name and font_name not in korean_fonts:
                        korean_fonts.append(font_name)
            except Exception as e:
                # fc-list 명령 실패 - 명령어가 없거나 실행 권한 없음
                pass
                
        # Windows 환경에서의 한글 폰트 목록 (일반적인 한글 폰트 이름)
        elif platform.system() == 'Windows':
            common_korean_fonts = ['Malgun Gothic', '맑은 고딕', 'Gulim', '굴림', 'Batang', '바탕', 'Dotum', '돋움']
            for font in fm.findSystemFonts():
                try:
                    font_name = fm.FontProperties(fname=font).get_name()
                    if font_name in common_korean_fonts:
                        korean_fonts.append(font_name)
                except:
                    pass
                    
        # macOS 환경에서의 한글 폰트 목록
        elif platform.system() == 'Darwin':
            common_korean_fonts = ['AppleGothic', 'AppleMyungjo', 'NanumGothic', 'NanumMyungjo']
            for font in fm.findSystemFonts():
                try:
                    font_name = fm.FontProperties(fname=font).get_name()
                    if font_name in common_korean_fonts:
                        korean_fonts.append(font_name)
                except:
                    pass
        
        if korean_fonts:
            HAS_KOREAN_FONT = True
        
        return korean_fonts
    
    except Exception as e:
        # 모든 예외 처리
        return []

# 한글 폰트 설치 안내 (Streamlit UI)
def show_korean_font_installation_guide():
    """한글 폰트 설치 방법 안내"""
    with st.sidebar.expander("💡 한글 폰트 설치 안내", expanded=False):
        st.markdown("""
        ### 📋 한글 폰트 설치 방법
        
        **Ubuntu/Debian Linux**:
        ```bash
        sudo apt-get update
        sudo apt-get install fonts-nanum
        fc-cache -fv
        ```
        
        **macOS**:
        - [나눔글꼴 다운로드](https://hangeul.naver.com/font) 후 설치
        
        **Windows**:
        - 이미 기본 한글 폰트가 설치되어 있습니다.
        
        설치 후 앱을 새로고침하세요.
        """)

# 한글 폰트 설정 함수 - 항상 동작하도록 개선
def set_korean_font():
    """시스템에 설치된 한글 폰트 확인 및 설정"""
    global HAS_KOREAN_FONT
    
    # Streamlit Cloud 환경인 경우
    if is_streamlit_cloud():
        # 클라우드 환경에서는 로마자 사용
        HAS_KOREAN_FONT = False
        
        # 조용히 실패하기
        try:
            plt.rcParams['font.family'] = 'DejaVu Sans'
        except:
            pass
            
        return False
        
    # 이미 폰트를 확인한 경우
    if HAS_KOREAN_FONT:
        return True
        
    # 한글 폰트 목록 확인
    korean_fonts = get_korean_fonts()
    
    # 한글 폰트가 있는 경우
    if korean_fonts:
        font_name = korean_fonts[0]
        try:
            plt.rcParams['font.family'] = font_name
            HAS_KOREAN_FONT = True
            return True
        except:
            pass
    
    # 대체 폰트 시도
    for font in ['NanumGothic', 'Malgun Gothic', 'AppleGothic', 'Gulim', 'Arial Unicode MS']:
        try:
            plt.rcParams['font.family'] = font
            HAS_KOREAN_FONT = True
            return True
        except:
            pass
    
    # 시스템 기본 폰트 사용
    try:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass
    
    # 폰트 안내 출력하지 않음 - 사용자 경험 향상을 위해
    HAS_KOREAN_FONT = False
    return False

# PyVis 네트워크에 한글 폰트 적용 (폰트 없이도 작동하도록 개선)
def apply_korean_font_to_pyvis(net):
    """PyVis 네트워크에 한글 폰트 적용"""
    # HTML <style> 요소 대신 직접 CSS를 주입하는 방식으로 변경
    # 이전 코드가 항상 작동하지 않는 경우가 있었음
    custom_css = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic&family=Noto+Sans+KR&display=swap');
      
      .node text {
        font-family: 'Noto Sans KR', 'Nanum Gothic', sans-serif !important;
      }
      
      .tooltip {
        font-family: 'Noto Sans KR', 'Nanum Gothic', sans-serif !important;
      }
    </style>
    """
    
    # 기존 options 딕셔너리에 직접 덮어쓰기
    net.html = net.html.replace("<head>", f"<head>\n{custom_css}")
    
    # 종합적인 수정사항 - 네트워크 자체의 옵션도 조정
    net.options.physics.enabled = True
    net.options.physics.solver = "forceAtlas2Based"
    
    return net

# 한글 로마자 변환 함수 - 성능 개선
SURNAMES = {
    '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung', 
    '강': 'Kang', '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim', 
    '한': 'Han', '오': 'Oh', '서': 'Seo', '신': 'Shin', '권': 'Kwon',
    '황': 'Hwang', '안': 'An', '송': 'Song', '전': 'Jeon', '홍': 'Hong',
    '유': 'Yoo', '고': 'Ko', '문': 'Moon', '양': 'Yang', '손': 'Son',
    '배': 'Bae', '백': 'Baek', '방': 'Bang', '노': 'No', '남': 'Nam',
    '류': 'Ryu', '심': 'Sim', '허': 'Heo', '원': 'Won', '전': 'Jeon',
    '천': 'Chun', '추': 'Chu', '동': 'Dong', '곽': 'Kwak', '금': 'Keum',
    '주': 'Joo', '선': 'Sun', '구': 'Koo', '민': 'Min', '성': 'Sung',
    '탁': 'Tak', '설': 'Seol', '길': 'Gil', '온': 'On', '경': 'Kyung',
    '연': 'Yeon', '울': 'Ul', '제': 'Je', '태': 'Tae', '빈': 'Bin',
    '라': 'Ra', '사': 'Sa', '상': 'Sang', '소': 'So', '채': 'Chae',
    '지': 'Ji', '진': 'Jin', '육': 'Yook', '필': 'Pil', '하': 'Ha',
    '감': 'Kam'
}

def romanize_korean(text):
    """한글 텍스트를 로마자로 변환하는 함수
    
    내부 처리용으로만 사용하고, 표시할 때는 원래 한글을 사용
    """
    if not text or not isinstance(text, str):
        return "Unknown"
        
    # 한글이 아닌 경우 그대로 반환
    if not any(c for c in text if ord('가') <= ord(c) <= ord('힣')):
        return text
        
    # 간단한 로마자 변환 (더 복잡한 규칙이 필요하면 hangul-romanize 등의 라이브러리 사용 권장)
    korean_to_roman = {
        '가': 'ga', '나': 'na', '다': 'da', '라': 'ra', '마': 'ma', '바': 'ba', '사': 'sa', 
        '아': 'a', '자': 'ja', '차': 'cha', '카': 'ka', '타': 'ta', '파': 'pa', '하': 'ha',
        '김': 'Kim', '이': 'Lee', '박': 'Park', '최': 'Choi', '정': 'Jung', '강': 'Kang',
        '조': 'Jo', '윤': 'Yoon', '장': 'Jang', '임': 'Lim', '한': 'Han', '오': 'Oh',
        '서': 'Seo', '신': 'Shin', '권': 'Kwon', '황': 'Hwang', '안': 'Ahn', '송': 'Song',
        '유': 'Yoo', '홍': 'Hong', '전': 'Jeon', '고': 'Go', '문': 'Moon', '양': 'Yang',
        '손': 'Son', '배': 'Bae', '조': 'Cho', '백': 'Baek', '허': 'Heo', '남': 'Nam'
    }
    
    result = ""
    for char in text:
        if '가' <= char <= '힣':
            if char in korean_to_roman:
                result += korean_to_roman[char]
            else:
                # 매핑되지 않은 한글 문자는 'x'로 대체
                result += 'x'
        else:
            result += char
    
    # 로마자 변환 결과 로깅
    logging.debug(f"로마자 변환: {text} -> {result}")
    return result

class NetworkVisualizer:
    """인터랙티브 네트워크 시각화를 담당하는 클래스"""
    
    def __init__(self, analyzer=None, graph=None, metrics=None, has_korean_font=False):
        """NetworkVisualizer 초기화
        
        Args:
            analyzer (NetworkAnalyzer, optional): 네트워크 분석기 객체. Defaults to None.
            graph (nx.DiGraph, optional): 네트워크 그래프. Defaults to None.
            metrics (dict, optional): 중심성 지표 딕셔너리. Defaults to None.
            has_korean_font (bool, optional): 한글 폰트 사용 여부. Defaults to False.
        """
        # 네트워크 분석기 설정
        self.analyzer = analyzer
        
        # 그래프 설정
        if graph is not None:
            self.G = graph
        elif analyzer is not None and hasattr(analyzer, 'graph'):
            self.G = analyzer.graph
        else:
            self.G = nx.DiGraph()
        
        # G_viz 초기화
        self.G_viz = None
        
        # 지표 설정
        if metrics is not None:
            self.metrics = metrics
        elif analyzer is not None and hasattr(analyzer, 'metrics'):
            self.metrics = analyzer.metrics
        else:
            self.metrics = {}
        
        # ID-이름 매핑 저장
        self.id_mapping = {}  # id -> name
        self.name_mapping = {}  # name -> id
        self.original_names = {}  # 로마자 이름 -> 원래 이름
                
        # 글로벌 한글 폰트 설정 확인
        self._check_korean_font()
        
        # 로마자화된 그래프 생성
        if self.G:
            self.G_roman = self._create_romanized_graph(self.G)
            # 원래 이름 그래프 생성 (실제 학생 이름 사용)
            self.G_original = self._create_original_name_graph(self.G)
    
    def _create_original_name_graph(self, G):
        """원래 이름을 사용하는 그래프 생성
        
        Args:
            G: 원본 그래프
            
        Returns:
            nx.DiGraph: 원래 이름을 사용하는 그래프
        """
        try:
            original_G = nx.DiGraph()
            
            # 노드 추가 (원래 이름 사용)
            for node in G.nodes():
                try:
                    # 노드 데이터 복사
                    attrs = G.nodes[node].copy() if G.nodes[node] else {}
                    
                    # 원래 이름 검색 - 다양한 소스에서 시도
                    original_name = str(node)  # 기본값은 노드 ID
                    name_found = False
                    
                    # 방법 1: analyzer의 매핑에서 이름 찾기
                    if hasattr(self.analyzer, 'id_to_name') and self.analyzer.id_to_name and node in self.analyzer.id_to_name:
                        original_name = self.analyzer.id_to_name.get(node, str(node))
                        name_found = True
                    # 방법 2: analyzer의 name_mapping에서 이름 찾기
                    elif hasattr(self.analyzer, 'name_mapping') and self.analyzer.name_mapping and node in self.analyzer.name_mapping:
                        original_name = self.analyzer.name_mapping.get(node, str(node))
                        name_found = True
                    # 방법 3: reverse_romanized에서 이름 찾기
                    elif hasattr(self.analyzer, 'reverse_romanized') and self.analyzer.reverse_romanized and node in self.analyzer.reverse_romanized:
                        original_name = self.analyzer.reverse_romanized.get(node, str(node))
                        name_found = True
                    # 방법 4: 자체 네이밍 매핑에서 찾기
                    elif hasattr(self, 'original_names') and self.original_names and node in self.original_names:
                        original_name = self.original_names.get(node, str(node))
                        name_found = True
                    
                    # 레이블 설정
                    attrs['label'] = original_name
                    
                    # 노드 추가
                    original_G.add_node(node, **attrs)
                    
                except Exception as e:
                    logger.warning(f"노드 {node} 원본 이름 변환 중 오류: {str(e)}")
                    # 오류 발생 시 기본값으로 추가
                    original_G.add_node(node, label=str(node))
            
            # 엣지 추가 (원래 그래프의 모든 엣지 속성 유지)
            for u, v, data in G.edges(data=True):
                try:
                    original_G.add_edge(u, v, **data)
                except Exception as e:
                    logger.warning(f"엣지 {u}-{v} 추가 중 오류: {str(e)}")
                    # 오류 발생 시 기본값으로 추가
                    original_G.add_edge(u, v)
            
            # G_viz에 저장
            self.G_viz = original_G
            
            return original_G
            
        except Exception as e:
            logger.error(f"원본 이름 그래프 생성 중 오류: {str(e)}")
            # 실패 시 원본 그래프 반환
            return G
    
    def _create_romanized_graph(self, G):
        """로마자화된 그래프 생성
        
        Args:
            G: 원본 그래프
            
        Returns:
            nx.DiGraph: 로마자화된 그래프
        """
        try:
            roman_G = nx.DiGraph()
            
            # 노드 추가 (로마자화)
            for node in G.nodes():
                try:
                    # 노드 데이터 복사
                    attrs = G.nodes[node].copy() if G.nodes[node] else {}
                    
                    # 이름 로마자화
                    roman_name = self._romanize_name(str(node))
                    
                    # 원래 이름 저장
                    self.original_names[roman_name] = str(node)
                    
                    # 로마자화된 이름으로 노드 추가
                    roman_G.add_node(roman_name, **attrs)
                    
                except Exception as e:
                    logger.warning(f"노드 {node} 로마자화 중 오류: {str(e)}")
                    # 오류 시 원본 노드명 그대로 사용
                    roman_G.add_node(str(node))
            
            # 엣지 추가
            for u, v, data in G.edges(data=True):
                try:
                    # 노드 이름 로마자화
                    roman_u = self._romanize_name(str(u))
                    roman_v = self._romanize_name(str(v))
                    
                    # 엣지 추가
                    roman_G.add_edge(roman_u, roman_v, **data)
                except Exception as e:
                    logger.warning(f"엣지 {u}-{v} 로마자화 중 오류: {str(e)}")
                    # 오류 시 원본 노드명 그대로 사용
                    roman_G.add_edge(str(u), str(v))
            
            return roman_G
        except Exception as e:
            logger.error(f"로마자화 그래프 생성 중 오류: {str(e)}")
            # 오류 시 빈 그래프 반환
            return nx.DiGraph()
            
    def _get_original_name(self, roman_name):
        """로마자화된 이름에서 원래 이름 가져오기
        
        Args:
            roman_name: 로마자화된 이름
            
        Returns:
            str: 원래 이름
        """
        return self.original_names.get(roman_name, str(roman_name))
    
    def _check_korean_font(self):
        """한글 폰트 사용 가능 여부 확인"""
        # 글로벌 변수 사용
        global HAS_KOREAN_FONT
        
        # 항상 False로 설정 (로마자 사용)
        self.has_korean_font = False
        
    def _romanize_name(self, name):
        """한글 이름을 로마자화된 이름으로 변환"""
        return romanize_korean(name)

    def create_plotly_network(self, layout="fruchterman", width=900, height=700, focus_node=None, neighbor_depth=1):
        """Plotly를 사용해 인터랙티브 네트워크 그래프 생성
        
        Args:
            layout (str): 그래프 레이아웃 알고리즘 ('fruchterman', 'spring', 'circular', 'kamada', 'spectral')
            width (int): 그래프 너비
            height (int): 그래프 높이
            focus_node (str, optional): 중심으로 볼 노드 이름 (None이면 전체 그래프)
            neighbor_depth (int, optional): 중심 노드로부터 포함할 이웃 깊이 (기본값: 1)
            
        Returns:
            go.Figure: Plotly 그래프 객체
        """
        try:
            # 원래 이름 그래프 사용 (실제 학생 이름)
            G = None
            if hasattr(self, 'G_original') and self.G_original is not None:
                G = self.G_original.copy()
            elif hasattr(self, 'G') and self.G is not None:
                G = self.G.copy()
            elif hasattr(self, 'analyzer') and hasattr(self.analyzer, 'graph'):
                G = self.analyzer.graph.copy()
            elif hasattr(self, 'analyzer') and hasattr(self.analyzer, 'G'):
                G = self.analyzer.G.copy()
            
            # 그래프가 없는 경우
            if G is None or G.number_of_nodes() == 0:
                fig = go.Figure()
                fig.add_annotation(text="네트워크 데이터가 없습니다", showarrow=False, font=dict(size=20))
                fig.update_layout(width=width, height=height)
                return fig
                
            # 특정 노드 중심 서브그래프 생성 (focus_node가 지정된 경우)
            original_G = G.copy()  # 원본 그래프 저장
            if focus_node is not None and focus_node in G.nodes():
                # 중심 노드 포함 서브그래프 생성
                nodes_to_keep = {focus_node}
                
                # neighbor_depth까지의 이웃 노드 추가
                current_neighbors = {focus_node}
                for i in range(neighbor_depth):
                    new_neighbors = set()
                    for node in current_neighbors:
                        # 진입 이웃 (들어오는 엣지)
                        new_neighbors.update(G.predecessors(node))
                        # 진출 이웃 (나가는 엣지)
                        new_neighbors.update(G.successors(node))
                    
                    # 새 이웃 추가
                    nodes_to_keep.update(new_neighbors)
                    current_neighbors = new_neighbors
                
                # 서브그래프 생성
                G = G.subgraph(nodes_to_keep).copy()
                
                # 서브그래프가 비어있으면 원본 사용
                if G.number_of_nodes() == 0:
                    G = original_G.copy()
                    focus_node = None  # 포커스 노드 초기화
            
            # 레이아웃 알고리즘 적용
            pos = None
            try:
                if layout == "circular":
                    pos = nx.circular_layout(G)
                elif layout == "spring":
                    pos = nx.spring_layout(G, seed=42, k=0.3, iterations=50)
                elif layout == "kamada":
                    pos = nx.kamada_kawai_layout(G)
                elif layout == "spectral":
                    pos = nx.spectral_layout(G)
                else:
                    # 기본값: fruchterman_reingold
                    pos = nx.fruchterman_reingold_layout(G, seed=42, k=0.3, iterations=100)
            except Exception as e:
                logger.warning(f"레이아웃 알고리즘 적용 오류: {str(e)}, 대체 레이아웃 사용")
                # 오류 시 안전한 레이아웃 사용
                pos = nx.spring_layout(G, seed=42)
            
            # 중심성 데이터 확인
            centrality_metrics = {}
            if hasattr(self, 'analyzer') and hasattr(self.analyzer, 'metrics'):
                centrality_metrics = self.analyzer.metrics
            elif hasattr(self, 'metrics'):
                centrality_metrics = self.metrics
            
            # 노드 크기 설정 (중심성 기반)
            node_size = []
            for node in G.nodes():
                try:
                    # 인기도(in-degree) 기반 크기 설정
                    if 'in_degree' in centrality_metrics and node in centrality_metrics['in_degree']:
                        # 중심성 값 가져오기
                        centrality = centrality_metrics['in_degree'][node]
                        # 값 유효성 검증
                        if isinstance(centrality, (int, float)):
                            size = 15 + centrality * 50
                        elif isinstance(centrality, list) and centrality:
                            size = 15 + float(centrality[0]) * 50
                        else:
                            size = 15
                    else:
                        # 인기도 정보가 없으면 연결 수 기반
                        size = 15 + G.in_degree(node) * 2
                    
                    # 크기 범위 제한
                    size = max(10, min(size, 50))
                    
                    # 포커스 노드이면 크기 키우기
                    if focus_node is not None and node == focus_node:
                        size = 70  # 중심 노드 강조
                        
                    node_size.append(size)
                except Exception as e:
                    logger.warning(f"노드 {node} 크기 계산 중 오류: {str(e)}")
                    node_size.append(15)  # 기본 크기
            
            # 커뮤니티 정보 가져오기
            communities = None
            if hasattr(self, 'communities') and self.communities:
                communities = self.communities
            elif hasattr(self.analyzer, 'communities'):
                communities = self.analyzer.communities
            
            # 노드 색상 설정 (커뮤니티 기반)
            node_color = []
            
            # 색상 팔레트
            color_palette = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
                '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
            ]
            
            # 커뮤니티별 색상 할당
            comm_color_map = {}
            
            for node in G.nodes():
                try:
                    if communities and node in communities:
                        comm_id = communities[node]
                        
                        # 다양한 타입 처리
                        if isinstance(comm_id, list):
                            comm_id = comm_id[0] if comm_id else 0
                            
                        # 문자열 타입 처리
                        if not isinstance(comm_id, (int, float)):
                            try:
                                comm_id = int(comm_id)
                            except (ValueError, TypeError):
                                # 해시 값으로 처리
                                comm_id = hash(str(comm_id)) % 10000
                        
                        # 색상 매핑에 없으면 새로 할당
                        if comm_id not in comm_color_map:
                            color_idx = len(comm_color_map) % len(color_palette)
                            comm_color_map[comm_id] = color_palette[color_idx]
                            
                        # 기본 색상
                        color = comm_color_map[comm_id]
                        
                        # 포커스 노드이면 다른 색상 사용
                        if focus_node is not None and node == focus_node:
                            color = 'red'  # 중심 노드 강조
                            
                        node_color.append(color)
                    else:
                        # 커뮤니티 정보가 없으면 기본 색상 사용
                        if focus_node is not None and node == focus_node:
                            node_color.append('red')  # 중심 노드 강조
                        else:
                            node_color.append('#1f77b4')
                except Exception as e:
                    logger.warning(f"노드 {node} 색상 설정 중 오류: {str(e)}")
                    node_color.append('#cccccc')
            
            # 가중치별 엣지 그룹화 (각 가중치별로 별도의 Scatter를 만들기 위함)
            edge_groups = {}  # 가중치별 엣지 정보 저장 (weight -> [x, y, info])
            
            # 엣지 그리기
            for u, v, data in G.edges(data=True):
                try:
                    x0, y0 = pos[u]
                    x1, y1 = pos[v]
                    
                    # 엣지 두께 (가중치 기반)
                    weight = 1
                    if 'weight' in data:
                        weight = data['weight']
                    
                    # 가중치가 숫자가 아니면 기본값 사용
                    try:
                        weight = float(weight)
                    except (ValueError, TypeError):
                        weight = 1
                        
                    # 두께 설정 (최소 1, 최대 5)
                    thickness = max(1, min(1 + weight * 0.5, 5))
                    thickness_rounded = round(thickness * 2) / 2  # 0.5 단위로 반올림
                    
                    # 포커스 노드와 연결된 엣지는 두껍게
                    if focus_node is not None and (u == focus_node or v == focus_node):
                        thickness_rounded = 3.0  # 중심 노드의 엣지 강조
                    
                    # 정보 텍스트
                    info = f"{u} → {v}"
                    if weight > 1:
                        info += f"<br>가중치: {weight}"
                    
                    # 가중치 그룹에 추가
                    if thickness_rounded not in edge_groups:
                        edge_groups[thickness_rounded] = {
                            'x': [],
                            'y': [],
                            'info': [],
                            'focus': []  # 중심 노드 연결 여부
                        }
                    
                    # 중심 노드 연결 여부
                    is_focus = focus_node is not None and (u == focus_node or v == focus_node)
                    
                    # 해당 가중치 그룹에 좌표와 정보 추가
                    edge_groups[thickness_rounded]['x'].extend([x0, x1, None])
                    edge_groups[thickness_rounded]['y'].extend([y0, y1, None])
                    edge_groups[thickness_rounded]['info'].extend([info, info, None])
                    edge_groups[thickness_rounded]['focus'].extend([is_focus, is_focus, False])
                    
                except Exception as e:
                    # 엣지 그리기 오류 무시
                    logger.warning(f"엣지 {u}-{v} 처리 중 오류: {str(e)}")
                    continue
            
            # 엣지 트레이스 (가중치별로 별도 생성)
            edge_traces = []
            for thickness, group in edge_groups.items():
                # 중심 노드 연결 엣지는 다른 색상 사용
                edge_color = 'rgba(150, 150, 150, 0.6)'
                if focus_node is not None and any(group['focus']):
                    edge_color = 'rgba(255, 0, 0, 0.6)'  # 중심 노드 연결 엣지는 빨간색
                
                # 해당 두께의 엣지 Scatter 생성
                edge_trace = go.Scatter(
                    x=group['x'], 
                    y=group['y'],
                    line=dict(width=thickness, color=edge_color),
                    hoverinfo='text',
                    text=group['info'],
                    mode='lines',
                    name=f'연결 (두께: {thickness})'
                )
                edge_traces.append(edge_trace)
            
            # 엣지가 없는 경우 빈 트레이스 추가
            if not edge_traces:
                edge_traces = [go.Scatter(
                    x=[], y=[],
                    line=dict(width=1, color='rgba(150, 150, 150, 0.6)'),
                    mode='lines'
                )]
                
            # 노드 데이터 준비
            node_x = []
            node_y = []
            node_text = []
            node_hover = []
            node_ids = []  # node_ids 변수 초기화 추가
            node_labels = {}
            for node in G.nodes():
                # 노드 ID가 이미 실제 이름인 경우 (G_original 사용 시)
                node_labels[node] = str(node)
                
                # 추가적인 레이블 검색 (노드 속성 사용)
                if 'label' in G.nodes[node] and G.nodes[node]['label']:
                    node_labels[node] = G.nodes[node]['label']
                elif 'name' in G.nodes[node] and G.nodes[node]['name']:
                    node_labels[node] = G.nodes[node]['name']
            
            # 노드 데이터 설정
            for node in G.nodes():
                try:
                    # 노드 위치
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    
                    # 노드 ID 저장 (클릭 이벤트용)
                    node_ids.append(node)
                    
                    # 노드 이름 설정 (실제 학생 이름 사용)
                    node_label = node_labels.get(node, str(node))
                    node_text.append(node_label)
                    
                    # 중심성 정보 가져오기
                    in_degree_val = 0
                    out_degree_val = 0
                    betweenness_val = 0
                    
                    if 'in_degree' in centrality_metrics and node in centrality_metrics['in_degree']:
                        try:
                            in_degree_val = float(centrality_metrics['in_degree'][node])
                        except (ValueError, TypeError):
                            in_degree_val = 0
                    
                    if 'out_degree' in centrality_metrics and node in centrality_metrics['out_degree']:
                        try:
                            out_degree_val = float(centrality_metrics['out_degree'][node])
                        except (ValueError, TypeError):
                            out_degree_val = 0
                    
                    if 'betweenness' in centrality_metrics and node in centrality_metrics['betweenness']:
                        try:
                            betweenness_val = float(centrality_metrics['betweenness'][node])
                        except (ValueError, TypeError):
                            betweenness_val = 0
                    
                    # 호버 텍스트 생성
                    hover_text = f"{node_label}\n"
                    hover_text += f"인기도: {in_degree_val:.3f}\n"
                    hover_text += f"활동성: {out_degree_val:.3f}\n"
                    hover_text += f"매개성: {betweenness_val:.3f}\n"
                    
                    # 연결 수 정보
                    in_edges = G.in_degree(node)
                    out_edges = G.out_degree(node)
                    hover_text += f"받은 선택: {in_edges}명\n"
                    hover_text += f"한 선택: {out_edges}명"
                    
                    # 커뮤니티 정보 추가
                    if communities and node in communities:
                        try:
                            comm = communities[node]
                            hover_text += f"\n그룹: {comm}"
                        except Exception as e:
                            logger.warning(f"노드 {node} 정보 설정 중 오류: {str(e)}")
                    
                    # 중심 노드 표시
                    if focus_node is not None and node == focus_node:
                        hover_text += "\n중심 노드"
                        # 원래 이름 추가 (이미 원본 이름 사용 중이므로 필요 없음)
                    elif focus_node is not None:
                        hover_text += "\n클릭: 이 학생 중심 보기"
                    else:
                        hover_text += "\n클릭: 이 학생 중심 보기"
                    
                    node_hover.append(hover_text)
                except Exception as e:
                    logger.warning(f"노드 {node} 정보 설정 중 오류: {str(e)}")
                    node_x.append(0)
                    node_y.append(0)
                    node_text.append(str(node))
                    node_hover.append(f"오류: {str(e)}")
                    # 딕셔너리에 추가하도록 수정
                    node_labels[node] = str(node)
                    node_ids.append(str(node))
            
            # 노드 트레이스
            node_trace = go.Scatter(
                x=node_x, 
                y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=node_text,
                hovertext=node_hover,
                textposition="top center",
                textfont=dict(
                    family="'Noto Sans KR', 'Malgun Gothic', sans-serif",
                    size=10,
                    color="black"
                ),
                marker=dict(
                    showscale=False,
                    color=node_color,
                    size=node_size,
                    line=dict(color='black', width=1),
                    opacity=0.9
                ),
                ids=node_ids,  # 클릭 이벤트용 ID
                customdata=node_ids  # 클릭 이벤트에서 접근할 데이터
            )
            
            # 그래프 제목 설정
            title = '<b>학급 관계 네트워크</b>'
            if focus_node is not None:
                title = f'<b>{focus_node} 중심 관계 네트워크</b>'
            
            # 그래프 레이아웃 설정
            fig = go.Figure(
                data=[*edge_traces, node_trace],
                layout=go.Layout(
                    title=title,
                    titlefont=dict(size=18, family="'Noto Sans KR', sans-serif"),
                    showlegend=False,  # 범례 숨김
                    hovermode='closest',
                    margin=dict(b=20, l=20, r=20, t=40),
                    annotations=[],
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    width=width,
                    height=height,
                    plot_bgcolor='rgba(248,249,250,1)',  # 배경색
                    paper_bgcolor='rgba(248,249,250,1)',  # 주변 배경색
                    clickmode='event+select'  # 클릭 이벤트 활성화
                )
            )
            
            # 다크 모드 지원
            fig.update_layout(
                template="plotly",
                margin=dict(l=10, r=10, t=50, b=10)
            )
            
            # 포커스 노드 있는 경우 주석 추가
            if focus_node is not None:
                fig.add_annotation(
                    text=f"중심 학생: {focus_node}",
                    xref="paper", yref="paper",
                    x=0.5, y=1.05,
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
                
                # 전체 보기 버튼 추가
                fig.add_annotation(
                    text="<a href='javascript:void(0);' onclick='resetFocus()'>전체 네트워크 보기</a>",
                    xref="paper", yref="paper",
                    x=0.95, y=1.05,
                    showarrow=False,
                    font=dict(size=12, color="blue")
                )
            
            # 인터랙티브 기능 추가
            fig.update_layout(
                dragmode='pan',  # 드래그 모드 설정
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="'Noto Sans KR', sans-serif"
                ),
                # 커스텀 버튼들 추가
                updatemenus=[
                    dict(
                        type="buttons",
                        direction="right",
                        x=0.1,
                        y=1.1,
                        showactive=True,
                        buttons=[
                            dict(
                                label="확대",
                                method="relayout",
                                args=["dragmode", "zoom"]
                            ),
                            dict(
                                label="이동",
                                method="relayout",
                                args=["dragmode", "pan"]
                            ),
                            dict(
                                label="초기화",
                                method="update",
                                args=[
                                    {"visible": [True, True]},
                                    {"dragmode": "pan"}
                                ]
                            )
                        ]
                    )
                ]
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Plotly 네트워크 시각화 생성 중 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 오류 발생 시 빈 그래프 반환
            fig = go.Figure()
            fig.add_annotation(
                text=f"네트워크 시각화 생성 중 오류가 발생했습니다:<br>{str(e)}",
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(width=width, height=height)
            return fig
    
    def create_pyvis_network(self, height="600px", width="100%", layout="kamada_kawai"):
        """PyVis 기반 대화형 네트워크 그래프 생성
        
        Args:
            height (str): 그래프 높이
            width (str): 그래프 너비
            layout (str): 레이아웃 알고리즘 (kamada_kawai가 학급 관계 시각화에 최적합)
        
        Returns:
            PyVis Network: 대화형 네트워크 객체
        """
        try:
            # 네트워크 객체 생성
            net = Network(height=height, width=width, directed=True, notebook=False)
            
            # 레이아웃 기반 물리 엔진 설정
            physics_options = {}
            
            if layout == "kamada_kawai":
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
            elif layout == "fruchterman":
                physics_options = {
                    "repulsion": {
                        "nodeDistance": 220,
                        "centralGravity": 0.15,
                        "springLength": 220,
                        "springConstant": 0.06,
                        "damping": 0.09
                    }
                }
            elif layout == "force":
                physics_options = {
                    "forceAtlas2Based": {
                        "gravitationalConstant": -60,
                        "centralGravity": 0.015,
                        "springLength": 120,
                        "springConstant": 0.1,
                        "damping": 0.4,
                        "avoidOverlap": 0.8
                    }
                }
            else:
                # 기본 물리 엔진 설정
                physics_options = {
                    "barnesHut": {
                        "gravitationalConstant": -4000,
                        "centralGravity": 0.2,
                        "springLength": 140,
                        "springConstant": 0.05,
                        "damping": 0.09,
                        "avoidOverlap": 0.8
                    }
                }
            
            # 사용자 정의 옵션 설정 - 최적화된 설정으로 교체
            options = {
                "nodes": {
                    "font": {
                        "size": 16,
                        "face": "Noto Sans KR, Malgun Gothic, sans-serif",
                        "color": "#000000",  # 더 어두운 글자색으로 가독성 향상
                        "strokeWidth": 3,  # 테두리 두께 증가
                        "strokeColor": "#ffffff"  # 흰색 테두리로 대비 강화
                    },
                    "borderWidth": 3,  # 테두리 두께 증가
                    "borderWidthSelected": 5,  # 선택 시 테두리 두께 증가
                    "shadow": True,
                    "shape": "dot",
                    "scaling": {
                        "min": 15,  # 최소 크기 증가
                        "max": 40,  # 최대 크기 증가
                        "label": {
                            "enabled": True,
                            "min": 14,  # 최소 라벨 크기 증가
                            "max": 20   # 최대 라벨 크기 증가
                        }
                    },
                    "color": {
                        "highlight": "#FF5722",  # 강조색 변경 (선명한 주황색)
                        "hover": "#4CAF50"       # 호버색 변경 (선명한 녹색)
                    }
                },
                "edges": {
                    "color": {
                        "color": "#444444",  # 기본 엣지 색상 어둡게 변경
                        "highlight": "#FF5722",  # 강조색 변경 (선명한 주황색)
                        "hover": "#4CAF50",      # 호버색 변경 (선명한 녹색)
                        "inherit": False
                    },
                    "smooth": {
                        "enabled": True,
                        "type": "dynamic",
                        "roundness": 0.5
                    },
                    "font": {
                        "face": "Noto Sans KR, Malgun Gothic, sans-serif",
                        "size": 13,  # 폰트 크기 증가
                        "color": "#000000",  # 더 어두운 글자색
                        "strokeWidth": 3,  # 테두리 두께 증가
                        "strokeColor": "#ffffff",  # 흰색 테두리
                        "align": "horizontal"
                    },
                    "width": 2.5,  # 기본 너비 증가
                    "selectionWidth": 4,  # 선택 시 너비 증가
                    "hoverWidth": 3.5,  # 호버 시 너비 증가
                    "arrows": {
                        "to": {
                            "enabled": True,
                            "scaleFactor": 0.6,
                            "type": "arrow"
                        }
                    }
                },
                "interaction": {
                    "dragNodes": True,
                    "dragView": True,
                    "hideEdgesOnDrag": False,
                    "hideNodesOnDrag": False,
                    "hover": True,
                    "navigationButtons": True,
                    "multiselect": True,
                    "selectable": True,
                    "selectConnectedEdges": True,
                    "hoverConnectedEdges": True,
                    "zoomView": True,
                    "keyboard": {
                        "enabled": True,
                        "bindToWindow": False
                    },
                    "tooltipDelay": 100  # 툴팁 표시 지연 시간 단축
                },
                "physics": {
                    "enabled": True,
                    "stabilization": {
                        "enabled": True,
                        "iterations": 1500,  # 안정화 반복 횟수 증가
                        "updateInterval": 25,  # 업데이트 간격 감소
                        "fit": True,
                        "onlyDynamicEdges": False,
                        "animationEnabled": True  # 안정화 애니메이션 활성화
                    },
                    **physics_options  # 레이아웃별 물리 설정 추가
                },
                "layout": {
                    "improvedLayout": True,
                    "hierarchical": {
                        "enabled": False
                    }
                }
            }
            
            # 네트워크 옵션 설정
            net.options = options
            
            # 커뮤니티 정보 가져오기
            communities = None
            if hasattr(self, 'communities') and self.communities:
                communities = self.communities
            elif hasattr(self.analyzer, 'communities'):
                communities = self.analyzer.communities
            
            # 그래프 데이터 가져오기
            G = self.G
            
            # 노드 중심성 지표 가져오기
            node_colors = {}
            node_sizes = {}
            
            if hasattr(self, 'metrics'):
                metrics = self.metrics
                
                # 크기 결정: 인기도(in_degree)
                if 'in_degree' in metrics:
                    node_sizes = metrics['in_degree']
                
                # 색상 결정: 매개 중심성(betweenness)
                if 'betweenness' in metrics:
                    node_colors = metrics['betweenness']
            
            # 커뮤니티 색상 맵 - 더 선명하고 대비가 높은 색상으로 변경
            color_map = ["#3F51B5", "#E91E63", "#FFC107", "#009688", "#9C27B0", "#03A9F4", "#F44336", "#4CAF50", "#673AB7", "#FF5722"]
            
            # 노드 추가
            for node in G.nodes():
                # 노드 속성 가져오기
                node_attr = G.nodes[node]
                
                # 기본 크기 및 색상 설정
                size = 20
                color = "#97C2FC"
                
                # 노드 크기 계산 (인기도 기반)
                if node in node_sizes:
                    # 노드 크기 정규화 (25-45)
                    size = node_sizes.get(node, 0.5)
                    size = 25 + min(20, size * 35)
                
                # 노드 색상 계산
                if communities and node in communities:
                    try:
                        comm = communities[node]
                        if isinstance(comm, (int, float)) and 0 <= comm < len(color_map):
                            color = color_map[int(comm)]
                        else:
                            # 기본값으로 매개 중심성 기반 색상 사용
                            intensity = node_colors.get(node, 0.5)
                            color = f"rgba(25, 118, 210, {min(0.9, max(0.3, intensity))})"
                    except Exception as e:
                        logger.warning(f"노드 {node} 색상 설정 중 오류: {str(e)}")
                        # 기본 색상 사용
                        color = "#97C2FC"
                else:
                    # 매개 중심성 기반 색상 설정
                    intensity = node_colors.get(node, 0.5)
                    color = f"rgba(25, 118, 210, {min(0.9, max(0.3, intensity))})"
                
                # 툴팁 정보 설정 (호버 시 표시)
                try:
                    # 노드 기본 정보
                    title = f"{node_attr.get('label', node)}\n"
                    
                    # 중심성 지표 추가
                    in_deg = 0
                    out_deg = 0
                    bet = 0
                    
                    if hasattr(self, 'metrics'):
                        if 'in_degree' in self.metrics and node in self.metrics['in_degree']:
                            in_deg = self.metrics['in_degree'][node]
                        if 'out_degree' in self.metrics and node in self.metrics['out_degree']:
                            out_deg = self.metrics['out_degree'][node]
                        if 'betweenness' in self.metrics and node in self.metrics['betweenness']:
                            bet = self.metrics['betweenness'][node]
                    
                    # 커뮤니티 정보 추가
                    if communities and node in communities:
                        try:
                            comm = communities[node]
                            title += f"소속 그룹: {comm}\n"
                        except Exception as e:
                            logger.warning(f"노드 {node} 정보 설정 중 오류: {str(e)}")
                    
                    # 중심성 지표 표시
                    title += f"인기도: {in_deg:.3f}\n"
                    title += f"활동성: {out_deg:.3f}\n"
                    title += f"매개성: {bet:.3f}\n"
                    
                    # 연결 정보
                    in_edges = G.in_degree(node)
                    out_edges = G.out_degree(node)
                    title += f"받은 선택: {in_edges}명\n"
                    title += f"한 선택: {out_edges}명"
                    
                    # 노드 추가 - 향상된 속성 설정
                    net.add_node(
                        node, 
                        label=node_attr.get('label', node), 
                        title=title,
                        color=color, 
                        size=size,
                        borderWidth=3,
                        borderWidthSelected=5,
                        shadow=True,
                        font={'size': 16, 'color': '#000000', 'strokeWidth': 3, 'strokeColor': '#ffffff'}
                    )
                except Exception as e:
                    logger.warning(f"노드 {node} 추가 중 오류: {str(e)}")
                    # 기본 설정으로 노드 추가
                    net.add_node(node, label=str(node))
            
            # 엣지 추가 - 관계 표현 강화
            for u, v, data in G.edges(data=True):
                try:
                    # 엣지 속성 설정
                    width = 2  # 기본 너비
                    title = f"{u}에서 {v}로 연결"
                    
                    # 가중치가 있는 경우 반영
                    if 'weight' in data:
                        width = data['weight'] * 2
                        title += f"\n가중치: {data['weight']}"
                    
                    # 관계 유형이 있는 경우 반영
                    if 'type' in data:
                        title += f"\n관계: {data['type']}"
                    elif 'relationship' in data:
                        title += f"\n관계: {data['relationship']}"
                    
                    # 엣지 색상 설정 - 두 노드의 커뮤니티에 따라 색상 설정
                    edge_color = "#606060"  # 기본 색상
                    
                    if communities and u in communities and v in communities:
                        comm_u = communities[u]
                        comm_v = communities[v]
                        
                        # 같은 커뮤니티면 해당 커뮤니티 색상 사용
                        if comm_u == comm_v and isinstance(comm_u, (int, float)) and 0 <= comm_u < len(color_map):
                            edge_color = color_map[int(comm_u)]
                            # 투명도 적용 (엣지는 노드보다 약간 투명하게)
                            if edge_color.startswith('#'):
                                edge_color = edge_color + '99'  # 16진수 색상에 투명도 추가
                    
                    # 엣지 추가
                    net.add_edge(
                        u, v, 
                        title=title, 
                        width=width, 
                        color=edge_color,
                        smooth={'enabled': True, 'type': 'dynamic'},
                        selectionWidth=4,  # 선택 시 너비 증가
                        hoverWidth=3       # 호버 시 너비 증가
                    )
                    
                except Exception as e:
                    logger.warning(f"엣지 {u}-{v} 추가 중 오류: {str(e)}")
                    # 기본 설정으로 엣지 추가
                    net.add_edge(u, v)
            
            # 향상된 네트워크 시각화 설정 적용
            temp_path = "temp_network.html"
            self.save_and_show_pyvis_network(net, filename=temp_path, height=height)
            
            return net
        
        except Exception as e:
            logger.error(f"PyVis 네트워크 생성 중 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def save_and_show_pyvis_network(self, net, filename="network.html", height="600px", add_custom_js=True):
        """PyVis 네트워크를 저장하고 추가 사용자 정의 스크립트 적용
        
        Args:
            net (PyVis Network): 네트워크 객체
            filename (str): 저장할 HTML 파일명
            height (str): 그래프 높이
            add_custom_js (bool): 사용자 정의 JS 추가 여부
        
        Returns:
            str: HTML 문자열
        """
        try:
            # 임시 파일로 저장
            net.save_graph(filename)
            
            # HTML 읽기
            with open(filename, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # 기본 스타일 업데이트
            updated_style = """
            <style>
                #mynetwork {
                    width: 100%;
                    height: """+height+""";
                    border: 1px solid #ddd;
                    background-color: #f9f9f9;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    border-radius: 8px;
                    margin: auto;
                }
                .vis-network:focus {
                    outline: none;
                }
                .vis-manipulation {
                    background-color: #f9f9f9 !important;
                    border-radius: 6px !important;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
                }
                .vis-button {
                    background-color: #ffffff !important;
                    border-radius: 50% !important;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
                    transition: all 0.3s ease !important;
                }
                .vis-button:hover {
                    background-color: #f5f5f5 !important;
                    transform: scale(1.05) !important;
                }
                .vis-tooltip {
                    position: absolute;
                    visibility: hidden;
                    padding: 8px;
                    white-space: pre-line;
                    font-family: 'Noto Sans KR', sans-serif;
                    font-size: 14px;
                    color: #000;
                    background-color: #fff;
                    border-radius: 6px;
                    border: 1px solid #ddd;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.15);
                    max-width: 250px;
                    line-height: 1.5;
                    z-index: 9999;
                }
            </style>
            """
            
            # 사용자 정의 스크립트 (클릭 효과 강화)
            if add_custom_js:
                custom_js = """
                <script type="text/javascript">
                    // 네트워크가 완전히 로드된 후 실행
                    network.once("stabilizationIterationsDone", function() {
                        // 안정화 완료 후 물리 엔진 비활성화 (더 부드러운 탐색을 위해)
                        // network.setOptions({physics: false});
                        console.log("네트워크 안정화 완료");
                        
                        // 기존 노드/엣지 스타일 저장
                        let originalNodeStyles = {};
                        let originalEdgeStyles = {};
                        let highlightedNodes = new Set();
                        let highlightedEdges = new Set();
                        
                        // 노드 클릭 이벤트 - 강화된 하이라이팅
                        network.on("click", function(params) {
                            // 클릭된 노드가 있는 경우
                            if (params.nodes.length > 0) {
                                // 이전 하이라이트 초기화
                                resetHighlights();
                                
                                const selectedNode = params.nodes[0];
                                // 연결된 노드 찾기
                                const connectedNodes = network.getConnectedNodes(selectedNode);
                                // 연결된 엣지 찾기
                                const connectedEdges = network.getConnectedEdges(selectedNode);
                                
                                // 클릭된 노드 하이라이트
                                highlightNode(selectedNode, "#FF5722", 6, 1.2);
                                
                                // 연결된 노드 하이라이트
                                connectedNodes.forEach(node => {
                                    highlightNode(node, "#4CAF50", 4, 1.1);
                                });
                                
                                // 연결된 엣지 하이라이트
                                connectedEdges.forEach(edge => {
                                    highlightEdge(edge, "#FF5722", 3);
                                });
                                
                                // 하이라이트 목록에 추가
                                highlightedNodes.add(selectedNode);
                                connectedNodes.forEach(node => highlightedNodes.add(node));
                                connectedEdges.forEach(edge => highlightedEdges.add(edge));
                                
                                // 선택되지 않은 노드는 흐리게 표시
                                fadeOtherNodes(highlightedNodes);
                                fadeOtherEdges(highlightedEdges);
                            } 
                            // 배경 클릭 시 리셋
                            else if (params.nodes.length === 0 && params.edges.length === 0) {
                                resetAll();
                            }
                        });
                        
                        // 노드 하이라이트 함수
                        function highlightNode(nodeId, color, borderWidth, scale) {
                            // 원본 스타일 저장
                            if (!originalNodeStyles[nodeId]) {
                                const node = network.body.nodes[nodeId];
                                if (node) {
                                    originalNodeStyles[nodeId] = {
                                        color: node.options.color,
                                        borderWidth: node.options.borderWidth,
                                        size: node.options.size
                                    };
                                }
                            }
                            
                            // 하이라이트 적용
                            network.body.nodes[nodeId].options.borderWidth = borderWidth;
                            network.body.nodes[nodeId].options.borderWidthSelected = borderWidth + 2;
                            network.body.nodes[nodeId].options.color = {
                                background: network.body.nodes[nodeId].options.color.background,
                                border: color,
                                highlight: {
                                    background: network.body.nodes[nodeId].options.color.background,
                                    border: color
                                }
                            };
                            // 크기 스케일 적용
                            network.body.nodes[nodeId].options.size *= scale;
                        }
                        
                        // 엣지 하이라이트 함수
                        function highlightEdge(edgeId, color, width) {
                            // 원본 스타일 저장
                            if (!originalEdgeStyles[edgeId]) {
                                const edge = network.body.edges[edgeId];
                                if (edge) {
                                    originalEdgeStyles[edgeId] = {
                                        color: edge.options.color,
                                        width: edge.options.width
                                    };
                                }
                            }
                            
                            // 하이라이트 적용
                            network.body.edges[edgeId].options.color = color;
                            network.body.edges[edgeId].options.width = width;
                        }
                        
                        // 다른 노드 페이드 아웃
                        function fadeOtherNodes(highlightedNodes) {
                            Object.keys(network.body.nodes).forEach(nodeId => {
                                if (!highlightedNodes.has(nodeId)) {
                                    // 원본 스타일 저장
                                    if (!originalNodeStyles[nodeId]) {
                                        const node = network.body.nodes[nodeId];
                                        originalNodeStyles[nodeId] = {
                                            color: node.options.color,
                                            borderWidth: node.options.borderWidth,
                                            size: node.options.size
                                        };
                                    }
                                    
                                    // 페이드 아웃 적용
                                    const nodeObj = network.body.nodes[nodeId];
                                    const bgColor = nodeObj.options.color.background;
                                    
                                    // 배경색에 투명도 적용
                                    let bgRgba;
                                    if (typeof bgColor === 'string' && bgColor.startsWith('rgba')) {
                                        // 이미 rgba 형식이면 투명도만 변경
                                        bgRgba = bgColor.replace(/rgba\((.*?),(.*?),(.*?),.*?\)/, 'rgba($1,$2,$3,0.3)');
                                    } else if (typeof bgColor === 'string' && bgColor.startsWith('rgb')) {
                                        // rgb 형식이면 rgba로 변환
                                        bgRgba = bgColor.replace(/rgb\((.*?),(.*?),(.*?)\)/, 'rgba($1,$2,$3,0.3)');
                                    } else if (typeof bgColor === 'string' && bgColor.startsWith('#')) {
                                        // HEX 색상 코드이면 rgba로 변환
                                        const r = parseInt(bgColor.slice(1, 3), 16);
                                        const g = parseInt(bgColor.slice(3, 5), 16);
                                        const b = parseInt(bgColor.slice(5, 7), 16);
                                        bgRgba = `rgba(${r},${g},${b},0.3)`;
                                    } else {
                                        // 기본값
                                        bgRgba = 'rgba(200,200,200,0.3)';
                                    }
                                    
                                    nodeObj.options.color = {
                                        background: bgRgba,
                                        border: 'rgba(150,150,150,0.3)',
                                        highlight: nodeObj.options.color.highlight
                                    };
                                    
                                    // 크기 감소
                                    nodeObj.options.size *= 0.9;
                                }
                            });
                        }
                        
                        // 다른 엣지 페이드 아웃
                        function fadeOtherEdges(highlightedEdges) {
                            Object.keys(network.body.edges).forEach(edgeId => {
                                if (!highlightedEdges.has(edgeId)) {
                                    // 원본 스타일 저장
                                    if (!originalEdgeStyles[edgeId]) {
                                        const edge = network.body.edges[edgeId];
                                        originalEdgeStyles[edgeId] = {
                                            color: edge.options.color,
                                            width: edge.options.width
                                        };
                                    }
                                    
                                    // 페이드 아웃 적용
                                    network.body.edges[edgeId].options.color = 'rgba(200,200,200,0.2)';
                                    network.body.edges[edgeId].options.width = 0.8;
                                }
                            });
                        }
                        
                        // 하이라이트 초기화
                        function resetHighlights() {
                            // 하이라이트된 노드 스타일 복원
                            highlightedNodes.forEach(nodeId => {
                                if (originalNodeStyles[nodeId] && network.body.nodes[nodeId]) {
                                    network.body.nodes[nodeId].options.color = originalNodeStyles[nodeId].color;
                                    network.body.nodes[nodeId].options.borderWidth = originalNodeStyles[nodeId].borderWidth;
                                    network.body.nodes[nodeId].options.size = originalNodeStyles[nodeId].size;
                                }
                            });
                            
                            // 하이라이트된 엣지 스타일 복원
                            highlightedEdges.forEach(edgeId => {
                                if (originalEdgeStyles[edgeId] && network.body.edges[edgeId]) {
                                    network.body.edges[edgeId].options.color = originalEdgeStyles[edgeId].color;
                                    network.body.edges[edgeId].options.width = originalEdgeStyles[edgeId].width;
                                }
                            });
                            
                            // 하이라이트 목록 초기화
                            highlightedNodes.clear();
                            highlightedEdges.clear();
                        }
                        
                        // 모든 스타일 초기화
                        function resetAll() {
                            // 모든 노드 스타일 복원
                            Object.keys(originalNodeStyles).forEach(nodeId => {
                                if (network.body.nodes[nodeId]) {
                                    network.body.nodes[nodeId].options.color = originalNodeStyles[nodeId].color;
                                    network.body.nodes[nodeId].options.borderWidth = originalNodeStyles[nodeId].borderWidth;
                                    network.body.nodes[nodeId].options.size = originalNodeStyles[nodeId].size;
                                }
                            });
                            
                            // 모든 엣지 스타일 복원
                            Object.keys(originalEdgeStyles).forEach(edgeId => {
                                if (network.body.edges[edgeId]) {
                                    network.body.edges[edgeId].options.color = originalEdgeStyles[edgeId].color;
                                    network.body.edges[edgeId].options.width = originalEdgeStyles[edgeId].width;
                                }
                            });
                            
                            // 하이라이트 목록 초기화
                            highlightedNodes.clear();
                            highlightedEdges.clear();
                            
                            // 원본 스타일 저장소 초기화
                            originalNodeStyles = {};
                            originalEdgeStyles = {};
                            
                            // 네트워크 리드로우
                            network.redraw();
                        }
                    });
                </script>
                """
                
                # 필요한 머리글/바닥글 추가
                head_end = "</head>"
                body_end = "</body>"
                
                # 스타일 추가
                if head_end in html:
                    html = html.replace(head_end, updated_style + head_end)
                
                # 사용자 정의 스크립트 추가
                if body_end in html and add_custom_js:
                    html = html.replace(body_end, custom_js + body_end)
            
            # 변경된 HTML 저장
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return html
            
        except Exception as e:
            logger.error(f"PyVis 네트워크 저장 중 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_centrality_plot(self, metric="in_degree", top_n=10):
        """중심성 지표 시각화 (내부 처리는 영문, 표시는 한글)"""
        try:
            # 메트릭스 존재 확인
            if not hasattr(self, 'metrics') or not self.metrics:
                logger.error(f"중심성 지표가 존재하지 않습니다.")
                return None
                
            # 지표 선택
            if metric not in self.metrics:
                # 사용 가능한 지표 목록 표시
                available_metrics = list(self.metrics.keys())
                if available_metrics:
                    logger.error(f"요청한 중심성 지표({metric})가 존재하지 않습니다. 사용 가능한 지표: {', '.join(available_metrics)}")
                else:
                    logger.error(f"요청한 중심성 지표({metric})가 존재하지 않으며, 사용 가능한 지표가 없습니다.")
                return None
            
            # 선택된 지표 값 가져오기
            metric_values = self.metrics[metric]
            
            # 지표 값이 비어있는지 확인
            if not metric_values:
                logger.error(f"선택한 중심성 지표({metric}) 값이 비어있습니다.")
                return None
            
            # 리스트 타입의 값을 처리하기 위한 정제 과정
            processed_values = {}
            for k, v in metric_values.items():
                # 값이 리스트인 경우 첫 번째 값 사용
                if isinstance(v, list):
                    if len(v) > 0:
                        processed_values[k] = v[0]
                    else:
                        processed_values[k] = 0
                # 숫자가 아닌 경우 변환 시도
                elif not isinstance(v, (int, float)):
                    try:
                        processed_values[k] = float(v)
                    except (ValueError, TypeError):
                        processed_values[k] = 0
                else:
                    processed_values[k] = v
            
            # 데이터프레임 변환 및 정렬
            df = pd.DataFrame(processed_values.items(), columns=['student_id', 'value'])
            
            # 이름이 문자열이 아닌 경우 문자열로 변환
            df['student_id'] = df['student_id'].apply(lambda x: str(x) if not isinstance(x, str) else x)
            
            df = df.sort_values('value', ascending=False).head(top_n)
            
            # 학생 ID 목록으로 학생 이름 대조표 만들기
            # student_id -> 실제 이름 매핑 수집
            name_mapping = {}
            for student_id in df['student_id']:
                # 여러 매핑 방식 시도
                real_name = None
                
                # 1. analyzer의 name_mapping 사용 (ID -> 이름)
                if hasattr(self, 'analyzer') and hasattr(self.analyzer, 'name_mapping') and student_id in self.analyzer.name_mapping:
                    real_name = self.analyzer.name_mapping[student_id]
                # 2. analyzer의 reverse_romanized 사용 (로마자 -> 한글)
                elif hasattr(self, 'analyzer') and hasattr(self.analyzer, 'reverse_romanized') and student_id in self.analyzer.reverse_romanized:
                    real_name = self.analyzer.reverse_romanized[student_id]
                # 3. 자체 original_names 매핑 사용
                elif hasattr(self, 'original_names') and student_id in self.original_names:
                    real_name = self.original_names[student_id]
                # 4. 변환 실패 시 원래 ID 그대로 사용
                else:
                    real_name = str(student_id)
                    
                name_mapping[student_id] = real_name
                
            # matplotlib 기본 폰트 설정 (영문 사용)
            plt.rcParams['font.family'] = 'DejaVu Sans'
            
            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # 컬러 팔레트 (구글 색상 사용)
            colors = ['#4285F4', '#EA4335', '#34A853', '#FBBC05', '#8E24AA', '#16A085']
            
            # Y축 레이블이 카테고리형 데이터가 아닌 숫자로 처리되는 문제 해결
            y_pos = np.arange(len(df))  # 숫자 위치값 생성
            
            # 반전된 순서로 그래프 생성 (위에서 아래로 내림차순)
            bars = ax.barh(y_pos, df['value'], 
                         color=[colors[i % len(colors)] for i in range(len(df))])
            
            # Y축 레이블 설정 (ID 표시)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df['student_id'])
            
            # 그래프 스타일링 
            ax.set_xlabel('Centrality Value', fontsize=12)
            
            # 중심성 지표별 적절한 제목 설정 (영문)
            metric_titles = {
                'in_degree': 'In-Degree Centrality',
                'out_degree': 'Out-Degree Centrality',
                'betweenness': 'Betweenness Centrality',
                'closeness': 'Closeness Centrality',
                'eigenvector': 'Eigenvector Centrality'
            }
            title = metric_titles.get(metric, metric)
            ax.set_title(f'Top {top_n} Students - {title}', fontsize=14, pad=20)
            
            # 값 주석 추가
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                       f'{width:.2f}', va='center', fontsize=10)
            
            # 그리드 추가
            ax.grid(axis='x', linestyle='--', alpha=0.6)
            
            # 레이아웃 조정
            plt.tight_layout()
            
            # 학생 ID와 실제 이름 대조표 추가 (Streamlit 표시 용)
            st.markdown("### 📋 학생 ID-이름 대조표")
            st.markdown("아래 표는 그래프에 표시된 학생 ID와 실제 이름의 대응표입니다.")
            
            # 대조표 데이터프레임 생성
            mapping_df = pd.DataFrame({
                "학생 ID": list(name_mapping.keys()),
                "실제 이름": list(name_mapping.values())
            })
            
            # 대조표 표시
            st.dataframe(mapping_df, use_container_width=True)
            
            return fig
            
        except Exception as e:
            logger.error(f"중심성 지표 시각화 중 오류 발생: {str(e)}")
            st.error(f"중심성 지표 시각화 중 오류가 발생했습니다: {str(e)}")
            return None
    
    def create_community_table(self):
        """커뮤니티별 학생 목록 생성"""
        try:
            # 커뮤니티 데이터가 없으면 가져오기
            if not hasattr(self, 'communities') or not self.communities:
                # 애널라이저가 있는지 확인
                if hasattr(self, 'analyzer') and self.analyzer:
                    self.communities = self.analyzer.get_communities()
                else:
                    # 애널라이저가 없으면 빈 데이터 반환
                    logger.warning("커뮤니티 테이블 생성 실패: analyzer가 설정되지 않았습니다.")
                    return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            if not self.communities or not isinstance(self.communities, dict):
                # 커뮤니티 데이터가 없거나 형식이 잘못된 경우 빈 데이터 반환
                logger.warning(f"커뮤니티 테이블 생성 실패: 잘못된 커뮤니티 데이터 형식 {type(self.communities)}")
                return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            # 커뮤니티별 학생 그룹화
            community_groups = {}
            try:
                # 커뮤니티 데이터 형식 검사
                is_nodeid_to_community = True
                for key in list(self.communities.keys())[:5]:  # 처음 몇 개만 확인
                    if not isinstance(key, (str, int)):
                        is_nodeid_to_community = False
                        break
                
                if is_nodeid_to_community:
                    # 구조: {노드ID: 커뮤니티ID, ...}
                    for node, community_id in self.communities.items():
                        # community_id가 리스트인 경우 (1개 이상의 커뮤니티에 속한 경우)
                        if isinstance(community_id, list):
                            # 첫 번째 커뮤니티만 사용
                            comm_id = str(community_id[0])
                        else:
                            comm_id = str(community_id)
                        
                        if comm_id not in community_groups:
                            community_groups[comm_id] = []
                        
                        # 노드가 문자열이 아닌 경우 문자열로 변환
                        node_str = str(node) if not isinstance(node, str) else node
                        community_groups[comm_id].append(node_str)
                else:
                    # 구조: {커뮤니티ID: [노드ID, ...], ...}
                    for community_id, members in self.communities.items():
                        comm_id = str(community_id)
                        
                        if comm_id not in community_groups:
                            community_groups[comm_id] = []
                        
                        # members가 리스트가 아닌 경우 리스트로 변환
                        if not isinstance(members, list):
                            members = [members]
                        
                        # 멤버를 문자열로 변환하여 추가
                        for member in members:
                            member_str = str(member) if not isinstance(member, str) else member
                            community_groups[comm_id].append(member_str)
            except Exception as e:
                logger.error(f"커뮤니티 그룹화 중 오류: {str(e)}")
                return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
            
            # 학생 ID를 실제 이름으로 변환하는 함수
            def get_real_student_name(student_id):
                # 1. analyzer의 name_mapping 사용 (ID -> 이름)
                if hasattr(self, 'analyzer') and hasattr(self.analyzer, 'name_mapping') and student_id in self.analyzer.name_mapping:
                    return self.analyzer.name_mapping[student_id]
                # 2. analyzer의 reverse_romanized 사용 (로마자 -> 한글)
                elif hasattr(self, 'analyzer') and hasattr(self.analyzer, 'reverse_romanized') and student_id in self.analyzer.reverse_romanized:
                    return self.analyzer.reverse_romanized[student_id]
                # 3. 자체 original_names 매핑 사용
                elif hasattr(self, 'original_names') and student_id in self.original_names:
                    return self.original_names[student_id]
                # 4. 변환 실패 시 원래 ID 그대로 사용
                else:
                    return str(student_id)
            
            # 결과 데이터 생성
            result_data = []
            for comm_id, members in community_groups.items():
                # 학생 수
                student_count = len(members)
                
                # 학생 ID를 실제 이름으로 변환
                real_name_members = [get_real_student_name(student_id) for student_id in members]
                
                # 주요 학생 (최대 5명)
                top_students = ', '.join(real_name_members[:5])
                if student_count > 5:
                    top_students += ', ...'
                
                result_data.append({
                    "그룹 ID": comm_id,
                    "학생 수": student_count,
                    "주요 학생": top_students
                })
            
            # 데이터프레임 생성
            result_df = pd.DataFrame(result_data)
            
            # 그룹 크기에 따라 정렬
            if not result_df.empty:
                result_df = result_df.sort_values(by="학생 수", ascending=False)
            
            return result_df
        
        except Exception as e:
            logger.error(f"커뮤니티 테이블 생성 실패: {str(e)}")
            return pd.DataFrame(columns=["그룹 ID", "학생 수", "주요 학생"])
    
    def get_centrality_metrics(self):
        """중심성 지표 반환 - analyzer의 지표를 사용"""
        if not self.metrics:
            # 중심성 지표가 계산되지 않았다면 계산
            self.metrics = self.analyzer.metrics
        return self.metrics 