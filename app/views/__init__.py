"""
Views Blueprint - 페이지 라우트
"""
from flask import Blueprint

views_bp = Blueprint('views', __name__)

from app.views import main, analysis
