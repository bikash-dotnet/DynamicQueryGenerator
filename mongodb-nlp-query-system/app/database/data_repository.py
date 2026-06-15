"""
Repository for executing queries on business data collections
"""

from typing import List, Dict, Any, Tuple, Optional
import time
from datetime import datetime, date
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId

from app.database.mongodb_client import mongodb_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def convert_objectid_to_str(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively convert ObjectId and datetime to JSON serializable types
    
    Args:
        doc: MongoDB document with ObjectId fields
    
    Returns:
        Document with ObjectId converted to string and datetime to ISO format
    """
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, date):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = convert_objectid_to_str(value)
            elif isinstance(value, list):
                result[key] = [
                    convert_objectid_to_str(item) if isinstance(item, dict) 
                    else (str(item) if isinstance(item, ObjectId) else item)
                    for item in value
                ]
            else:
                result[key] = value
        return result
    return doc


class DataRepository:
    """Execute queries on business data collections"""
    
    async def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name"""
        return await mongodb_client.get_collection(name)
    
    async def execute_query(
        self, 
        collection_name: str, 
        query: Dict[str, Any], 
        limit: Optional[int] = None,
        skip: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Execute a find query and return results with total count
        
        Returns:
            Tuple of (results list, total count)
        """
        start_time = time.time()
        fetch_limit = limit if limit is not None else settings.DEFAULT_QUERY_LIMIT
        
        try:
            collection = await self.get_collection(collection_name)
            
            # Validate collection exists
            collections = await self.get_collection_names()
            if collection_name not in collections:
                raise ValueError(f"Collection '{collection_name}' does not exist. Available: {collections}")
            
            # Execute count with timeout
            total_count = await self._count_with_timeout(collection, query)
            
            # Execute find with timeout and limit
            cursor = collection.find(query).skip(skip).limit(fetch_limit)
            
            # Add sort if specified in query (optional)
            if "$sort" in query:
                cursor = cursor.sort(query["$sort"])
            
            results = await self._fetch_with_timeout(cursor, fetch_limit)
            
            # Convert ObjectId to string for JSON serialization
            results = [convert_objectid_to_str(doc) for doc in results]
            
            execution_time = (time.time() - start_time) * 1000
            logger.debug(f"Query executed in {execution_time:.2f}ms, returned {len(results)} results")
            
            return results, total_count
            
        except Exception as e:
            logger.error(f"Failed to execute query on {collection_name}: {e}")
            raise
    
    async def _count_with_timeout(self, collection, query: Dict) -> int:
        """Count documents with timeout"""
        import asyncio
        
        try:
            return await asyncio.wait_for(
                collection.count_documents(query),
                timeout=settings.QUERY_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning(f"Count query timed out after {settings.QUERY_TIMEOUT_SECONDS}s")
            raise TimeoutError("Query count operation timed out")
    
    async def _fetch_with_timeout(self, cursor, limit: int) -> List[Dict]:
        """Fetch documents with timeout"""
        import asyncio
        
        try:
            return await asyncio.wait_for(
                cursor.to_list(length=limit),
                timeout=settings.QUERY_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning(f"Fetch query timed out after {settings.QUERY_TIMEOUT_SECONDS}s")
            raise TimeoutError("Data fetch operation timed out")
    
    async def get_collection_names(self) -> List[str]:
        """Get list of all collection names (excluding system collections)"""
        db = mongodb_client.database
        if db is None:
            return []
        
        collections = await db.list_collection_names()
        
        # Exclude internal collections
        exclude = ["user_queries", "query_logs", "system.indexes", "system.views"]
        return [col for col in collections if col not in exclude]
    
    async def validate_collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists"""
        collections = await self.get_collection_names()
        return collection_name in collections
    
    async def get_total_count(self, collection_name: str, query: Dict) -> int:
        """Get total count of matching documents without fetching data"""
        collection = await self.get_collection(collection_name)
        return await collection.count_documents(query)
    
    async def explain_query(self, collection_name: str, query: Dict) -> Dict:
        """Get query execution plan for performance analysis"""
        collection = await self.get_collection(collection_name)
        return await collection.find(query).explain()


# Singleton instance
data_repository = DataRepository()