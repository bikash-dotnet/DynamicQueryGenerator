"""
Query processing API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any

from app.models.user_request import UserQueryRequest, QueryResponse
from app.services.query_service import query_service
from app.core.schema_loader import schema_loader
from app.config import settings

router = APIRouter(prefix="/api/v1/query", tags=["queries"])


async def verify_api_key(request: Request):
    """Verify API key if authentication is enabled"""
    if settings.ENABLE_API_KEY_AUTH:
        api_key = request.headers.get("X-API-Key") if request.headers else None
        if not api_key or api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/process", response_model=QueryResponse)
async def process_query(
    request: UserQueryRequest,
    _: None = Depends(verify_api_key)
):
    """
    Process natural language query and return results
    """
    return await query_service.process_query(request)


@router.get("/history")
async def get_query_history(
    limit: int = 10,
    _: None = Depends(verify_api_key)
):
    """
    Get recent query history
    """
    if limit > 100:
        limit = 100
    
    history = await query_service.get_query_history(limit)
    return {"success": True, "history": history}


@router.get("/stats")
async def get_query_stats(_: None = Depends(verify_api_key)):
    """
    Get query system statistics
    """
    stats = await query_service.get_stats()
    return {"success": True, "stats": stats}


@router.get("/collections")
async def get_collections(_: None = Depends(verify_api_key)):
    """
    List all available collections with schemas
    """
    collections = schema_loader.get_all_collections()
    
    result = []
    for collection in collections:
        schema = schema_loader.get_schema(collection)
        result.append({
            "name": collection,
            "fields": [{
                "name": f["name"],
                "type": f["type"],
                "searchable": f.get("searchable", True),
                "description": f.get("description", "")
            } for f in schema.get("fields", [])]
        } if schema else {"name": collection, "fields": []})
    
    return {"success": True, "collections": result}


@router.get("/explain/{collection}")
async def explain_query(
    collection: str,
    field: str | None = None,
    value: str | None = None,
    _: None = Depends(verify_api_key)
):
    """
    Explain how queries are processed (for debugging)
    """
    if not schema_loader.get_schema(collection):
        raise HTTPException(status_code=404, detail=f"Collection '{collection}' not found")
    
    # This would return query explanation from MongoDB
    return {
        "success": True,
        "message": "Query explanation endpoint. Send POST to /process with your query.",
        "collection": collection,
        "available_fields": schema_loader.get_searchable_fields(collection)
    }