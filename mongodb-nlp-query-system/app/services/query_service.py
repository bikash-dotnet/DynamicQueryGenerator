"""
Orchestration service for query processing
"""

import time
import uuid
from typing import Optional, Dict, Any, List
import logging

from app.models.user_request import UserQueryRequest, QueryResponse
from app.models.query_model import StoredQuery
from app.core.nlp_processor import nlp_processor, NLPProcessor
from app.core.query_generator import query_generator
from app.core.query_validator import query_safety_validator
from app.core.schema_loader import schema_loader
from app.database.query_repository import query_repository
from app.database.data_repository import data_repository
from app.config import settings

logger = logging.getLogger(__name__)


class QueryService:
    """Orchestrate the entire query processing pipeline"""
    
    def __init__(self):
        self.query_cache = {}  # Simple in-memory cache
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def process_query(self, request: UserQueryRequest) -> QueryResponse:
        """
        Main orchestration method for query processing
        
        Flow:
        1. Validate request and check safety
        2. Check cache for similar query
        3. Generate new query if not cached
        4. Execute query against database
        5. Cache new query
        6. Return formatted response
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Processing query [id={request_id}]: {request.text[:100]}")
        
        try:
            # Step 1: Safety validation
            is_safe, reason = await query_safety_validator.validate_text_safety(request.text)
            if not is_safe:
                suggestion = query_safety_validator.get_helpful_suggestion(request.text)
                return QueryResponse(
                    success=False,
                    query_id=None,
                    results=[],
                    total_count=0,
                    query_used={},
                    from_cache=False,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    allow_export=False,
                    message=f"Safety check failed: {reason}. {suggestion}"
                )
            
            # Step 2: Detect intent
            intent, confidence = await nlp_processor.detect_intent(request.text)
            is_safe, reason = await query_safety_validator.validate_intent_safety(intent)
            if not is_safe:
                suggestion = query_safety_validator.get_helpful_suggestion(request.text)
                return QueryResponse(
                    success=False,
                    query_id=None,
                    results=[],
                    total_count=0,
                    query_used={},
                    from_cache=False,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    allow_export=False,
                    message=f"Operation not allowed: {reason}. {suggestion}"
                )
            
            # Step 3: Detect collection
            collection, collection_confidence = await nlp_processor.detect_collection(request.text)
            if request.collection:
                collection = request.collection
            
            if not collection:
                available = schema_loader.get_all_collections()
                return QueryResponse(
                    success=False,
                    query_id=None,
                    results=[],
                    total_count=0,
                    query_used={},
                    from_cache=False,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    allow_export=False,
                    message=f"Could not determine which collection to query. Available: {', '.join(available)}"
                )
            
            # Step 4: Check cache
            cached_query = await self._check_cache(request.text, collection)
            from_cache = cached_query is not None
            
            if from_cache:
                stored_query = cached_query
                query = stored_query.get("generated_query", {})
                logger.info(f"Cache hit for query [id={request_id}]")
            else:
                # Step 5: Extract conditions and generate query
                extracted_conditions = await nlp_processor.extract_conditions(request.text, collection)
                
                # Convert Dict[field, value] to List[Dict[field, operator, value]]
                query_conditions = []
                for field, value in extracted_conditions.items():
                    query_conditions.append({
                        "field": field,
                        "operator": "$eq",
                        "value": value
                    })
                
                query = query_generator.build_query(query_conditions)
                query = query_generator.sanitize_query(query)
                
                # Validate against schema
                is_valid, error = query_generator.validate_query(collection, query)
                if not is_valid:
                    return QueryResponse(
                        success=False,
                        query_id=None,
                        results=[],
                        total_count=0,
                        query_used=query,
                        from_cache=False,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        allow_export=False,
                        message=f"Query validation failed: {error}"
                    )
                
                # Save to cache
                await self._save_to_cache(request.text, collection, query)
            
            # Step 6: Execute query
            results, total_count = await data_repository.execute_query(
                collection, 
                query if query else {}, 
                limit=settings.DEFAULT_QUERY_LIMIT
            )
            
            # Ensure total_count is an integer
            if total_count is None:
                total_count = 0
            
            # Step 7: Format response
            execution_time = int((time.time() - start_time) * 1000)
            
            # Log query
            await self._log_query(
                request_id=request_id,
                query_text=request.text,
                collection=collection,
                query=query,
                result_count=len(results),
                total_count=total_count,
                from_cache=from_cache,
                execution_time=execution_time
            )
            query_hash = StoredQuery.create_hash(request.text, collection) if not from_cache else cached_query.get('query_hash')
            logger.info(f"Response - success: {True}, total_count: {total_count}, results_count: {len(results)}")
            return QueryResponse(
                success=True,
                query_id=query_hash,
                results=results,
                total_count=total_count,
                query_used=query,
                from_cache=from_cache,
                execution_time_ms=execution_time,
                allow_export=total_count > 1,
                message=f"Showing {len(results)} of {total_count} records" if total_count > len(results) else None
            )
            
        except TimeoutError as e:
            logger.error(f"Query timeout [id={request_id}]: {e}")
            return QueryResponse(
                success=False,
                query_id=None,
                results=[],
                total_count=0,
                query_used={},
                from_cache=False,
                execution_time_ms=int((time.time() - start_time) * 1000),
                allow_export=False,
                message=f"Query timed out after {settings.QUERY_TIMEOUT_SECONDS} seconds. Please try a simpler query."
            )
        except Exception as e:
            logger.error(f"Query processing failed [id={request_id}]: {e}", exc_info=True)
            return QueryResponse(
                success=False,
                query_id=None,
                results=[],
                total_count=0,
                query_used={},
                from_cache=False,
                execution_time_ms=int((time.time() - start_time) * 1000),
                allow_export=False,
                message=f"Failed to process query: {str(e)}"
            )
    
    async def _check_cache(self, text: str, collection: str) -> Optional[Dict[str, Any]]:
        """Check cache for similar query"""
        # Create cache key
        cache_key = StoredQuery.create_hash(text, collection)
    
        # Check in-memory cache first (safe access with .get())
        if cache_key in self.query_cache:
            self.cache_hits += 1
            logger.debug(f"Cache hit (memory): {cache_key}")
            return self.query_cache[cache_key]
    
        # Check database by exact hash
        try:
            stored = await query_repository.find_by_hash(cache_key)
            if stored:
                self.cache_hits += 1
                self.query_cache[cache_key] = stored.model_dump()
                logger.debug(f"Cache hit (database): {cache_key}")
                return stored.model_dump()
        except Exception as e:
            logger.warning(f"Database cache check failed: {e}")
    
        # Check similarity
        try:
            similar = await nlp_processor.find_similar_query(text, threshold=0.85)
            if similar:
                self.cache_hits += 1
                similar_hash = similar.get('query_hash')
                if similar_hash:
                    self.query_cache[similar_hash] = similar
                    logger.debug(f"Cache hit (similarity): {similar_hash}")
            return similar
        except Exception as e:
            logger.warning(f"Similarity check failed: {e}")
    
        self.cache_misses += 1
        return None
    
    async def _save_to_cache(self, text: str, collection: str, query: Dict[str, Any]) -> None:
        """Save new query to cache"""
        normalized = nlp_processor.normalize_text(text)
        query_hash = StoredQuery.create_hash(text, collection)
        
        stored = StoredQuery(
            original_text=text,
            normalized_text=normalized,
            generated_query=query,
            collection_name=collection,
            query_hash=query_hash,
            average_response_ms=0
        )
        
        await query_repository.save_query(stored)
        
        # Update in-memory cache
        self.query_cache[query_hash] = stored.model_dump()
    
    async def _log_query(
        self,
        request_id: str,
        query_text: str,
        collection: str,
        query: Dict[str, Any],
        result_count: int,
        total_count: int,
        from_cache: bool,
        execution_time: int
    ) -> None:
        """Log query to audit collection"""
        try:
            db = await data_repository.get_collection("query_logs")
            await db.insert_one({
                "request_id": request_id,
                "timestamp": time.time(),
                "query_text": query_text[:500],
                "collection": collection,
                "query": query,
                "result_count": result_count,
                "total_count": total_count,
                "from_cache": from_cache,
                "execution_time_ms": execution_time
            })
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
    
    async def get_query_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent query history"""
        stored = await query_repository.get_recent_queries(limit)
        return [q.model_dump() for q in stored]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        db_stats = await query_repository.get_query_stats()
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            **db_stats,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": hit_rate
        }


# Singleton instance
query_service = QueryService()