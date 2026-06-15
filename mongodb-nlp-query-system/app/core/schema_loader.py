"""
Load and manage JSON schemas for MongoDB collections
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class SchemaLoader:
    """Load and manage collection schemas from JSON files"""
    
    def __init__(self):
        self.schemas: Dict[str, dict] = {}
        self.schema_path = settings.SCHEMA_PATH
        self.observer: Optional[Observer] = None
    
    async def load_all_schemas(self) -> Dict[str, dict]:
        """Load all schema JSON files from the schema directory"""
        if not self.schema_path.exists():
            logger.warning(f"Schema path does not exist: {self.schema_path}")
            return {}
        
        for file_path in self.schema_path.glob("*_schema.json"):
            try:
                with open(file_path, 'r') as f:
                    schema = json.load(f)
                
                # Validate schema structure
                if self._validate_schema(schema):
                    collection_name = schema.get("collection_name")
                    if collection_name:
                        self.schemas[collection_name] = schema
                        logger.info(f"Loaded schema for collection: {collection_name}")
                    else:
                        logger.error(f"Schema missing collection_name: {file_path}")
                else:
                    logger.error(f"Invalid schema structure: {file_path}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from {file_path}: {e}")
            except Exception as e:
                logger.error(f"Failed to load schema {file_path}: {e}")
        
        return self.schemas
    
    def _validate_schema(self, schema: dict) -> bool:
        """Validate schema structure"""
        required_fields = ["collection_name", "fields"]
        
        for field in required_fields:
            if field not in schema:
                logger.error(f"Schema missing required field: {field}")
                return False
        
        # Validate fields structure
        for field in schema.get("fields", []):
            if "name" not in field or "type" not in field:
                logger.error(f"Field missing name or type: {field}")
                return False
        
        return True
    
    def get_schema(self, collection_name: str) -> Optional[dict]:
        """Get schema for a specific collection"""
        return self.schemas.get(collection_name)
    
    def get_all_collections(self) -> List[str]:
        """Get list of all collection names with schemas"""
        return list(self.schemas.keys())
    
    def validate_field(self, collection_name: str, field_name: str) -> bool:
        """Check if a field exists in the schema"""
        schema = self.get_schema(collection_name)
        if not schema:
            return False
        
        for field in schema.get("fields", []):
            if field["name"] == field_name:
                return True
        
        return False
    
    def get_field_type(self, collection_name: str, field_name: str) -> Optional[str]:
        """Get the type of a field"""
        schema = self.get_schema(collection_name)
        if not schema:
            return None
        
        for field in schema.get("fields", []):
            if field["name"] == field_name:
                return field.get("type")
        
        return None
    
    def get_searchable_fields(self, collection_name: str) -> List[str]:
        """Get list of fields that are marked as searchable"""
        schema = self.get_schema(collection_name)
        if not schema:
            return []
        
        searchable = []
        for field in schema.get("fields", []):
            if field.get("searchable", True):
                searchable.append(field["name"])
        
        return searchable
    
    async def reload_schemas(self) -> None:
        """Hot reload schemas without restarting"""
        logger.info("Reloading schemas...")
        self.schemas.clear()
        await self.load_all_schemas()
        logger.info(f"Reloaded {len(self.schemas)} schemas")
    
    def start_watching(self) -> None:
        """Start watching schema directory for changes"""
        if not self.schema_path.exists():
            return
        
        class SchemaFileHandler(FileSystemEventHandler):
            def __init__(self, loader):
                self.loader = loader
            
            def on_modified(self, event):
                if event.src_path.endswith("_schema.json"):
                    import asyncio
                    asyncio.create_task(self.loader.reload_schemas())
        
        event_handler = SchemaFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.schema_path), recursive=False)
        self.observer.start()
        logger.info(f"Started watching schema directory: {self.schema_path}")
    
    def stop_watching(self) -> None:
        """Stop watching schema directory"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped watching schema directory")


# Singleton instance
schema_loader = SchemaLoader()