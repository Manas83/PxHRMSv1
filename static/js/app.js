// HRMS Application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation enhancement
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Confirmation dialogs for delete actions
    var deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var message = this.getAttribute('data-confirm') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Loading state for buttons
    var loadingButtons = document.querySelectorAll('.btn-loading');
    loadingButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            this.classList.add('disabled');
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
        });
    });

    // Auto-refresh for dashboard every 5 minutes
    if (window.location.pathname.includes('dashboard')) {
        setInterval(function() {
            // Only refresh if user is active (has interacted in last 5 minutes)
            if (Date.now() - lastActivity < 300000) {
                location.reload();
            }
        }, 300000); // 5 minutes
    }

    // Track user activity
    var lastActivity = Date.now();
    document.addEventListener('click', function() {
        lastActivity = Date.now();
    });
    document.addEventListener('keypress', function() {
        lastActivity = Date.now();
    });

    // Real-time clock update
    updateClock();
    setInterval(updateClock, 1000);

    // File upload preview
    var fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    // Create preview if it's an image
                    if (file.type.startsWith('image/')) {
                        var preview = document.createElement('img');
                        preview.src = e.target.result;
                        preview.className = 'img-thumbnail mt-2';
                        preview.style.maxWidth = '200px';
                        
                        // Remove existing preview
                        var existingPreview = input.parentNode.querySelector('.file-preview');
                        if (existingPreview) {
                            existingPreview.remove();
                        }
                        
                        // Add new preview
                        var previewContainer = document.createElement('div');
                        previewContainer.className = 'file-preview mt-2';
                        previewContainer.appendChild(preview);
                        input.parentNode.appendChild(previewContainer);
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    });
});

// Clock update function
function updateClock() {
    var clockElements = document.querySelectorAll('.current-time');
    var now = new Date();
    var timeString = now.toLocaleTimeString();
    
    clockElements.forEach(function(element) {
        element.textContent = timeString;
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    // Create notification element
    var notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(function() {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function formatDuration(hours) {
    if (!hours) return '0h 0m';
    
    var h = Math.floor(hours);
    var m = Math.floor((hours - h) * 60);
    return h + 'h ' + m + 'm';
}

function formatDate(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(time) {
    if (typeof time === 'string') {
        time = new Date(time);
    }
    
    return time.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// AJAX helper function
function makeRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    const finalOptions = Object.assign(defaultOptions, options);
    
    return fetch(url, finalOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred. Please try again.', 'danger');
            throw error;
        });
}

// Export functions for use in other scripts
window.HRMS = {
    showNotification: showNotification,
    formatDuration: formatDuration,
    formatDate: formatDate,
    formatTime: formatTime,
    makeRequest: makeRequest
};
