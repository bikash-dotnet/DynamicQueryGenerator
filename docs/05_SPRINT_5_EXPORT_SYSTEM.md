# Sprint 5: Export System & Email (5 Days)

## Goal
Implement CSV/Excel export with email delivery and download options

## High-Level Tasks

### Task 5.1: Export Service Core (8 hours)
- Implement CSV generator with streaming support
- Implement Excel generator with formatting
- Add nested JSON flattening
- Add file compression for large exports (ZIP)
- Implement auto-cleanup (24 hours)

### Task 5.2: CSV Export (4 hours)
- Generate RFC 4180 compliant CSV
- Handle special characters (quotes, commas)
- Support UTF-8 encoding with BOM
- Stream large datasets to disk
- Add configurable delimiter

### Task 5.3: Excel Export (5 hours)
- Generate Excel with openpyxl
- Add auto-filter on headers
- Auto-size column widths
- Freeze header row
- Split large datasets into multiple sheets
- Add formatting (bold headers, alternating rows)

### Task 5.4: Email Integration (6 hours)
- Implement SMTP email sender
- Add SendGrid support (optional)
- Create HTML email templates
- Implement retry logic (3 attempts)
- Add email validation (format + MX)
- Rate limit emails (10/hour per user)

### Task 5.5: Export API Endpoints (5 hours)
- `POST /export/csv` - Download CSV
- `POST /export/excel` - Download Excel
- `POST /export/email` - Send to email
- `GET /export/status/{job_id}` - Check progress
- Implement async export for large datasets

### Task 5.6: File Management (4 hours)
- Create file manager with unique IDs
- Implement secure storage (outside web root)
- Add signed URLs for access
- Auto-delete files after 24 hours
- Monitor disk usage (alert at 80%)

### Task 5.7: Email Queue (3 hours)
- Implement database-backed queue
- Add background worker for processing
- Track delivery status
- Add dead letter queue for failures

### Task 5.8: Frontend Export UI (5 hours)
- Add export buttons (CSV/Excel) to results
- Add email input field with validation
- Implement progress indicator
- Add success/error notifications
- Implement download via blob

### Task 5.9: Testing (4 hours)
- Test CSV with 100k records
- Test Excel with large datasets
- Test email delivery with attachments
- Test concurrent exports (10 simultaneous)

## Deliverables
- [ ] CSV/Excel export functionality
- [ ] Email delivery system
- [ ] Async export for large datasets
- [ ] File management with auto-cleanup
- [ ] Export UI components

## Acceptance Criteria
- [ ] Exports only when results > 1 record
- [ ] CSV/Excel files open correctly
- [ ] Emails delivered with attachments
- [ ] Files auto-deleted after 24 hours
- [ ] Rate limiting prevents abuse

## Dependencies
- Sprint 3 (API and database)
- Sprint 4 (safety validations)

## Risks
| Risk | Mitigation |
|------|------------|
| Large exports cause memory issues | Streaming, async processing, chunking |
| Email marked as spam | SPF/DKIM, plain text + HTML versions |
| Disk fills with exports | Auto-cleanup, disk monitoring, alerts |