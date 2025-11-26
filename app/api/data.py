"""
데이터 업로드 및 처리 API
"""
import os
import uuid
from flask import request, jsonify, session, current_app
from werkzeug.utils import secure_filename

from app.api import api_bp


def allowed_file(filename):
    """허용된 파일 확장자인지 확인"""
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'csv', 'xlsx', 'xls'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """파일 업로드 처리"""
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '허용되지 않는 파일 형식입니다. CSV, XLSX, XLS만 가능합니다.'}), 400

    # 고유 세션 ID 생성
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id

    # 파일 저장
    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    session_folder = os.path.join(upload_folder, session_id)
    os.makedirs(session_folder, exist_ok=True)

    file_path = os.path.join(session_folder, filename)
    file.save(file_path)

    # 세션에 파일 정보 저장
    session['uploaded_file'] = file_path
    session['filename'] = filename

    return jsonify({
        'success': True,
        'session_id': session_id,
        'filename': filename,
        'message': '파일이 업로드되었습니다.'
    })


@api_bp.route('/sheet', methods=['POST'])
def process_sheet():
    """Google Sheets URL 처리"""
    data = request.get_json()
    sheet_url = data.get('url')

    if not sheet_url:
        return jsonify({'error': 'Google Sheets URL이 필요합니다.'}), 400

    # 세션 ID 생성
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session['sheet_url'] = sheet_url

    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Google Sheets URL이 등록되었습니다.'
    })


@api_bp.route('/analyze', methods=['POST'])
def analyze_data():
    """데이터 분석 시작"""
    from app.services.data_processor import DataProcessor
    from app.services.network_analyzer import NetworkAnalyzer

    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': '먼저 데이터를 업로드해주세요.'}), 400

    try:
        # 데이터 처리
        processor = DataProcessor()

        # 파일 또는 Google Sheets에서 데이터 로드
        if session.get('uploaded_file'):
            file_path = session['uploaded_file']
            filename = session.get('filename', 'data.csv')

            # 파일 내용 읽기
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # process_uploaded_file 메서드 사용 (load + analyze + convert)
            result = processor.process_uploaded_file(file_content, filename)
            network_data = result['network_data']

        elif session.get('sheet_url'):
            result = processor.process_survey_data(session['sheet_url'])
            network_data = result['network_data']
        else:
            return jsonify({'error': '데이터 소스가 없습니다.'}), 400

        # 네트워크 분석
        analyzer = NetworkAnalyzer(network_data)
        metrics = analyzer.calculate_all_metrics()
        communities = analyzer.detect_communities()

        # 세션에 분석 결과 저장
        session['analyzed'] = True
        session['network_data'] = network_data
        session['metrics'] = metrics
        session['communities'] = communities
        session['node_count'] = len(analyzer.graph.nodes())
        session['edge_count'] = len(analyzer.graph.edges())

        return jsonify({
            'success': True,
            'message': '분석이 완료되었습니다.',
            'stats': {
                'nodes': session['node_count'],
                'edges': session['edge_count'],
                'communities': len(set(communities.values())) if communities else 0
            }
        })

    except Exception as e:
        return jsonify({'error': f'분석 중 오류가 발생했습니다: {str(e)}'}), 500


@api_bp.route('/examples', methods=['GET'])
def get_examples():
    """예시 데이터 목록"""
    examples = [
        {'name': 'example1.csv', 'description': '예시 데이터 1 - 30명 학급'},
        {'name': 'example2.csv', 'description': '예시 데이터 2 - 25명 학급'}
    ]
    return jsonify({'examples': examples})


@api_bp.route('/examples/<name>', methods=['GET'])
def use_example(name):
    """예시 데이터 사용"""
    allowed_examples = ['example1.csv', 'example2.csv']
    if name not in allowed_examples:
        return jsonify({'error': '유효하지 않은 예시 데이터입니다.'}), 400

    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session['uploaded_file'] = os.path.join('data', name)

    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': f'예시 데이터 {name}가 로드되었습니다.'
    })
