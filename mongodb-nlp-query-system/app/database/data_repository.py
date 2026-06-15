"""
Repository for executing queries on business data collections
"""

from typing import List, Dict, Any, Tuple, Optional
import time
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.mongodb_client import mongodb_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class DataRepository:
    """Execute queries on business data collections"""
    
    async def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name"""
        return await mongodb_client.get_collection(name)
    
    async def execute_query(
        self, 
        collection_name: str, 
        query: Dict[str, Any], 
        limit: int = None,
        skip: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Execute a find query and return results with total count
        
        Returns:
            Tuple of (results list, total count)
        """
        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT
        
        start_time = time.time()
        
        try:
            collection = await self.get_collection(collection_name)
            
            # Validate collection exists
            if collection_name not in await self.get_collection_names():
                raise ValueError(f"Collection '{collection_name}' does not exist")
            
            # Execute count with timeout
            total_count = await self._count_with_timeout(collection, query)
            
            # Execute find with timeout and limit
            cursor = collection.find(query).skip(skip).limit(limit)
            
            # Add sort if specified in query (optional)
            if "$sort" in query:
                cursor = cursor.sort(query["$sort"])
            
            results = await self._fetch_with_timeout(cursor, limit)
            
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
        collections = await db.list_collection_names()
        
        # Exclude internal collections
        exclude = ["user_queries", "query_logs", "system.indexes"]
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