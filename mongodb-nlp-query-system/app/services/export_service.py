"""
Export service for CSV and Excel file generation
"""

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Handle data export to CSV and Excel formats"""
    
    def __init__(self):
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
    
    async def export_to_csv(self, data: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Export data to CSV format
        
        Returns:
            Path to generated file
        """
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        file_path = self.export_dir / filename
        
        if not data:
            # Create empty CSV with headers only
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([])
            return str(file_path)
        
        # Flatten nested data
        flattened_data = [self._flatten_json(row) for row in data]
        
        # Get all unique columns
        columns = set()
        for row in flattened_data:
            columns.update(row.keys())
        columns = sorted(columns)
        
        # Write CSV
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(flattened_data)
        
        file_size = file_path.stat().st_size / (1024 * 1024)
        logger.info(f"Exported {len(data)} records to CSV: {filename} ({file_size:.2f} MB)")
        
        # Compress if too large
        if file_size > 10:
            zip_path = await self.compress_file(file_path)
            return zip_path
        
        return str(file_path)
    
    async def export_to_excel(self, data: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Export data to Excel format with formatting
        """
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        file_path = self.export_dir / filename
        
        if not data:
            # Create empty workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Query Results"
            wb.save(file_path)
            return str(file_path)
        
        # Flatten data
        flattened_data = [self._flatten_json(row) for row in data]
        df = pd.DataFrame(flattenated_data)
        
        # Write to Excel with openpyxl for better formatting
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Split into multiple sheets if needed (max 100k rows per sheet)
            rows_per_sheet = 100000
            if len(df) > rows_per_sheet:
                num_sheets = (len(df) + rows_per_sheet - 1) // rows_per_sheet
                for i in range(num_sheets):
                    start = i * rows_per_sheet
                    end = min((i + 1) * rows_per_sheet, len(df))
                    sheet_name = f"Part_{i+1}"
                    df.iloc[start:end].to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name="Query Results", index=False)
            
            # Apply formatting
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                
                # Header formatting
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal="center")
                
                # Auto-size columns
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        file_size = file_path.stat().st_size / (1024 * 1024)
        logger.info(f"Exported {len(data)} records to Excel: {filename} ({file_size:.2f} MB)")
        
        # Compress if too large
        if file_size > 10:
            zip_path = await self.compress_file(file_path)
            return zip_path
        
        return str(file_path)
    
    async def compress_file(self, file_path: Path) -> str:
        """Compress file to ZIP archive"""
        zip_path = file_path.with_suffix('.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, file_path.name)
        
        # Remove original file
        file_path.unlink()
        
        logger.info(f"Compressed to: {zip_path.name}")
        return str(zip_path)
    
    def _flatten_json(self, data: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """
        Flatten nested JSON objects for CSV/Excel export
        
        Example: {"user": {"name": "John"}} -> {"user_name": "John"}
        """
        flattened = {}
        
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            if isinstance(value, dict):
                flattened.update(self._flatten_json(value, new_key, sep=sep))
            elif isinstance(value, list):
                # Convert list to JSON string
                flattened[new_key] = json.dumps(value)
            elif isinstance(value, datetime):
                flattened[new_key] = value.isoformat()
            else:
                flattened[new_key] = value
        
        return flattened
    
    async def get_file(self, filename: str) -> Optional[Path]:
        """Get file path by filename"""
        file_path = self.export_dir / filename
        if file_path.exists():
            return file_path
        return None
    
    async def delete_file(self, filename: str) -> bool:
        """Delete an export file"""
        file_path = self.export_dir / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {filename}")
            return True
        return False
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Delete files older than max_age_hours"""
        import time
        deleted_count = 0
        current_time = time.time()
        
        for file_path in self.export_dir.iterdir():
            if file_path.is_file():
                file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
                if file_age_hours > max_age_hours:
                    file_path.unlink()
                    deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old files")
        return deleted_count


# Singleton instance
export_service = ExportService()