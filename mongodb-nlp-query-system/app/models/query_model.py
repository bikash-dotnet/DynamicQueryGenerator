"""
Model for storing queries in database
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer, field_validator
import hashlib
import json


class StoredQuery(BaseModel):
    """Model for storing generated queries in user_queries collection"""
    
    original_text: str = Field(..., description="User's original query text")
    normalized_text: str = Field(..., description="Normalized text for similarity")
    generated_query_object: Dict[str, Any] = Field(default_factory=dict, description="MongoDB query as object")
    generated_query_string: str = Field(default="{}", description="MongoDB query as JSON string")
    collection_name: str = Field(..., description="Target collection")
    query_hash: str = Field(..., description="SHA-256 hash for exact matching")
    usage_count: int = Field(default=1, description="Number of times used")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    average_response_ms: Optional[int] = Field(None)
    
    @field_validator("generated_query_string", mode="before")
    @classmethod
    def ensure_query_string(cls, v, info):
        """Ensure query string is set from object if missing"""
        if (not v or v == "{}") and info.data.get("generated_query_object"):
            return json.dumps(info.data["generated_query_object"], default=str)
        return v if v else "{}"
    
    @field_validator("generated_query_object", mode="before")
    @classmethod
    def ensure_query_object(cls, v, info):
        """Ensure query object is set from string if missing"""
        if (not v or v == {}) and info.data.get("generated_query_string"):
            try:
                return json.loads(info.data["generated_query_string"])
            except:
                return {}
        return v if v else {}
    
    @classmethod
    def create_hash(cls, text: str, collection: str) -> str:
        """Create hash from normalized text and collection"""
        normalized = text.lower().strip()
        normalized = ' '.join(normalized.split())
        content = f"{normalized}|{collection}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Normalize text for similarity matching"""
        import re
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "Find users older than 25",
                "normalized_text": "find users older than 25",
                "generated_query_object": {"age": {"$gt": 25}},
                "generated_query_string": "{\"age\":{\"$gt\":25}}",
                "collection_name": "users",
                "query_hash": "abc123...",
                "usage_count": 45
            }
        }