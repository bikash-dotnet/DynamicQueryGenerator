"""
MongoDB query generator from extracted conditions
"""

from typing import Dict, Any, List, Optional
import logging

from app.config import settings
from app.core.schema_loader import schema_loader

logger = logging.getLogger(__name__)


class QueryGenerator:
    """Generate MongoDB queries from extracted conditions"""
    
    def __init__(self):
        self.allowed_operators = {
            '$eq', '$ne', '$gt', '$gte', '$lt', '$lte',
            '$in', '$nin', '$regex', '$exists', '$type',
            '$and', '$or', '$nor'
        }
    
    def build_query(self, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build MongoDB query from list of conditions
        
        Args:
            conditions: List of {"field": str, "operator": str, "value": Any}
        
        Returns:
            MongoDB query dictionary
        """
        if not conditions:
            return {}
        
        # Check if we need OR logic
        has_or = any(cond.get('is_or', False) for cond in conditions)
        
        if has_or:
            # Build $or query
            or_conditions = []
            and_conditions = []
            
            for cond in conditions:
                condition = {cond['field']: {cond['operator']: cond['value']}}
                if cond.get('is_or', False):
                    or_conditions.append(condition)
                else:
                    and_conditions.append(condition)
            
            query = {}
            if and_conditions:
                query['$and'] = and_conditions
            if or_conditions:
                query['$or'] = or_conditions
            
            return query
        
        else:
            # Simple AND query
            query = {}
            for cond in conditions:
                query[cond['field']] = {cond['operator']: cond['value']}
            
            return query
    
    def add_default_limit(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Add default limit to query"""
        query['$limit'] = settings.DEFAULT_QUERY_LIMIT
        return query
    
    def add_sorting(self, query: Dict[str, Any], sort_field: str, order: str = "asc") -> Dict[str, Any]:
        """Add sorting to query"""
        sort_order = 1 if order.lower() == "asc" else -1
        query['$sort'] = {sort_field: sort_order}
        return query
    
    def build_projection(self, fields: List[str]) -> Dict[str, Any]:
        """Build projection to select specific fields"""
        projection = {field: 1 for field in fields}
        projection['_id'] = 1  # Always include _id
        return projection
    
    def validate_query(self, collection: str, query: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate query against schema
        
        Returns:
            (is_valid, error_message)
        """
        # Remove system operators for validation
        system_ops = {'$limit', '$sort', '$projection'}
        clean_query = {k: v for k, v in query.items() if k not in system_ops}
        
        # Handle $and/$or
        if '$and' in clean_query:
            for subquery in clean_query['$and']:
                is_valid, error = self._validate_single_query(collection, subquery)
                if not is_valid:
                    return False, error
        elif '$or' in clean_query:
            for subquery in clean_query['$or']:
                is_valid, error = self._validate_single_query(collection, subquery)
                if not is_valid:
                    return False, error
        else:
            return self._validate_single_query(collection, clean_query)
        
        return True, None
    
    def _validate_single_query(self, collection: str, query: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a single query (no $and/$or)"""
        for field, condition in query.items():
            # Check field exists
            if not schema_loader.validate_field(collection, field):
                searchable_fields = schema_loader.get_searchable_fields(collection)
                return False, f"Field '{field}' not found in collection '{collection}'. Available fields: {', '.join(searchable_fields)}"
            
            # Check operator is allowed
            if isinstance(condition, dict):
                for op in condition.keys():
                    if op not in self.allowed_operators:
                        return False, f"Operator '{op}' is not allowed. Allowed operators: {', '.join(self.allowed_operators)}"
        
        return True, None
    
    def sanitize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Remove dangerous operators and sanitize query"""
        sanitized = {}
        
        for key, value in query.items():
            # Skip dangerous operators
            if key in ['$where', '$function', '$eval']:
                logger.warning(f"Removed dangerous operator: {key}")
                continue
            
            # Recursively sanitize nested queries
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_query(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def build_count_query(self, base_query: Dict[str, Any]) -> Dict[str, Any]:
        """Build query for counting documents"""
        # Remove limit and sort for count
        count_query = {k: v for k, v in base_query.items() 
                      if k not in ['$limit', '$sort', '$projection']}
        return count_query


# Singleton instance
query_generator = QueryGenerator()