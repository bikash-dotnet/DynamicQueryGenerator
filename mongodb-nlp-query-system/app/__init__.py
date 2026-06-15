"""
MongoDB NLP Query System - Main Package
A natural language query interface for MongoDB with safety controls
"""

__version__ = "1.0.0"
__author__ = "AI Development Team"
__license__ = "MIT"

# Expose key classes at package level for easier imports
from app.config import settings
from app.main import app
from app.core.nlp_processor import NLPProcessor
from app.services.query_service import QueryService

__all__ = [
    "app",
    "settings",
    "NLPProcessor",
    "QueryService",
]