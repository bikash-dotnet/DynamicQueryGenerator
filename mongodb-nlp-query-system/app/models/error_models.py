"""
Standard error response models
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model"""
    
    success: bool = Field(False, description="Always false for errors")
    error_code: str = Field(..., description="Error code for client handling")
    message: str = Field(..., description="User-friendly error message")
    details: Optional[str] = Field(None, description="Technical details")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    request_id: str = Field(..., description="Unique request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    available_collections: Optional[List[str]] = Field(None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "OPERATION_NOT_ALLOWED",
                "message": "Delete operations are not permitted",
                "suggestion": "Try: 'Find user John' instead",
                "request_id": "req_123abc",
                "timestamp": "2026-06-14T10:30:00Z"
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """Validation error response with field details"""
    
    field_errors: Dict[str, List[str]] = Field(default_factory=dict)


class RateLimitErrorResponse(ErrorResponse):
    """Rate limit exceeded response"""
    
    retry_after_seconds: int = Field(..., description="Seconds to wait before retry")