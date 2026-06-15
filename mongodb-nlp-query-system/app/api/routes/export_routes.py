"""
Export API endpoints
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
import uuid

from app.services.export_service import export_service
from app.services.email_service import email_service
from app.database.query_repository import query_repository
from app.config import settings
import logging

logger = logging.getLogger(__name__)

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
    Export query results to CSV and download
    """
    try:
        # Generate CSV file
        file_path = await export_service.export_query_to_csv(query_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="No data to export or query not found")
        
        # Extract filename from path
        import os
        filename = os.path.basename(file_path)
        
        # Schedule cleanup after 1 hour
        background_tasks.add_task(
            export_service.delete_file,
            filename
        )
        
        # Determine media type
        if file_path.endswith('.zip'):
            media_type = 'application/zip'
            download_name = filename.replace('.csv.zip', '.csv.zip')
        else:
            media_type = 'text/csv'
            download_name = filename
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=download_name
        )
        
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/excel/{query_id}")
async def export_excel(
    query_id: str,
    background_tasks: BackgroundTasks
):
    """
    Export query results to Excel and download
    """
    try:
        # Generate Excel file
        file_path = await export_service.export_query_to_excel(query_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="No data to export or query not found")
        
        # Extract filename from path
        import os
        filename = os.path.basename(file_path)
        
        # Schedule cleanup after 1 hour
        background_tasks.add_task(
            export_service.delete_file,
            filename
        )
        
        # Determine media type
        if file_path.endswith('.zip'):
            media_type = 'application/zip'
            download_name = filename.replace('.xlsx.zip', '.xlsx.zip')
        else:
            media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = filename
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=download_name
        )
        
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email")
async def export_to_email(
    request: EmailExportRequest,
    background_tasks: BackgroundTasks
):
    """
    Send export to email
    """
    try:
        # Validate email
        if not email_service.validate_email(request.email):
            raise HTTPException(status_code=400, detail="Invalid email address")
        
        # Generate file based on format
        if request.format == "csv":
            file_path = await export_service.export_query_to_csv(request.query_id)
        else:
            file_path = await export_service.export_query_to_excel(request.query_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="No data to export or query not found")
        
        # Get query info for email
        stored_query = await query_repository.find_by_hash(request.query_id)
        
        query_info = {
            "original_text": stored_query.original_text if stored_query else "Query Export",
            "total_count": 0,  # Would need to execute query to get count
            "collection": stored_query.collection_name if stored_query else "Unknown",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Send email with attachment
        background_tasks.add_task(
            email_service.send_export_email,
            request.email,
            file_path,
            query_info
        )
        
        # Schedule cleanup
        import os
        background_tasks.add_task(
            export_service.delete_file,
            os.path.basename(file_path)
        )
        
        return {
            "success": True,
            "message": f"Export is being sent to {request.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_export_status(job_id: str):
    """
    Check export job status (for async exports)
    """
    # This would be implemented with a job queue system
    return {
        "success": True,
        "job_id": job_id,
        "status": "completed",
        "message": "Export ready"
    }