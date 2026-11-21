/**
 * RuralLink Client Communication & REST API Service
 * Handles:
 * - JWT Authorization headers
 * - Duplicate prevention via Idempotency-Key
 * - Exponential backoff retry mechanism for reliable transport
 * - Round-trip time (RTT) calculation
 * - Network fault resilience
 */

class APIService {
  constructor() {
    this.tokenKey = 'rurallink_jwt_token';
    this.userKey = 'rurallink_user_profile';
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  setToken(token) {
    if (token) {
      localStorage.setItem(this.tokenKey, token);
    } else {
      localStorage.removeItem(this.tokenKey);
    }
  }

  getCurrentUser() {
    try {
      return JSON.parse(localStorage.getItem(this.userKey));
    } catch {
      return null;
    }
  }

  setCurrentUser(user) {
    if (user) {
      localStorage.setItem(this.userKey, JSON.stringify(user));
    } else {
      localStorage.removeItem(this.userKey);
    }
  }

  clearAuth() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0,
        v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  /**
   * Core request engine with timing, headers, and error parsing
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${endpoint}`;
    const token = this.getToken();

    const headers = options.headers || {};
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Set idempotency key for mutations if not already specified
    if (['POST', 'PATCH', 'PUT'].includes((options.method || 'GET').toUpperCase())) {
      if (!headers['Idempotency-Key'] && options.idempotencyKey) {
        headers['Idempotency-Key'] = options.idempotencyKey;
      }
    }

    const config = {
      ...options,
      headers
    };

    const startTime = performance.now();
    try {
      const response = await fetch(url, config);
      const endTime = performance.now();
      const rttMs = Math.round(endTime - startTime);

      const contentType = response.headers.get('content-type') || '';
      let data = null;

      if (contentType.includes('application/json')) {
        data = await response.json();
      } else if (contentType.includes('application/pdf')) {
        // Blob for PDF downloads
        data = await response.blob();
        return { response, data, rttMs };
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg = (data && data.message) || response.statusText || 'Request failed';
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = data;
        error.rttMs = rttMs;
        throw error;
      }

      return { response, data, rttMs };
    } catch (err) {
      const endTime = performance.now();
      err.rttMs = Math.round(endTime - startTime);
      throw err;
    }
  }

  /**
   * Reliable Transport: Exponential backoff retry mechanism
   * Formula: backoff = baseDelay * (2 ** attempt) + randomJitter
   */
  async requestWithRetry(endpoint, options = {}, maxRetries = 4, baseDelay = 1000, onRetry = null) {
    let attempt = 0;
    // Guarantee same idempotency key across all retries to prevent duplicate processing on server
    if (!options.idempotencyKey && ['POST', 'PUT', 'PATCH'].includes((options.method || 'GET').toUpperCase())) {
      options.idempotencyKey = `IDEMP-${this.generateUUID()}`;
    }

    while (attempt < maxRetries) {
      try {
        return await this.request(endpoint, options);
      } catch (err) {
        attempt++;
        // Retry on network errors or 5xx server issues (e.g. 503, 504)
        const isNetworkOrServerError = !err.status || (err.status >= 500 && err.status <= 504);
        
        if (attempt >= maxRetries || !isNetworkOrServerError) {
          throw err;
        }

        const jitter = Math.floor(Math.random() * 300);
        const delay = (baseDelay * Math.pow(2, attempt - 1)) + jitter;

        if (typeof onRetry === 'function') {
          onRetry({ attempt, maxRetries, delay, error: err });
        }

        console.warn(`[DataComm Reliable Transport] Attempt ${attempt} failed with ${err.message}. Retrying in ${delay}ms...`);
        await new Promise((res) => setTimeout(res, delay));
      }
    }
  }

  // Auth Methods
  async login(email, password) {
    const res = await this.request('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (res.data && res.data.token) {
      this.setToken(res.data.token);
      this.setCurrentUser(res.data.user);
    }
    return res;
  }

  async logout() {
    try {
      await this.request('/api/auth/logout', { method: 'POST' });
    } finally {
      this.clearAuth();
    }
  }

  async getProfile() {
    return await this.request('/api/auth/me');
  }

  // Reports API Methods
  async getReports(params = {}) {
    const query = new URLSearchParams(params).toString();
    const endpoint = `/api/reports${query ? '?' + query : ''}`;
    return await this.request(endpoint);
  }

  async getReport(reportId) {
    return await this.request(`/api/reports/${reportId}`);
  }

  async createReport(formData, idempotencyKey, onRetry) {
    // Handle multipart form submission with idempotency key and exponential backoff
    const options = {
      method: 'POST',
      body: formData,
      idempotencyKey: idempotencyKey || `IDEMP-${this.generateUUID()}`
    };
    return await this.requestWithRetry('/api/reports', options, 4, 1200, onRetry);
  }

  async updateReportStatus(reportId, status) {
    return await this.request(`/api/reports/${reportId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
  }

  async submitHospitalResponse(reportId, responseData) {
    return await this.request(`/api/reports/${reportId}/response`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(responseData)
    });
  }

  async requestAck(reportId) {
    return await this.request(`/api/reports/${reportId}/ack`, {
      method: 'POST'
    });
  }

  async getNetworkTrace(reportId) {
    return await this.request(`/api/reports/${reportId}/network-trace`);
  }

  async getLabStats() {
    return await this.request('/api/network-lab/stats');
  }

  async simulateFault(type = 'drop', delaySeconds = 2) {
    return await this.request('/api/network-lab/simulate-fault', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fault_type: type, delay_seconds: delaySeconds })
    });
  }
}

// Global API instance
window.api = new APIService();

// Toast Notifications Helper
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button style="background:none;border:none;cursor:pointer;color:#94a3b8;font-size:1.1rem;margin-left:0.5rem;" onclick="this.parentElement.remove()">&times;</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, duration);
}
