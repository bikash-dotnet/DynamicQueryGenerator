"""
Natural Language Processing engine for query understanding
"""

import os
import json
from pydoc import text
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
                self.nlp = spacy.load("en_core_web_md")
                logger.info("spaCy loaded successfully")
            except Exception:
                # model may not be installed
                self.nlp = None
                logger.warning("spaCy model not available; continuing with stub")
        except Exception:
            self.nlp = None
            logger.warning("spaCy not installed; continuing with stub")

    def _init_google_adk(self):
        """Initialize Google Gemini LLM."""
        try:
            import google.generativeai as genai
            api_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
            if not api_key:
                logger.warning("GEMINI_API_KEY not found. LLM features will be disabled.")
                self.llm_model = None
                return
            
            genai.configure(api_key=api_key)
            self.llm_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Google Gemini LLM loaded successfully")
        except ImportError:
            self.llm_model = None
            logger.warning("google-generativeai package not installed; continuing with regex stub")
        except Exception as e:
            self.llm_model = None
            logger.error(f"Failed to initialize Gemini LLM: {e}")
    
    async def detect_intent(self, text: str) -> Tuple[Intent, float]:
        """
        Detect the intent (SELECT, INSERT, UPDATE, DELETE, or UNKNOWN) from user text
        
        Args:
            text: User query text
            
        Returns:
            Tuple of (Intent, confidence_score)
        """
        text_lower = text.lower()
        
        # Keywords for each intent type
        select_keywords = ['find', 'get', 'show', 'list', 'query', 'search', 'retrieve', 'fetch', 'display', 'lookup', 'select', 'where', 'what','which', 'count','how many','total', 'sum', 'average', 'avg', 'min', 'max', 'group by']
        insert_keywords = ['add', 'create', 'insert', 'new', 'save', 'put', 'store', 'register','make', 'append']
        update_keywords = ['update', 'edit', 'change', 'modify', 'set', 'replace', 'alter', 'rename']
        delete_keywords = ['delete', 'remove', 'drop', 'erase', 'destroy', 'kill', 'clear', 'truncate']
        
        # Score each intent
        scores = {
            Intent.SELECT: sum(1 for kw in select_keywords if kw in text_lower),
            Intent.INSERT: sum(1 for kw in insert_keywords if kw in text_lower),
            Intent.UPDATE: sum(1 for kw in update_keywords if kw in text_lower),
            Intent.DELETE: sum(1 for kw in delete_keywords if kw in text_lower),
        }
        
        # Determine intent and confidence
        max_score = max(scores.values())
        if max_score == 0:
            return Intent.UNKNOWN, 0.0
        
        intent = max(scores, key=lambda k: scores[k])
        confidence = scores[intent] / sum(scores.values())
        
        logger.debug(f"Detected intent: {intent} (confidence: {confidence:.2f})")
        return intent, confidence
    
    async def detect_collection(self, text: str) -> Tuple[Optional[str], float]:
        """
        Detect which collection is being referenced in the query
        
        Args:
            text: User query text
            
        Returns:
            Tuple of (collection_name, confidence_score)
        """
        text_lower = text.lower()
        all_collections = schema_loader.get_all_collections()
        
        # Find matches for collection names
        matches = {}
        for collection in all_collections:
            collection_lower = collection.lower()
            # Check for exact matches, plural forms, and common variations
            if collection_lower in text_lower:
                matches[collection] = 2.0  # Exact match
            elif collection_lower.rstrip('s') in text_lower:  # Singular form
                matches[collection] = 1.5
            elif collection_lower + 's' in text_lower:  # Plural form
                matches[collection] = 1.5
        
        if not matches:
            return None, 0.0
        
        # Get best match
        collection = max(matches, key=lambda k: matches[k])
        confidence = matches[collection] / sum(matches.values())
        
        logger.debug(f"Detected collection: {collection} (confidence: {confidence:.2f})")
        return collection, confidence
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for similarity matching and storage
        
        Args:
            text: Input text to normalize
        
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation (keep alphanumeric and spaces)
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common stopwords (optional, can enhance similarity)
        stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'so', 'for', 'nor', 'yet',
                     'of', 'to', 'in', 'for', 'on', 'with', 'without', 'by', 'at',
                     'from', 'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'over', 'show', 'me', 'please', 'query'}
        
        words = text.split()
        text = ' '.join([word for word in words if word not in stopwords])
        
        return text
    
    async def extract_conditions(self, text: str, collection: str) -> Dict[str, Any]:
        """
        Extract filter conditions from query text
        
        Args:
            text: User query text
            collection: Target collection name
            
        Returns:
            Dictionary of query conditions (filters)
        """
        conditions = {}
        
        # Get schema for this collection
        schema = schema_loader.get_schema(collection)
        if not schema:
            logger.warning(f"Schema not found for collection: {collection}")
            return conditions
        
        # Extract field-value pairs from text
        # Simple pattern: look for "field is value" or "field equals value" or "field = value"
        text_lower = text.lower()
        fields = schema.get("properties", {})
        
        for field_name in fields.keys():
            field_lower = field_name.lower()
            
            # Pattern 1: "field is/equals/= value"
            patterns = [
                rf'\b{field_lower}\s+(?:is|equals?|=)\s+([^,\.\s]+)',
                rf'\b{field_lower}\s*:\s*([^,\.\s]+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    value = matches[0]
                    # Try to convert to appropriate type
                    conditions[field_name] = self._convert_value(value, fields[field_name])
                    break
        
        logger.debug(f"Extracted conditions: {conditions}")
        return conditions
    
    def _convert_value(self, value: str, field_schema: Dict[str, Any]) -> Any:
        """
        Convert string value to appropriate type based on field schema
        
        Args:
            value: String value to convert
            field_schema: Field schema defining expected type
            
        Returns:
            Converted value
        """
        field_type = field_schema.get("type", "string")
        
        # Remove quotes if present
        value = value.strip('\'"')
        
        if field_type == "integer":
            try:
                return int(value)
            except ValueError:
                return value
        elif field_type == "number":
            try:
                return float(value)
            except ValueError:
                return value
        elif field_type == "boolean":
            return value.lower() in ['true', 'yes', '1']
        else:
            return value
    
    async def generate_mongo_query(self, text: str, collection: str) -> Dict[str, Any]:
        """
        Generate a MongoDB query using an LLM.
        Returns a MongoDB query dictionary.
        """
        # Get schema for context
        schema = schema_loader.get_schema(collection)
        schema_str = json.dumps(schema.get("properties", {})) if schema else "Unknown schema"
        
        if hasattr(self, 'llm_model') and self.llm_model:
            prompt = f"""
            You are a MongoDB query generator. 
            Given the user request and the collection schema, output ONLY a valid MongoDB query as a JSON object.
            Do not include markdown blocks like ```json, do not include explanations. Just the raw JSON.
            
            User Request: "{text}"
            Collection Schema: {schema_str}
            
            Example Output:
            {{"status": "active", "age": {{"$gt": 30}}}}
            """
            try:
                response = self.llm_model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Clean up response text if markdown is still present
                if response_text.startswith("```json"):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith("```"):
                    response_text = response_text[3:-3].strip()
                    
                query = json.loads(response_text)
                logger.info(f"LLM generated query: {query}")
                return query
            except Exception as e:
                logger.error(f"LLM query generation failed: {e}. Falling back to regex extraction.")
        
        # Fallback to basic regex extraction
        extracted = await self.extract_conditions(text, collection)
        query = {}
        for field, value in extracted.items():
            query[field] = {"$eq": value}
        
        logger.debug(f"Fallback generated query: {query}")
        return query

    async def find_similar_query(self, text: str, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """
            Find similar previously executed query using text similarity
    
            Args:
            text: User's query text
            threshold: Similarity threshold (0-1)
    
            Returns:
            Similar query dict if found, None otherwise
        """
        from app.database.query_repository import query_repository
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
            # Get recent queries from database
        recent_queries = await query_repository.get_recent_queries(limit=100)
        
        if not recent_queries:
            return None
        
        # Normalize input text
        normalized_input = self.normalize_text(text)
        
        # Prepare texts for similarity comparison
        texts = [q.normalized_text for q in recent_queries]
        texts.append(normalized_input)
        
        # Calculate TF-IDF and cosine similarity
        try:
            vectorizer = TfidfVectorizer().fit_transform(texts)
            similarities = cosine_similarity(vectorizer[-1:], vectorizer[:-1]).flatten() # type: ignore
            
            # Find best match above threshold
            best_idx = similarities.argmax()
            best_score = similarities[best_idx]
            
            if best_score >= threshold:
                similar_query = recent_queries[best_idx]
                logger.info(f"Found similar query with score {best_score:.2f}: {similar_query.original_text[:50]}...")
                return similar_query.model_dump()
            
            return None
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return None

# module-level instance
nlp_processor = NLPProcessor()  # pyright: ignore[reportUndefinedVariable]
