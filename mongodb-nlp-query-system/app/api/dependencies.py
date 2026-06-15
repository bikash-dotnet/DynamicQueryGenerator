"""
API dependencies for authentication, rate limiting, and request validation
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import hashlib
import hmac
from datetime import datetime, timedelta

from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Security scheme for API key authentication
security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    Verify API key from Authorization header
    
    Returns:
        API key if valid, raises 401 otherwise
    """
    if not settings.ENABLE_API_KEY_AUTH:
        return "disabled"
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    api_key = credentials.credentials
    
    if not settings.API_KEY or not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.info(f"API key authenticated successfully")
    return api_key


async def verify_admin_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    Verify admin API key (separate from regular API key)
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing admin API key")
    
    admin_key = credentials.credentials
    expected_admin_key = getattr(settings, "ADMIN_API_KEY", None)
    
    if not expected_admin_key or not hmac.compare_digest(admin_key, expected_admin_key):
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    
    return admin_key


class RateLimiter:
    """
    Rate limiting dependency
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # {ip: [timestamps]}
    
    async def __call__(self, request: Request) -> bool:
        """
        Check if request is within rate limit
        
        Returns:
            True if within limit, raises 429 otherwise
        """
        if not settings.ENABLE_RATE_LIMITING:
            return True
        
        client_ip = request.client.host
        now = datetime.now()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if (now - ts).seconds < 60
            ]
        else:
            self.requests[client_ip] = []
        
        # Check limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            retry_after = 60 - (now - self.requests[client_ip][-1]).seconds
            raise HTTPException(
                status_code=429,
                headers={"Retry-After": str(max(1, retry_after))},
                detail=f"Rate limit exceeded. Limit: {self.requests_per_minute} requests per minute"
            )
        
        # Add current request
        self.requests[client_ip].append(now)
        return True


class RequestValidator:
    """
    Request validation dependency
    """
    
    async def __call__(self, request: Request) -> Request:
        """
        Validate request before processing
        """
        # Check content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type:
                raise HTTPException(
                    status_code=415,
                    detail="Content-Type must be application/json"
                )
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                max_size = 10 * 1024 * 1024  # 10MB
                if length > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request too large. Max size: {max_size // (1024*1024)}MB"
                    )
            except ValueError:
                pass
        
        return request


# Create instances
rate_limiter = RateLimiter(settings.RATE_LIMIT_PER_MINUTE)
request_validator = RequestValidator()


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state
    """
    return getattr(request.state, "request_id", "unknown")