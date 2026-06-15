"""
Query safety validator to prevent destructive operations
"""

import re
from typing import Tuple, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QuerySafetyValidator:
    """Multi-layer query safety validator"""
    
    # Forbidden patterns in natural language
    FORBIDDEN_PATTERNS = [
        (r'\bdelete\b', 'DELETE operation detected'),
        (r'\bremove\b', 'REMOVE operation detected'),
        (r'\bdrop\b', 'DROP operation detected'),
        (r'\btruncate\b', 'TRUNCATE operation detected'),
        (r'\bupdate\b', 'UPDATE operation detected'),
        (r'\bmodify\b', 'MODIFY operation detected'),
        (r'\balter\b', 'ALTER operation detected'),
        (r'\binsert\b', 'INSERT operation detected'),
        (r'\bcreate\b', 'CREATE operation detected'),
    ]
    
    # Forbidden MongoDB operators
    FORBIDDEN_OPERATORS = [
        '$where', '$function', '$eval', '$jsonSchema',
        '$out', '$merge', '$expr'
    ]
    
    # Allowed operations (only read)
    ALLOWED_OPERATIONS = ['find', 'count', 'aggregate', 'distinct']
    
    # Denial messages for different scenarios
    DENIAL_MESSAGES = {
        'DELETE': "🔒 Safety first! I cannot delete data. Please use SELECT queries to find your data.",
        'UPDATE': "🔒 Updates are not allowed. You can only query (SELECT) data.",
        'INSERT': "🔒 Insert operations are disabled. This system only supports data retrieval.",
        'DROP': "🔒 Dangerous operation detected. Dropping collections is not permitted.",
        'OPERATOR': "⚠️ Your query contains unsafe MongoDB operators. Only simple comparisons are allowed.",
        'GENERAL': "❌ This query cannot be executed for safety reasons."
    }
    
    def __init__(self):
        self.compiled_patterns = [(re.compile(pattern, re.IGNORECASE), msg) 
                                   for pattern, msg in self.FORBIDDEN_PATTERNS]
    
    async def validate_intent_safety(self, intent: str) -> Tuple[bool, str]:
        """
        Validate intent safety at NLP level
        
        Returns:
            (is_safe, reason_if_unsafe)
        """
        if intent != "SELECT":
            denial_msg = self.DENIAL_MESSAGES.get(intent, self.DENIAL_MESSAGES['GENERAL'])
            return False, denial_msg
        return True, ""
    
    async def validate_query_safety(self, query: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate query structure safety
        
        Returns:
            (is_safe, reason_if_unsafe)
        """
        # Check for forbidden operators
        for op in self.FORBIDDEN_OPERATORS:
            if self._contains_operator(query, op):
                return False, self.DENIAL_MESSAGES['OPERATOR']
        
        # Check for write operations in query
        if self._contains_write_operation(query):
            return False, self.DENIAL_MESSAGES['GENERAL']
        
        return True, ""
    
    def _contains_operator(self, query: Dict[str, Any], operator: str) -> bool:
        """Recursively check if query contains a specific operator"""
        if operator in query:
            return True
        
        for value in query.values():
            if isinstance(value, dict):
                if self._contains_operator(value, operator):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and self._contains_operator(item, operator):
                        return True
        
        return False
    
    def _contains_write_operation(self, query: Dict[str, Any]) -> bool:
        """Check for write operation indicators"""
        # Check for update operators
        update_ops = ['$set', '$unset', '$inc', '$push', '$pull', '$addToSet']
        for op in update_ops:
            if self._contains_operator(query, op):
                return True
        
        return False
    
    async def validate_text_safety(self, text: str) -> Tuple[bool, str]:
        """
        Validate natural language text for safety
        
        Returns:
            (is_safe, reason_if_unsafe)
        """
        text_lower = text.lower()
        
        for pattern, message in self.compiled_patterns:
            if pattern.search(text_lower):
                # Check for negation (e.g., "don't delete")
                match = pattern.search(text_lower)
                if match and not self._is_negated(text_lower, match.start()):
                    return False, message
        
        return True, ""
    
    def _is_negated(self, text: str, keyword_pos: int) -> bool:
        """Check if a keyword at position is negated"""
        negations = ['not', "don't", 'do not', "won't", 'will not', "shouldn't"]
        
        # Check 15 characters before keyword
        start = max(0, keyword_pos - 15)
        preceding = text[start:keyword_pos]
        
        for neg in negations:
            if neg in preceding:
                return True
        
        return False
    
    def get_helpful_suggestion(self, text: str) -> str:
        """Generate helpful suggestion for blocked query"""
        text_lower = text.lower()
        
        if 'delete' in text_lower:
            return "Try using 'find', 'show', or 'list' instead of 'delete'"
        elif 'update' in text_lower or 'modify' in text_lower:
            return "Try using 'find' to locate the records you want to see"
        elif 'insert' in text_lower or 'create' in text_lower:
            return "This system only reads data. Use 'show' or 'find' to query existing records"
        elif 'drop' in text_lower:
            return "Dropping collections is not allowed. You can only query data"
        else:
            return "Please rephrase your query as a data retrieval request (find, show, list)"
        
    def is_read_operation(self, text: str) -> bool:
        """Check if the query is a read operation"""
        read_patterns = [
            r'\b(count|sum|average|avg|min|max)\b',
            r'\b(find|show|get|list|retrieve|display|search)\b',
            r'\bhow many\b',
            r'\btotal number of\b',
            r'\bgroup by\b'
        ]
        
        for pattern in read_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


# Singleton instance
query_safety_validator = QuerySafetyValidator()