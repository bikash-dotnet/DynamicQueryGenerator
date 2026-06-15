"""
FastAPI application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import time
import uuid
import logging

from app.config import settings, validate_config
from app.database.mongodb_client import mongodb_client
from app.core.schema_loader import schema_loader
from app.api.routes import query_router, export_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting application...")
    
    # Validate configuration
    try:
        validate_config()
        logger.info("Configuration validated")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    # Connect to MongoDB
    await mongodb_client.connect()
    logger.info("MongoDB connected")
    
    # Load schemas
    await schema_loader.load_all_schemas()
    schema_loader.start_watching()
    logger.info(f"Loaded {len(schema_loader.schemas)} schemas")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    schema_loader.stop_watching()
    await mongodb_client.disconnect()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MongoDB NLP Query System",
    description="Natural language query interface for MongoDB",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    # Log request
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = (time.time() - start_time) * 1000
    logger.info(f"Response {request_id}: {response.status_code} ({process_time:.2f}ms)")
    
    # Add custom headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-MS"] = str(int(process_time))
    
    return response


# Rate limiting middleware (simplified)
if settings.ENABLE_RATE_LIMITING:
    from collections import defaultdict
    from datetime import datetime
    
    request_counts = defaultdict(list)
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Simple rate limiting middleware"""
        client_ip = request.client.host
        now = datetime.now()
        
        # Clean old requests
        request_counts[client_ip] = [
            req_time for req_time in request_counts[client_ip]
            if (now - req_time).seconds < 60
        ]
        
        # Check limit
        if len(request_counts[client_ip]) >= settings.RATE_LIMIT_PER_IP:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {settings.RATE_LIMIT_PER_IP} per minute",
                    "retry_after": 60
                }
            )
        
        request_counts[client_ip].append(now)
        return await call_next(request)


# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Include routers
app.include_router(query_router)
app.include_router(export_router)


# Root endpoint - serve UI
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main UI"""
    return templates.TemplateResponse("index.html", {"request": request})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_health = await mongodb_client.health_check()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "timestamp": time.time(),
        "database": db_health,
        "schemas_loaded": len(schema_loader.schemas),
        "version": "1.0.0"
    }


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint (simplified)"""
    from app.services.query_service import query_service
    stats = await query_service.get_stats()
    
    return {
        "total_queries": stats.get("total_queries", 0),
        "cache_hit_rate": stats.get("cache_hit_rate", 0),
        "cache_size": stats.get("cache_size", 0)
    }