"""
Repository for user_queries collection operations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId

from app.database.mongodb_client import mongodb_client
from app.models.query_model import StoredQuery
import logging

logger = logging.getLogger(__name__)


class QueryRepository:
    """CRUD operations for user_queries collection"""
    
    def __init__(self):
        self.collection_name = "user_queries"
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the collection instance"""
        return await mongodb_client.get_collection(self.collection_name)
    
    async def save_query(self, query: StoredQuery) -> str:
        """Save a generated query to the collection"""
        collection = await self.get_collection()
        
        query_dict = query.model_dump(exclude_none=True)
        query_dict["created_at"] = datetime.utcnow()
        query_dict["last_used"] = datetime.utcnow()
        
        result = await collection.insert_one(query_dict)
        logger.info(f"Saved query with hash: {query.query_hash}")
        
        return str(result.inserted_id)
    
    async def find_by_hash(self, query_hash: str) -> Optional[StoredQuery]:
        """Find query by its hash"""
        collection = await self.get_collection()
        doc = await collection.find_one({"query_hash": query_hash})
        
        if doc:
            return StoredQuery(**doc)
        return None
    
    async def find_similar_query(self, text: str, threshold: float = 0.85) -> Optional[StoredQuery]:
        """
        Find similar query using text similarity
        Note: This is a simplified version. In production, use embeddings.
        """
        collection = await self.get_collection()
        
        # Use MongoDB's text search as basic similarity
        cursor = collection.find(
            {"$text": {"$search": text}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(1)
        
        docs = await cursor.to_list(length=1)
        
        if docs and docs[0].get("score", 0) >= threshold:
            return StoredQuery(**docs[0])
        
        return None
    
    async def increment_usage(self, query_id: str) -> None:
        """Increment usage count for a query"""
        collection = await self.get_collection()
        
        await collection.update_one(
            {"_id": ObjectId(query_id)},
            {
                "$inc": {"usage_count": 1},
                "$set": {"last_used": datetime.utcnow()}
            }
        )
    
    async def get_recent_queries(self, limit: int = 10) -> List[StoredQuery]:
        """Get most recent queries"""
        collection = await self.get_collection()
        
        cursor = collection.find().sort("last_used", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        return [StoredQuery(**doc) for doc in docs]
    
    async def get_query_stats(self) -> Dict[str, Any]:
        """Get statistics about stored queries"""
        collection = await self.get_collection()
        
        total_queries = await collection.count_documents({})
        
        # Get most used collection
        pipeline = [
            {"$group": {"_id": "$collection_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        cursor = collection.aggregate(pipeline)
        top_collection = await cursor.to_list(length=1)
        
        # Get average usage count
        avg_usage_pipeline = [
            {"$group": {"_id": None, "avg_usage": {"$avg": "$usage_count"}}}
        ]
        cursor = collection.aggregate(avg_usage_pipeline)
        avg_usage = await cursor.to_list(length=1)
        
        return {
            "total_queries": total_queries,
            "most_used_collection": top_collection[0]["_id"] if top_collection else None,
            "average_usage_count": avg_usage[0]["avg_usage"] if avg_usage else 0,
            "cache_size": total_queries
        }
    
    async def delete_old_queries(self, days: int = 30) -> int:
        """Delete queries older than specified days"""
        collection = await self.get_collection()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await collection.delete_many({"created_at": {"$lt": cutoff_date}})
        logger.info(f"Deleted {result.deleted_count} old queries")
        
        return result.deleted_count


# Create singleton instance
query_repository = QueryRepository()