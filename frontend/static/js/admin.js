// Admin page functionality
let currentPage = 1;
let currentSearch = '';
let totalPages = 1;

// Initialize admin page
document.addEventListener('DOMContentLoaded', function () {
    loadTrackingData();
    setupEventListeners();
});

function setupEventListeners() {
    // Search input enter key
    document.getElementById('searchInput').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            searchTracking();
        }
    });
}

// Load tracking data
async function loadTrackingData(page = 1, search = '') {
    const tableBody = document.getElementById('trackingTableBody');

    // Show loading
    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </td>
        </tr>
    `;

    try {
        const params = new URLSearchParams({
            page: page.toString(),
            ...(search && { search })
        });

        const data = await apiRequest(`/api/tracking?${params}`);

        if (data.success) {
            currentPage = data.current_page;
            totalPages = data.pages;
            currentSearch = search;

            renderTrackingTable(data.data);
            renderPagination(data);
        } else {
            throw new Error(data.message || 'Failed to load tracking data');
        }

    } catch (error) {
        console.error('Failed to load tracking data:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger py-4">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load data: ${error.message}
                </td>
            </tr>
        `;
    }
}

function renderTrackingTable(data) {
    const tableBody = document.getElementById('trackingTableBody');

    if (data.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <i class="fas fa-inbox me-2"></i>
                    No tracking data found
                </td>
            </tr>
        `;
        return;
    }

    let html = '';

    data.forEach(item => {
        const openStatus = item.open_count > 0 ? 'opened' : 'not-opened';
        const statusClass = item.open_count > 0 ? 'bg-success' : 'bg-secondary';

        const clickStatusClass = item.click_count > 0 ? 'bg-primary' : 'bg-secondary';

        html += `
            <tr class="fade-in">
                <td>
                    <div class="d-flex flex-column">
                        <span class="fw-medium text-primary" style="cursor: pointer;" onclick="showTrackingDetails('${item.tracking_id}', '${escapeHtml(item.recipient_email)}')">
                            ${escapeHtml(item.recipient_email)}
                        </span>
                        ${item.subject ? `<small class="text-muted">${escapeHtml(item.subject)}</small>` : ''}
                    </div>
                </td>
                <td>
                    <span class="tracking-id" title="Click to copy" onclick="copyToClipboard('${item.tracking_id}')">
                        ${item.tracking_id.substring(0, 8)}...
                    </span>
                </td>
                <td>
                    <span class="badge ${statusClass} status-badge">
                        ${item.open_count} ${item.open_count === 1 ? 'open' : 'opens'}
                    </span>
                </td>
                <td>
                    <span class="badge ${clickStatusClass} status-badge">
                        ${item.click_count || 0} ${(item.click_count || 0) === 1 ? 'click' : 'clicks'}
                    </span>
                </td>
                <td>
                    <span class="${item.last_open_time ? 'text-success' : 'text-muted'}">
                        ${formatDate(item.last_open_time)}
                    </span>
                </td>
                <td>
                    <span class="font-monospace text-primary">
                        ${item.last_ip || '-'}
                    </span>
                </td>
                <td>
                    <span class="font-monospace text-info">
                        ${item.last_port || '-'}
                    </span>
                </td>
                <td>
                    <small class="text-muted">
                        ${formatDate(item.created_at)}
                    </small>
                </td>
            </tr>
        `;
    });

    tableBody.innerHTML = html;
}
// Clear database functions
function confirmClearDatabase() {
    const modal = new bootstrap.Modal(document.getElementById('clearDatabaseModal'));

    // Reset form
    document.getElementById('confirmDeleteInput').value = '';
    document.getElementById('confirmDeleteBtn').disabled = true;

    // Add input listener
    const input = document.getElementById('confirmDeleteInput');
    input.addEventListener('input', function () {
        const btn = document.getElementById('confirmDeleteBtn');
        btn.disabled = this.value !== 'DELETE ALL';
    });

    modal.show();
}

async function clearDatabase() {
    const confirmInput = document.getElementById('confirmDeleteInput').value;
    const btn = document.getElementById('confirmDeleteBtn');
    const originalText = btn.innerHTML;

    if (confirmInput !== 'DELETE ALL') {
        showToast('Please type "DELETE ALL" to confirm', 'error');
        return;
    }

    // Show loading
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
    btn.disabled = true;

    try {
        const data = await apiRequest('/api/admin/clear-database', {
            method: 'POST',
            body: JSON.stringify({
                confirmation: confirmInput
            })
        });

        if (data.success) {
            // Hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('clearDatabaseModal'));
            modal.hide();

            // Refresh data
            loadTrackingData(1, '');

            showToast('All tracking data has been deleted', 'success');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        showToast(`Failed to clear database: ${error.message}`, 'error');
    } finally {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}


// Show tracking details modal
async function showTrackingDetails(trackingId, email) {
    const modal = new bootstrap.Modal(document.getElementById('trackingDetailsModal'));
    const content = document.getElementById('trackingDetailsContent');

    // Show loading
    content.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-2">Loading tracking details...</div>
        </div>
    `;

    modal.show();

    try {
        const data = await apiRequest(`/api/tracking/${trackingId}/details`);

        if (data.success) {
            renderTrackingDetails(data.tracking, data.opens, email);
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        content.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load tracking details: ${error.message}
            </div>
        `;
    }
}



function renderTrackingDetails(tracking, opens, email) {
    const content = document.getElementById('trackingDetailsContent');

    let html = `
        <div class="mb-4">
            <h6><i class="fas fa-envelope me-2"></i>Email Information</h6>
            <div class="row">
                <div class="col-md-6">
                    <strong>Email:</strong> ${escapeHtml(email)}<br>
                    <strong>Tracking ID:</strong> <span class="tracking-id">${tracking.tracking_id}</span><br>
                    <strong>Total Opens:</strong> <span class="badge bg-success">${tracking.open_count}</span><br>
                    <strong>Total Clicks:</strong> <span class="badge bg-primary">${tracking.click_count || 0}</span>
                </div>
                <div class="col-md-6">
                    <strong>Created:</strong> ${formatDate(tracking.created_at)}<br>
                    <strong>Subject:</strong> ${tracking.subject ? escapeHtml(tracking.subject) : 'No subject'}<br>
                    <strong>Last Open:</strong> ${formatDate(tracking.last_open_time)}<br>
                    <strong>Last Click:</strong> ${formatDate(tracking.last_click_time)}
                </div>
            </div>
        </div>
    `;

    // Show opens and clicks sections
    if (opens.length === 0 && (!tracking.click_count || tracking.click_count === 0)) {
        html += `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                This email has not been opened or clicked yet.
            </div>
        `;
    } else {
        // Opens section
        if (opens.length > 0) {
            html += `
                <h6><i class="fas fa-eye me-2"></i>Open History (${opens.length} events)</h6>
                <div class="table-responsive mb-4">
                    <table class="table table-striped table-sm">
                        <thead>
                            <tr>
                                <th>Open Time</th>
                                <th>IP Address</th>
                                <th>Port</th>
                                <th>Time Ago</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            opens.forEach((open, index) => {
                const timeAgo = getTimeAgo(open.open_time);
                const isLatest = index === 0;

                html += `
                    <tr class="${isLatest ? 'table-success' : ''}">
                        <td>
                            ${formatDate(open.open_time)}
                            ${isLatest ? '<span class="badge bg-success ms-2">Latest</span>' : ''}
                        </td>
                        <td>
                            <span class="font-monospace text-primary">${open.ip}</span>
                        </td>
                        <td>
                            <span class="font-monospace text-info">${open.port}</span>
                        </td>
                        <td>
                            <small class="text-muted">${timeAgo}</small>
                        </td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }

        // Clicks section (you'll need to modify the API call to include clicks)
        // For now, just show a placeholder
        html += `
            <h6><i class="fas fa-mouse-pointer me-2"></i>Click History (${tracking.click_count || 0} events)</h6>
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Click events will be shown here when available.
            </div>
        `;
    }

    content.innerHTML = html;
}


function getTimeAgo(dateString) {
    const now = new Date();
    const date = new Date(dateString);

    // Debug logging
    console.log('Current time:', now.toISOString());
    console.log('Event time:', date.toISOString());
    console.log('Raw date string:', dateString);

    const diffInMs = now.getTime() - date.getTime();
    const diffInSeconds = Math.floor(diffInMs / 1000);

    console.log('Difference in seconds:', diffInSeconds);

    if (diffInSeconds < 0) {
        return 'In the future';
    }

    if (diffInSeconds < 60) return `${diffInSeconds} seconds ago`;
    if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
    }
    if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
    }

    const days = Math.floor(diffInSeconds / 86400);
    return `${days} ${days === 1 ? 'day' : 'days'} ago`;
}
function renderPagination(data) {
    const pagination = document.getElementById('pagination');

    if (data.pages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';

    // Previous button
    html += `
        <li class="page-item ${data.current_page === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${data.current_page - 1})"
               aria-label="Previous">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>
    `;

    // Page numbers
    const startPage = Math.max(1, data.current_page - 2);
    const endPage = Math.min(data.pages, data.current_page + 2);

    if (startPage > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="goToPage(1)">1</a></li>`;
        if (startPage > 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === data.current_page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="goToPage(${i})">${i}</a>
            </li>
        `;
    }

    if (endPage < data.pages) {
        if (endPage < data.pages - 1) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        html += `<li class="page-item"><a class="page-link" href="#" onclick="goToPage(${data.pages})">${data.pages}</a></li>`;
    }

    // Next button
    html += `
        <li class="page-item ${data.current_page === data.pages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${data.current_page + 1})"
               aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;

    pagination.innerHTML = html;
}

// Navigation functions
function goToPage(page) {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
        loadTrackingData(page, currentSearch);
    }
}

function searchTracking() {
    const searchValue = document.getElementById('searchInput').value.trim();
    loadTrackingData(1, searchValue);
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    loadTrackingData(1, '');
}

function refreshData() {
    loadTrackingData(currentPage, currentSearch);
    showToast('Data refreshed successfully!', 'success');
}

// Utility functions
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Tracking ID copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy tracking ID', 'error');
    });
}

// Auto-refresh every 30 seconds
setInterval(() => {
    loadTrackingData(currentPage, currentSearch);
}, 30000);