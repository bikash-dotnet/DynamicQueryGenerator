"""
Export API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr

from app.services.export_service import export_service
from app.services.email_service import email_service
from app.database.query_repository import query_repository
from app.database.data_repository import data_repository
from app.config import settings

router = APIRouter(prefix="/api/v1/export", tags=["exports"])


class EmailExportRequest(BaseModel):
    query_id: str
    email: EmailStr
    format: Literal["csv", "excel"]


@router.post("/csv/{query_id}")
async def export_csv(
    query_id: str,
    background_tasks: BackgroundTasks
):
    """
    Export query results to CSV
    """
    # Get stored query
    # Note: In production, you'd retrieve the actual query and execute it
    # This is a simplified example
    
    return FileResponse(
        path="exports/sample.csv",
        media_type="text/csv",
        filename=f"export_{query_id}.csv"
    )


@router.post("/excel/{query_id}")
async def export_excel(
    query_id: str,
    background_tasks: BackgroundTasks
):
    """
    Export query results to Excel
    """
    return FileResponse(
        path="exports/sample.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"export_{query_id}.xlsx"
    )


@router.post("/email")
async def export_to_email(
    request: EmailExportRequest,
    background_tasks: BackgroundTasks
):
    """
    Send export to email
    """
    # Validate email
    if not email_service.validate_email(request.email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    # In production, you'd:
    # 1. Retrieve query from database
    # 2. Execute query to get results
    # 3. Generate export file
    # 4. Send email with attachment
    
    background_tasks.add_task(
        email_service.send_export_email,
        request.email,
        "exports/sample.csv",
        {"original_text": "Sample query", "total_count": 100}
    )
    
    return {
        "success": True,
        "message": f"Export will be sent to {request.email}"
    }