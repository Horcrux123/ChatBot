// Base API URL configuration from environment variables or local fallback
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Standard fetch wrapper that automatically injects cookies credentials 
 * and handles base responses.
 */
async function request(path, options = {}) {
  const url = `${API_BASE.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
  
  // Enforce include credentials so session cookie is sent & stored
  options.credentials = 'include';
  options.headers = {
    'Accept': 'application/json',
    ...options.headers
  };
  
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, options);

  if (response.status === 401 && !path.includes('/auth/me')) {
    // Session expired or unauthorized, redirect to login page
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    let errMsg = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      errMsg = errorJson.detail || errMsg;
    } catch (_) {}
    throw new Error(errMsg);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const apiClient = {
  /**
   * Sends a chat message to the assistant.
   * If confirming or cancelling a pending action, message should be empty string
   * and confirmed parameter should be true or false.
   */
  async sendMessage(message, sessionId, confirmed = null) {
    return request('/chat', {
      method: 'POST',
      body: {
        message: message,
        session_id: sessionId,
        confirmed: confirmed
      }
    });
  },

  /**
   * Retrieves profile details of the currently logged-in user.
   * Used for initial auth checking on route guards.
   */
  async checkAuth() {
    return request('/auth/me', {
      method: 'GET'
    });
  },

  /**
   * Logs out the user and destroys the session cookie.
   */
  async logout() {
    return request('/auth/logout', {
      method: 'POST'
    });
  }
};
