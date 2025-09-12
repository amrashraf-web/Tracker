// Dashboard specific functionality
let smtpConfig = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    loadSMTPConfig();
    setupEventListeners();
});

function setupEventListeners() {
    // SMTP Form submission
    document.getElementById('smtpForm').addEventListener('submit', handleSMTPSubmit);

    // Email Form submission
    document.getElementById('emailForm').addEventListener('submit', handleEmailSubmit);

    // Add image upload listener
    document.getElementById('imageUpload').addEventListener('change', handleImageUpload);
}

async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file size
    if (file.size > 5 * 1024 * 1024) {
        showToast('File too large. Maximum size: 5MB', 'error');
        e.target.value = '';
        return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
        const preview = document.getElementById('imagePreview');
        const container = document.getElementById('imagePreviewContainer');

        preview.src = e.target.result;
        container.style.display = 'block';
    };
    reader.readAsDataURL(file);

    // Upload to server
    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch('/api/upload-image', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            uploadedImageUrl = data.url;
            showToast('Image uploaded successfully!', 'success');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        showToast(`Upload failed: ${error.message}`, 'error');
        e.target.value = '';
        document.getElementById('imagePreviewContainer').style.display = 'none';
        uploadedImageUrl = null;
    }
}


async function handleEmailSubmit(e) {
    e.preventDefault();

    if (!smtpConfig) {
        showToast('Please configure SMTP settings first', 'warning');
        return;
    }

    if (!uploadedImageUrl) {
        showToast('Please upload an image first', 'warning');
        return;
    }

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sending...';
    submitBtn.disabled = true;

    try {
        // Get form values - check if elements exist first
        const subjectElement = document.getElementById('subject');
        const redirectUrlElement = document.getElementById('redirectUrl');
        const emailsElement = document.getElementById('emails');
        const bodyElement = document.getElementById('body');
        const bodyText = bodyElement ? bodyElement.value.trim() : '';
        if (!subjectElement || !redirectUrlElement || !emailsElement) {
            throw new Error('Form elements not found. Please refresh the page.');
        }

        const subject = subjectElement.value.trim();
        const redirectUrl = redirectUrlElement.value.trim() || 'https://www.google.com';
        const emailsText = emailsElement.value.trim();

        const emails = emailsText.split('\n')
            .map(email => email.trim())
            .filter(email => email && isValidEmail(email));

        if (emails.length === 0) {
            throw new Error('Please enter at least one valid email address');
        }

        const data = await apiRequest('/api/send-email', {
            method: 'POST',
            body: JSON.stringify({
                subject: subject,
                body: bodyText,
                image_url: uploadedImageUrl,
                redirect_url: redirectUrl,
                emails: emails
            })
        });

        if (data.success) {
            showSendResults(data.results);

            // Clear form on success
            form.reset();
            document.getElementById('imagePreviewContainer').style.display = 'none';
            uploadedImageUrl = null;

            showToast(`Successfully processed ${emails.length} emails!`, 'success');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        showToast(`Failed to send emails: ${error.message}`, 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}


// SMTP Configuration Functions
async function loadSMTPConfig() {
    try {
        const data = await apiRequest('/api/smtp/config');

        if (data.success && data.config) {
            smtpConfig = data.config;
            populateSMTPForm(data.config);
        }
    } catch (error) {
        console.error('Failed to load SMTP config:', error);
    }
}

function populateSMTPForm(config) {
    document.getElementById('host').value = config.host || '';
    document.getElementById('port').value = config.port || 587;
    document.getElementById('username').value = config.username || '';
    document.getElementById('password').value = ''; // Don't populate password for security
    document.getElementById('use_tls').checked = config.use_tls !== false;
}

async function handleSMTPSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    // Show loading
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    submitBtn.disabled = true;

    try {
        const formData = {
            host: document.getElementById('host').value.trim(),
            port: parseInt(document.getElementById('port').value),
            username: document.getElementById('username').value.trim(),
            password: document.getElementById('password').value,
            use_tls: document.getElementById('use_tls').checked
        };

        const data = await apiRequest('/api/smtp/config', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (data.success) {
            smtpConfig = formData;
            showToast('SMTP configuration saved successfully!', 'success');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        showToast(`Failed to save SMTP config: ${error.message}`, 'error');
    } finally {
        // Reset button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

function clearSMTPConfig() {
    if (confirm('Are you sure you want to clear the SMTP configuration?')) {
        document.getElementById('smtpForm').reset();
        document.getElementById('port').value = 587;
        document.getElementById('use_tls').checked = true;
        smtpConfig = null;
        showToast('SMTP configuration cleared', 'info');
    }
}

// Test SMTP Configuration
function testSMTP() {
    if (!smtpConfig) {
        showToast('Please save SMTP configuration first', 'warning');
        return;
    }

    const modal = new bootstrap.Modal(document.getElementById('testModal'));
    modal.show();
}

async function sendTestEmail() {
    const testEmail = document.getElementById('testEmail').value.trim();

    if (!testEmail) {
        showToast('Please enter a test email address', 'warning');
        return;
    }

    const modal = bootstrap.Modal.getInstance(document.getElementById('testModal'));

    try {
        const data = await apiRequest('/api/smtp/test', {
            method: 'POST',
            body: JSON.stringify({ test_email: testEmail })
        });

        if (data.success) {
            showToast('Test email sent successfully!', 'success');
            modal.hide();
            document.getElementById('testEmail').value = '';
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        showToast(`Test failed: ${error.message}`, 'error');
    }
}


function showSendResults(results) {
    const modalBody = document.getElementById('sendResults');

    let html = '<div class="row">';

    const successful = results.filter(r => r.success);
    const failed = results.filter(r => !r.success);

    // Summary
    html += `
        <div class="col-12 mb-3">
            <div class="alert alert-info">
                <strong>Summary:</strong> ${successful.length} successful, ${failed.length} failed
            </div>
        </div>
    `;

    // Successful sends
    if (successful.length > 0) {
        html += `
            <div class="col-md-6">
                <h6 class="text-success"><i class="fas fa-check-circle me-1"></i>Successful (${successful.length})</h6>
                <div class="list-group mb-3">
        `;

        successful.forEach(result => {
            html += `
        <div class="list-group-item">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>${result.email}</span>
                <small class="tracking-id">${result.tracking_id}</small>
            </div>
            ${result.click_url ? `
                <div class="mt-2">
                    <label class="form-label small">Click Tracking URL:</label>
                    <div class="input-group input-group-sm">
                        <input type="text" class="form-control" value="${result.click_url}" readonly>
                        <button class="btn btn-outline-secondary" onclick="copyToClipboard('${result.click_url}')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
        });

        html += '</div></div>';
    }

    // Failed sends
    if (failed.length > 0) {
        html += `
            <div class="col-md-6">
                <h6 class="text-danger"><i class="fas fa-times-circle me-1"></i>Failed (${failed.length})</h6>
                <div class="list-group mb-3">
        `;

        failed.forEach(result => {
            html += `
                <div class="list-group-item">
                    <div class="mb-1">${result.email}</div>
                    <small class="text-danger">${result.error}</small>
                </div>
            `;
        });

        html += '</div></div>';
    }

    html += '</div>';

    modalBody.innerHTML = html;

    const modal = new bootstrap.Modal(document.getElementById('resultsModal'));
    modal.show();
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Click tracking URL copied to clipboard!', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Click tracking URL copied to clipboard!', 'success');
    });
}