// Utility to read cookies by name
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Show alert banners
function showAlert(message, type = 'success') {
    const banner = document.getElementById('alert-banner');
    if (!banner) return;
    
    banner.textContent = message;
    banner.className = `alert-banner ${type}`;
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        banner.classList.add('hidden');
    }, 5000);
}

// Wrapper for all backend requests, enforcing CSRF protection on writes
async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    
    // Set headers
    if (!(options.body instanceof FormData)) {
        options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
    }
    
    // State-changing requests must attach double-submit CSRF token
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE'].includes(method)) {
        const csrfToken = getCookie('csrf_token');
        if (csrfToken) {
            options.headers['X-CSRF-Token'] = csrfToken;
        }
    }
    
    // Always include credentials (cookies)
    options.credentials = 'include';
    
    try {
        const response = await fetch(url, options);
        
        // Handle Session Expiry or lack of authentication
        if (response.status === 401) {
            // Invalidate local user caches
            localStorage.removeItem('user');
            // Route back to auth view
            switchView('auth');
            updateNav();
            return { error: 'Session expired. Please log in.' };
        }
        
        // If file download response (CSV exports)
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/csv')) {
            return response;
        }
        
        const data = await response.json();
        if (!response.ok) {
            return { error: data.detail || 'An error occurred.' };
        }
        
        return data;
    } catch (err) {
        console.error('Fetch error:', err);
        return { error: 'Network connection failed.' };
    }
}
