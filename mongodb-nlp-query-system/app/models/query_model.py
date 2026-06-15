"""
Model for storing queries in database
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib
import json


class StoredQuery(BaseModel):
    """Model for storing generated queries in user_queries collection"""
    
    original_text: str = Field(..., description="User's original query text")
    normalized_text: str = Field(..., description="Normalized text for similarity")
    generated_query: Dict[str, Any] = Field(..., description="MongoDB query")
    collection_name: str = Field(..., description="Target collection")
    query_hash: str = Field(..., description="SHA-256 hash for exact matching")
    usage_count: int = Field(default=1, description="Number of times used")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    average_response_ms: Optional[int] = Field(None)
    
    @classmethod
    def create_hash(cls, text: str, collection: str) -> str:
        """Create hash from normalized text and collection"""
        normalized = text.lower().strip()
        content = f"{normalized}|{collection}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Normalize text for similarity matching"""
        import re
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        return text
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "Find users older than 25",
                "normalized_text": "find users older than 25",
                "generated_query": {"age": {"$gt": 25}},
                "collection_name": "users",
                "query_hash": "abc123...",
                "usage_count": 45
            }
        }