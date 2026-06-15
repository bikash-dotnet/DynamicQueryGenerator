"""
Request and response models for user queries
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class UserQueryRequest(BaseModel):
    """User query request model"""
    
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Natural language query text"
    )
    collection: Optional[str] = Field(
        None,
        description="Target collection (auto-detect if not specified)"
    )
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Sanitize and validate query text"""
        # Remove excessive whitespace
        v = " ".join(v.split())
        
        # Check for obvious injection attempts
        dangerous_patterns = ["$where", "$function", "db.eval"]
        for pattern in dangerous_patterns:
            if pattern in v.lower():
                raise ValueError(f"Dangerous pattern detected: {pattern}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Show me all users older than 30 from India",
                "collection": "users"
            }
        }


class QueryResponse(BaseModel):
    """Query response model"""
    
    success: bool = Field(..., description="Whether query succeeded")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    total_count: int = Field(0, description="Total matching records")
    query_used: Dict[str, Any] = Field(..., description="MongoDB query used")
    from_cache: bool = Field(False, description="Whether response came from cache")
    execution_time_ms: int = Field(0, description="Execution time in milliseconds")
    allow_export: bool = Field(False, description="Whether export is available")
    message: Optional[str] = Field(None, description="Additional message")
    
    @field_validator("total_count")
    @classmethod
    def validate_total_count(cls, v: int) -> int:
        """Validate total count"""
        if v < 0:
            raise ValueError("Total count cannot be negative")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "results": [{"name": "John Doe", "age": 35}],
                "total_count": 47,
                "query_used": {"age": {"$gt": 30}},
                "from_cache": False,
                "execution_time_ms": 234,
                "allow_export": True,
                "message": "Showing 5 of 47 records"
            }
        }