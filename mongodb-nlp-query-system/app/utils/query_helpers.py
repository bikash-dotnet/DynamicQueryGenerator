"""
Helper functions for working with MongoDB query objects
"""

from typing import Dict, Any, List
import json


def query_to_readable_string(query: Dict[str, Any]) -> str:
    """
    Convert MongoDB query object to readable string for display
    
    Example: {"age": {"$gt": 30}} -> "age > 30"
    """
    if not query:
        return "No conditions"
    
    conditions = []
    for field, condition in query.items():
        if isinstance(condition, dict):
            for op, value in condition.items():
                if op == "$gt":
                    conditions.append(f"{field} > {value}")
                elif op == "$lt":
                    conditions.append(f"{field} < {value}")
                elif op == "$gte":
                    conditions.append(f"{field} >= {value}")
                elif op == "$lte":
                    conditions.append(f"{field} <= {value}")
                elif op == "$eq":
                    conditions.append(f"{field} = {value}")
                elif op == "$ne":
                    conditions.append(f"{field} != {value}")
                elif op == "$in":
                    conditions.append(f"{field} in {value}")
                else:
                    conditions.append(f"{field}: {value}")
        else:
            conditions.append(f"{field} = {condition}")
    
    return " AND ".join(conditions)


def compare_queries(query1: Dict[str, Any], query2: Dict[str, Any]) -> float:
    """
    Compare two query objects for similarity
    
    Returns:
        Similarity score between 0 and 1
    """
    if query1 == query2:
        return 1.0
    
    # Convert to strings for comparison
    str1 = json.dumps(query1, sort_keys=True)
    str2 = json.dumps(query2, sort_keys=True)
    
    # Simple length-based similarity
    from difflib import SequenceMatcher
    return SequenceMatcher(None, str1, str2).ratio()


def extract_query_fields(query: Dict[str, Any]) -> List[str]:
    """
    Extract field names from query object
    
    Example: {"age": {"$gt": 30}, "status": "active"} -> ["age", "status"]
    """
    fields = []
    
    for key in query.keys():
        if not key.startswith('$'):  # Skip operators
            fields.append(key)
    
    return fields


def extract_query_operators(query: Dict[str, Any]) -> List[str]:
    """
    Extract MongoDB operators used in query
    
    Example: {"age": {"$gt": 30}} -> ["$gt"]
    """
    operators = set()
    
    def extract(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.startswith('$'):
                    operators.add(key)
                extract(value)
        elif isinstance(obj, list):
            for item in obj:
                extract(item)
    
    extract(query)
    return list(operators)