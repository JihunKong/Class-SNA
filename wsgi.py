"""
WSGI 진입점
Gunicorn 및 개발 서버용
"""
import os
from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
