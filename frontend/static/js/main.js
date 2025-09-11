// Global utility functions
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');

    // Set message
    toastBody.textContent = message;

    // Set toast type
    toast.className = `toast ${type === 'success' ? 'bg-success text-white' :
                              type === 'error' ? 'bg-danger text-white' :
                              type === 'warning' ? 'bg-warning text-dark' :
                              'bg-info text-white'}`;

    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function formatDate(dateString) {
    if (!dateString) return 'Never';

    const date = new Date(dateString);

    // Format for Egypt timezone display
    return date.toLocaleString('en-US', {
        timeZone: 'Africa/Cairo',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }) + ' (Egypt)';
}

function showLoading(element) {
    element.classList.add('loading');
}

function hideLoading(element) {
    element.classList.remove('loading');
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('Simple Email Tracker loaded');
});