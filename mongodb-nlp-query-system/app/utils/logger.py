"""
Logging configuration with JSON formatting and rotation
"""

import logging
import logging.config
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from logging.handlers import RotatingFileHandler

from app.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        """
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        
        if hasattr(record, "user_ip"):
            log_entry["user_ip"] = record.user_ip
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        
        return json.dumps(log_entry)


class PlainTextFormatter(logging.Formatter):
    """
    Plain text formatter for development
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as plain text
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Include request_id if present
        request_id = getattr(record, "request_id", "")
        request_part = f"[{request_id}] " if request_id else ""
        
        return f"{timestamp} - {record.levelname} - {record.name} - {request_part}{record.getMessage()}"


class RequestIdFilter(logging.Filter):
    """
    Add request ID to log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter that adds request_id attribute
        """
        if not hasattr(record, "request_id"):
            record.request_id = "N/A"
        return True


def setup_logging():
    """
    Setup logging configuration
    """
    # Create logs directory if it doesn't exist
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Select formatter based on configuration
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = PlainTextFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add request ID filter
    request_filter = RequestIdFilter()
    for handler in root_logger.handlers:
        handler.addFilter(request_filter)
    
    # Set specific log levels for third-party libraries
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with {settings.LOG_FORMAT} format")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Add extra context if needed
    logger.extra_context = {}
    
    # Add method to log with extra context
    def log_with_context(level, message, **kwargs):
        extra = getattr(logger, "extra_context", {}).copy()
        extra.update(kwargs)
        
        # Create record with extra fields
        record = logging.LogRecord(
            name=logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.extra = extra
        logger.handle(record)
    
    logger.log_with_context = log_with_context
    
    return logger


# Initialize logging on import
setup_logging()