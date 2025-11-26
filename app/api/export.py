"""
내보내기 API
"""
import io
from flask import jsonify, session, send_file, request

from app.api import api_bp


@api_bp.route('/export/<format>', methods=['GET'])
def export_data(format):
    """분석 결과 내보내기"""
    if not session.get('analyzed'):
        return jsonify({'error': '분석된 데이터가 없습니다.'}), 404

    valid_formats = ['csv', 'excel', 'json']
    if format not in valid_formats:
        return jsonify({'error': f'유효하지 않은 형식입니다. 가능한 값: {valid_formats}'}), 400

    metrics = session.get('metrics', {})
    communities = session.get('communities', {})

    if format == 'json':
        return jsonify({
            'metrics': metrics,
            'communities': communities,
            'stats': {
                'nodes': session.get('node_count', 0),
                'edges': session.get('edge_count', 0)
            }
        })

    elif format == 'csv':
        import pandas as pd

        # DataFrame 생성
        data = []
        in_degree = metrics.get('in_degree', {})
        out_degree = metrics.get('out_degree', {})
        betweenness = metrics.get('betweenness', {})
        closeness = metrics.get('closeness', {})
        eigenvector = metrics.get('eigenvector', {})

        for name in in_degree.keys():
            data.append({
                '학생': name,
                '인기도(In-Degree)': round(in_degree.get(name, 0), 4),
                '활동성(Out-Degree)': round(out_degree.get(name, 0), 4),
                '매개중심성': round(betweenness.get(name, 0), 4),
                '근접중심성': round(closeness.get(name, 0), 4),
                '영향력': round(eigenvector.get(name, 0), 4),
                '그룹': communities.get(name, 0)
            })

        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='class_sna_analysis.csv'
        )

    elif format == 'excel':
        import pandas as pd

        # DataFrame 생성
        data = []
        in_degree = metrics.get('in_degree', {})
        out_degree = metrics.get('out_degree', {})
        betweenness = metrics.get('betweenness', {})
        closeness = metrics.get('closeness', {})
        eigenvector = metrics.get('eigenvector', {})

        for name in in_degree.keys():
            data.append({
                '학생': name,
                '인기도(In-Degree)': round(in_degree.get(name, 0), 4),
                '활동성(Out-Degree)': round(out_degree.get(name, 0), 4),
                '매개중심성': round(betweenness.get(name, 0), 4),
                '근접중심성': round(closeness.get(name, 0), 4),
                '영향력': round(eigenvector.get(name, 0), 4),
                '그룹': communities.get(name, 0)
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='분석결과', index=False)
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='class_sna_analysis.xlsx'
        )
