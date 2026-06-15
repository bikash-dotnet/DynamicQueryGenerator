"""
MongoDB connection manager with connection pooling and retry logic
"""

import asyncio
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB client wrapper with connection management"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False
        self._retry_count = 3
        self._retry_delay = 1  # seconds
    
    async def connect(self) -> None:
        """Establish connection to MongoDB with retry logic"""
        for attempt in range(self._retry_count):
            try:
                logger.info(f"Connecting to MongoDB (attempt {attempt + 1})...")
                
                self.client = AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    maxPoolSize=settings.MONGODB_MAX_CONNECTIONS,
                    minPoolSize=settings.MONGODB_MIN_CONNECTIONS,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                )
                
                # Verify connection
                await self.client.admin.command('ping')
                
                self.database = self.client[settings.DATABASE_NAME]
                self._is_connected = True
                
                logger.info(f"Connected to MongoDB: {settings.DATABASE_NAME}")
                
                # Create indexes
                await self._create_indexes()
                
                return
                
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (2 ** attempt))
                else:
                    raise ConnectionError(f"Failed to connect to MongoDB after {self._retry_count} attempts")
    
    async def disconnect(self) -> None:
        """Close MongoDB connection gracefully"""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self) -> None:
        """Create necessary indexes for collections"""
        try:
            # user_queries collection indexes
            user_queries = self.database["user_queries"]
            
            # Unique index on query_hash
            await user_queries.create_index("query_hash", unique=True)
            
            # TTL index for auto-deletion after 30 days
            await user_queries.create_index("created_at", expireAfterSeconds=2592000)
            
            # Compound index for common queries
            await user_queries.create_index([("collection_name", 1), ("last_used", -1)])
            
            # Text index for similarity search
            await user_queries.create_index([("original_text", "text")])
            
            # query_logs collection indexes
            query_logs = self.database["query_logs"]
            await query_logs.create_index("timestamp")
            await query_logs.create_index([("user_ip", 1), ("timestamp", -1)])
            await query_logs.create_index("was_rejected")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def get_collection(self, name: str):
        """Get a collection by name"""
        if not self._is_connected:
            raise ConnectionError("Not connected to MongoDB")
        return self.database[name]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        if not self._is_connected:
            return {"status": "disconnected", "error": "Not connected"}
        
        try:
            await self.client.admin.command('ping')
            return {
                "status": "healthy",
                "database": settings.DATABASE_NAME,
                "latency_ms": 0  # Would calculate actual latency in production
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Singleton instance
mongodb_client = MongoDBClient()