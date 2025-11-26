"""
분석 결과 API
"""
from flask import jsonify, session, request

from app.api import api_bp


@api_bp.route('/network', methods=['GET'])
def get_network():
    """네트워크 그래프 데이터"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    from app.services.visualizer import NetworkVisualizer

    network_data = session.get('network_data')
    metrics = session.get('metrics')
    communities = session.get('communities')

    # PyVis HTML 생성
    visualizer = NetworkVisualizer(network_data, metrics, communities)
    layout = request.args.get('layout', 'barnes_hut')
    html = visualizer.generate_pyvis_html(layout=layout)

    return jsonify({
        'html': html,
        'stats': {
            'nodes': session.get('node_count', 0),
            'edges': session.get('edge_count', 0),
            'communities': len(set(communities.values())) if communities else 0
        }
    })


@api_bp.route('/centrality/<metric>', methods=['GET'])
def get_centrality(metric):
    """중심성 지표 데이터"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    valid_metrics = ['in_degree', 'out_degree', 'betweenness', 'closeness', 'eigenvector']
    if metric not in valid_metrics:
        return jsonify({'error': f'유효하지 않은 지표입니다. 가능한 값: {valid_metrics}'}), 400

    metrics = session.get('metrics', {})
    metric_data = metrics.get(metric, {})

    # 상위 N개
    top_n = request.args.get('top_n', 10, type=int)
    sorted_data = sorted(metric_data.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return jsonify({
        'metric': metric,
        'labels': [item[0] for item in sorted_data],
        'values': [round(item[1], 4) for item in sorted_data]
    })


@api_bp.route('/communities', methods=['GET'])
def get_communities():
    """커뮤니티(그룹) 정보"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    communities = session.get('communities', {})

    # 커뮤니티별 구성원 그룹화
    community_groups = {}
    for node, comm_id in communities.items():
        if comm_id not in community_groups:
            community_groups[comm_id] = []
        community_groups[comm_id].append(node)

    return jsonify({
        'count': len(community_groups),
        'groups': community_groups
    })


@api_bp.route('/students', methods=['GET'])
def get_students():
    """학생 목록 및 기본 정보"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    metrics = session.get('metrics', {})
    communities = session.get('communities', {})

    students = []
    in_degree = metrics.get('in_degree', {})
    out_degree = metrics.get('out_degree', {})
    betweenness = metrics.get('betweenness', {})

    for name in in_degree.keys():
        students.append({
            'name': name,
            'in_degree': round(in_degree.get(name, 0), 4),
            'out_degree': round(out_degree.get(name, 0), 4),
            'betweenness': round(betweenness.get(name, 0), 4),
            'community': communities.get(name, 0)
        })

    # 인기도(in_degree) 기준 정렬
    students.sort(key=lambda x: x['in_degree'], reverse=True)

    return jsonify({'students': students})


@api_bp.route('/students/<name>', methods=['GET'])
def get_student_detail(name):
    """개별 학생 상세 분석"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    metrics = session.get('metrics', {})
    communities = session.get('communities', {})
    network_data = session.get('network_data', {})

    if name not in metrics.get('in_degree', {}):
        return jsonify({'error': f'학생 {name}을(를) 찾을 수 없습니다.'}), 404

    # 연결된 학생들
    edges = network_data.get('edges', [])
    incoming = [e['source'] for e in edges if e['target'] == name]
    outgoing = [e['target'] for e in edges if e['source'] == name]

    return jsonify({
        'name': name,
        'metrics': {
            'in_degree': round(metrics['in_degree'].get(name, 0), 4),
            'out_degree': round(metrics['out_degree'].get(name, 0), 4),
            'betweenness': round(metrics['betweenness'].get(name, 0), 4),
            'closeness': round(metrics['closeness'].get(name, 0), 4),
            'eigenvector': round(metrics['eigenvector'].get(name, 0), 4)
        },
        'community': communities.get(name, 0),
        'connections': {
            'incoming': incoming,
            'outgoing': outgoing,
            'mutual': list(set(incoming) & set(outgoing))
        }
    })


@api_bp.route('/isolated', methods=['GET'])
def get_isolated():
    """고립 학생 목록"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    metrics = session.get('metrics', {})
    in_degree = metrics.get('in_degree', {})
    out_degree = metrics.get('out_degree', {})

    # 고립 기준: in_degree와 out_degree 모두 낮은 학생
    threshold = request.args.get('threshold', 0.1, type=float)

    isolated = []
    for name in in_degree.keys():
        in_d = in_degree.get(name, 0)
        out_d = out_degree.get(name, 0)
        if in_d <= threshold and out_d <= threshold:
            isolated.append({
                'name': name,
                'in_degree': round(in_d, 4),
                'out_degree': round(out_d, 4)
            })

    return jsonify({
        'count': len(isolated),
        'threshold': threshold,
        'students': isolated
    })
