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
            self._init_spacy() # type: ignore
        elif settings.NLP_ENGINE == "google_adk":
            self._init_google_adk() # type: ignore
        else:
            raise ValueError(f"Unknown NLP engine: {settings.NLP_ENGINE}")
    
    def _init_spacy(self):
        """Initialize spaCy engine if available; otherwise set a safe stub."""
        try:
            import spacy
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy loaded successfully")
            except Exception:
                # model may not be installed
                self.nlp = None
                logger.warning("spaCy model not available; continuing with stub")
        except Exception:
            self.nlp = None
            logger.warning("spaCy not installed; continuing with stub")

    def _init_google_adk(self):
        """Placeholder initializer for Google ADK engine."""
        # Google ADK integration not implemented; use stub
        self.nlp = None
        logger.warning("google_adk engine selected but not implemented; using stub")
    

# module-level instance
nlp_processor = NLPProcessor()  # pyright: ignore[reportUndefinedVariable]
