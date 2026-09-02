document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeConfirmations();
    initializeAutoDismissAlerts();
    initializeSidebarToggle();
    initializeSearchForms();
    initializeDatePickers();
});

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeConfirmations() {
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

function initializeAutoDismissAlerts() {
    document.querySelectorAll('.alert-dismissible:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

function initializeSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            document.body.classList.toggle('sidebar-collapsed');
        });
    }
}

function initializeSearchForms() {
    document.querySelectorAll('.search-form').forEach(form => {
        const input = form.querySelector('input[type="search"]');
        if (input) {
            let debounceTimer;
            input.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    if (this.getAttribute('data-auto-submit') === 'true') {
                        form.submit();
                    }
                }, 300);
            });
        }
    });
}

function initializeDatePickers() {
    document.querySelectorAll('input[type="date"], input[type="datetime-local"]').forEach(input => {
        if (!input.value && input.hasAttribute('data-default-today')) {
            const today = new Date();
            if (input.type === 'date') {
                input.value = today.toISOString().split('T')[0];
            } else {
                input.value = today.toISOString().slice(0, 16);
            }
        }
    });
}

function showLoading(element) {
    element.classList.add('loading');
    element.disabled = true;
    const originalText = element.innerHTML;
    element.dataset.originalText = originalText;
    element.innerHTML = '<span class="loading-spinner me-2"></span>Loading...';
}

function hideLoading(element) {
    element.classList.remove('loading');
    element.disabled = false;
    if (element.dataset.originalText) {
        element.innerHTML = element.dataset.originalText;
    }
}

function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
}

function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1080';
        document.body.appendChild(container);
    }
    return container;
}

function formatDate(dateString, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        ...options
    };
    return new Date(dateString).toLocaleDateString(undefined, defaultOptions);
}

function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString, { hour: undefined, minute: undefined });
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'danger');
    });
}

function handleFormSubmit(form, callback) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) showLoading(submitBtn);
    
    const formData = new FormData(form);
    const url = form.action || window.location.href;
    const method = form.method || 'POST';
    
    fetch(url, {
        method: method,
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (response.redirected) {
            window.location.href = response.url;
        }
        return response.json();
    })
    .then(data => {
        if (submitBtn) hideLoading(submitBtn);
        if (data.success) {
            showToast(data.message || 'Success!', 'success');
            if (callback) callback(data);
        } else {
            showToast(data.message || 'An error occurred', 'danger');
            if (data.errors) {
                displayFormErrors(form, data.errors);
            }
        }
    })
    .catch(error => {
        if (submitBtn) hideLoading(submitBtn);
        showToast('Network error. Please try again.', 'danger');
        console.error('Form submission error:', error);
    });
}

function displayFormErrors(form, errors) {
    Object.keys(errors).forEach(field => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('is-invalid');
            let feedback = input.parentNode.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                input.parentNode.appendChild(feedback);
            }
            feedback.textContent = Array.isArray(errors[field]) ? errors[field].join(', ') : errors[field];
        }
    });
}

function clearFormErrors(form) {
    form.querySelectorAll('.is-invalid').forEach(input => {
        input.classList.remove('is-invalid');
    });
    form.querySelectorAll('.invalid-feedback').forEach(feedback => {
        feedback.remove();
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function updateUrlParams(params) {
    const url = new URL(window.location);
    Object.keys(params).forEach(key => {
        if (params[key]) {
            url.searchParams.set(key, params[key]);
        } else {
            url.searchParams.delete(key);
        }
    });
    window.history.pushState({}, '', url);
}

function getUrlParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

function initDataTable(tableId, options = {}) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const defaultOptions = {
        pageLength: 25,
        order: [[0, 'desc']],
        language: {
            search: '',
            searchPlaceholder: 'Search...',
            lengthMenu: 'Show _MENU_ entries',
            info: 'Showing _START_ to _END_ of _TOTAL_ entries',
            paginate: {
                first: 'First',
                last: 'Last',
                next: 'Next',
                previous: 'Previous'
            }
        },
        ...options
    };
    
    return $(table).DataTable(defaultOptions);
}

window.RAGApp = {
    showToast,
    showLoading,
    hideLoading,
    formatDate,
    formatRelativeTime,
    copyToClipboard,
    handleFormSubmit,
    debounce,
    updateUrlParams,
    getUrlParam,
    initDataTable
};