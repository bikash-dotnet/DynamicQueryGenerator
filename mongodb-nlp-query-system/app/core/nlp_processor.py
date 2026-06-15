"""
Natural Language Processing engine for query understanding
"""

import re
from typing import Dict, Any, List, Tuple, Optional
import logging
from enum import Enum

from app.config import settings
from app.core.schema_loader import schema_loader

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Query intent types"""
    SELECT = "SELECT"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    UNKNOWN = "UNKNOWN"


class NLPProcessor:
    """Process natural language to extract query intent and conditions"""
    
    def __init__(self):
        self.initialize_nlp_engine()
    
    def initialize_nlp_engine(self):
        """Initialize NLP engine based on configuration"""
        if settings.NLP_ENGINE == "spacy":
            self._init_spacy()
        elif settings.NLP_ENGINE == "google_adk":
            self._init_google_adk()
        else:
            raise ValueError(f"Unknown NLP engine: {settings.NLP_ENGINE}")
    
    nlp_processor = NLPProcessor()
