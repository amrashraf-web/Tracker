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

// Email Sending Functions
async function handleEmailSubmit(e) {
    e.preventDefault();

    if (!smtpConfig) {
        showToast('Please configure SMTP settings first', 'warning');
        return;
    }

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    // Show loading
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sending...';
    submitBtn.disabled = true;

    try {
        const subject = document.getElementById('subject').value.trim();
        const body = document.getElementById('body').value.trim();
        const emailsText = document.getElementById('emails').value.trim();

        // Parse emails
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
                body: body,
                emails: emails
            })
        });

        if (data.success) {
            showSendResults(data.results);

            // Clear form on success
            document.getElementById('emailForm').reset();

            showToast(`Successfully processed ${emails.length} emails!`, 'success');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        showToast(`Failed to send emails: ${error.message}`, 'error');
    } finally {
        // Reset button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
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
                    <div class="d-flex justify-content-between align-items-center">
                        <span>${result.email}</span>
                        <small class="tracking-id">${result.tracking_id}</small>
                    </div>
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