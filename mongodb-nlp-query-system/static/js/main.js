// Global variables
let currentQueryId = null;
let currentResults = null;
let currentTotalCount = 0;
let currentPage = 1;
const pageSize = 5;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadCollections();
    loadHistory();
    
    // Ctrl+Enter to submit
    document.getElementById('queryInput').addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            submitQuery();
        }
    });
});

// Show toast notification
function showToast(message, type = 'success') {
    const container = document.querySelector('.toast-container');
    const toastId = 'toast-' + Date.now();
    
    const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-info');
    const icon = type === 'success' ? 'check-circle' : (type === 'error' ? 'exclamation-triangle' : 'info-circle');
    
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="true" data-bs-delay="5000">
            <div class="toast-header ${bgClass} text-white">
                <i class="bi bi-${icon} me-2"></i>
                <strong class="me-auto">${type.toUpperCase()}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove after hide
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Load available collections
async function loadCollections() {
    try {
        const response = await fetch('/api/v1/query/collections');
        const data = await response.json();
        
        if (data.success && data.collections) {
            const select = document.getElementById('collectionSelect');
            data.collections.forEach(collection => {
                const option = document.createElement('option');
                option.value = collection.name;
                option.textContent = collection.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load collections:', error);
    }
}

// Load query history
async function loadHistory() {
    try {
        const response = await fetch('/api/v1/query/history?limit=10');
        const data = await response.json();
        
        const historyDiv = document.getElementById('queryHistory');
        
        if (data.success && data.history && data.history.length > 0) {
            historyDiv.innerHTML = '';
            data.history.forEach(query => {
                const div = document.createElement('div');
                div.className = 'list-group-item list-group-item-action cursor-pointer';
                div.onclick = () => useExample(query.original_text);
                div.innerHTML = `
                    <div class="d-flex justify-content-between">
                        <small class="text-truncate">${escapeHtml(query.original_text)}</small>
                        <small class="text-muted">${formatDate(query.last_used)}</small>
                    </div>
                    <div class="text-muted small">
                        Used ${query.usage_count || 1} times
                    </div>
                `;
                historyDiv.appendChild(div);
            });
        } else {
            historyDiv.innerHTML = '<div class="list-group-item text-muted">No recent queries</div>';
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// Submit query
async function submitQuery() {
    const queryText = document.getElementById('queryInput').value.trim();
    const collection = document.getElementById('collectionSelect').value;
    
    if (!queryText) {
        showToast('Please enter a query', 'warning');
        return;
    }
    
    // Show loading
    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    
    try {
        const response = await fetch('/api/v1/query/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: queryText,
                collection: collection || null
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentQueryId = data.query_id;
            currentResults = data.results;
            currentTotalCount = data.total_count;
            currentPage = 1;
            
            displayResults(data);
            showToast(`Found ${data.total_count} records. Showing ${data.results.length}`, 'success');
            loadHistory(); // Refresh history
        } else {
            showToast(data.message || 'Query failed', 'error');
        }
    } catch (error) {
        showToast('Network error. Please try again.', 'error');
        console.error('Query error:', error);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Display results
function displayResults(data) {
    const resultsDiv = document.getElementById('resultsSection');
    
    if (!data.results || data.results.length === 0) {
        resultsDiv.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i>
                No results found. Try a different query.
            </div>
        `;
        resultsDiv.style.display = 'block';
        return;
    }
    
    // Get columns from first result
    const columns = Object.keys(data.results[0]);
    
    // Build table HTML
    let tableHtml = `
        <div class="card shadow-sm">
            <div class="card-header bg-success text-white">
                <i class="bi bi-table"></i>
                Results (${data.results.length} of ${data.totalCount})
                ${data.from_cache ? '<span class="badge bg-light text-dark ms-2"><i class="bi bi-database-check"></i> From Cache</span>' : ''}
            </div>
            <div class="card-body">
                <div class="table-responsive result-table">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                ${columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${data.results.map(row => `
                                <tr>
                                    ${columns.map(col => `
                                        <td>
                                            ${formatCellValue(row[col])}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                
                ${data.totalCount > data.results.length ? `
                    <nav>
                        <ul class="pagination justify-content-center">
                            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                                <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Previous</a>
                            </li>
                            <li class="page-item active"><span class="page-link">${currentPage}</span></li>
                            <li class="page-item ${currentPage * pageSize >= data.totalCount ? 'disabled' : ''}">
                                <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next</a>
                            </li>
                        </ul>
                    </nav>
                ` : ''}
                
                ${data.allowExport ? `
                    <div class="alert alert-info mt-3">
                        <i class="bi bi-download"></i>
                        Export all ${data.totalCount} records:
                        <button class="btn btn-sm btn-success" onclick="exportCSV()">
                            <i class="bi bi-filetype-csv"></i> CSV
                        </button>
                        <button class="btn btn-sm btn-success" onclick="exportExcel()">
                            <i class="bi bi-filetype-xlsx"></i> Excel
                        </button>
                        <div class="mt-2">
                            <input type="email" id="exportEmail" class="form-control form-control-sm d-inline-block w-auto" placeholder="Email address">
                            <button class="btn btn-sm btn-info" onclick="sendToEmail('csv')">
                                Send CSV
                            </button>
                            <button class="btn btn-sm btn-info" onclick="sendToEmail('excel')">
                                Send Excel
                            </button>
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    resultsDiv.innerHTML = tableHtml;
    resultsDiv.style.display = 'block';
}

// Format cell value for display
function formatCellValue(value) {
    if (value === null || value === undefined) {
        return '<span class="text-muted">NULL</span>';
    }
    
    if (typeof value === 'boolean') {
        return value ? '<i class="bi bi-check-lg text-success"></i>' : '<i class="bi bi-x-lg text-danger"></i>';
    }
    
    if (typeof value === 'object') {
        return `<pre class="mb-0 small">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }
    
    if (typeof value === 'string' && value.length > 100) {
        return escapeHtml(value.substring(0, 100)) + '...';
    }
    
    return escapeHtml(String(value));
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${Math.floor(diffHours)} hours ago`;
    return `${Math.floor(diffHours / 24)} days ago`;
}

// Clear query input
function clearQuery() {
    document.getElementById('queryInput').value = '';
    document.getElementById('resultsSection').style.display = 'none';
}

// Use example query
function useExample(query) {
    document.getElementById('queryInput').value = query;
    submitQuery();
}

// Show help modal
function showHelp() {
    const modal = new bootstrap.Modal(document.getElementById('helpModal'));
    modal.show();
}

// Change page
function changePage(page) {
    currentPage = page;
    // In production, re-fetch with pagination
    submitQuery();
}

// Export functions
async function exportCSV() {
    if (!currentQueryId) {
        showToast('No query results to export', 'warning');
        return;
    }
    
    showToast('Preparing CSV export...', 'info');
    
    try {
        const response = await fetch(`/api/v1/export/csv/${currentQueryId}`, {
            method: 'POST'
        });
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `export_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        
        showToast('CSV export downloaded', 'success');
    } catch (error) {
        showToast('Export failed', 'error');
        console.error('Export error:', error);
    }
}

async function exportExcel() {
    if (!currentQueryId) {
        showToast('No query results to export', 'warning');
        return;
    }
    
    showToast('Preparing Excel export...', 'info');
    
    try {
        const response = await fetch(`/api/v1/export/excel/${currentQueryId}`, {
            method: 'POST'
        });
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `export_${Date.now()}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
        
        showToast('Excel export downloaded', 'success');
    } catch (error) {
        showToast('Export failed', 'error');
        console.error('Export error:', error);
    }
}

async function sendToEmail(format) {
    const email = document.getElementById('exportEmail')?.value;
    
    if (!email) {
        showToast('Please enter an email address', 'warning');
        return;
    }
    
    if (!currentQueryId) {
        showToast('No query results to export', 'warning');
        return;
    }
    
    showToast(`Sending ${format.toUpperCase()} to ${email}...`, 'info');
    
    try {
        const response = await fetch('/api/v1/export/email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query_id: currentQueryId,
                email: email,
                format: format
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`Export sent to ${email}`, 'success');
        } else {
            showToast(data.message || 'Failed to send email', 'error');
        }
    } catch (error) {
        showToast('Failed to send email', 'error');
        console.error('Email error:', error);
    }
}