/**
 * RuralLink Offline Queue & Local Storage Resilience
 * Implements store-and-forward architecture for rural clinics with intermittent network connectivity.
 */

class OfflineQueueManager {
  constructor() {
    this.storageKey = 'rurallink_offline_report_queue';
    this.isProcessing = false;
    this.initNetworkListeners();
  }

  initNetworkListeners() {
    window.addEventListener('online', () => {
      this.updateNetworkUI(true);
      showToast('Network restored. Flushing offline transmission queue...', 'info');
      this.flushQueue();
    });

    window.addEventListener('offline', () => {
      this.updateNetworkUI(false);
      showToast('Network connection lost! Reports will be queued locally until reconnected.', 'warning', 6000);
    });

    // Check status on load
    document.addEventListener('DOMContentLoaded', () => {
      this.updateNetworkUI(navigator.onLine);
      this.notifySubscribers();
    });
  }

  updateNetworkUI(isOnline) {
    const banner = document.getElementById('offline-banner');
    const netStatusBadge = document.getElementById('network-status-badge');
    
    if (banner) {
      banner.style.display = isOnline ? 'none' : 'flex';
    }
    if (netStatusBadge) {
      if (isOnline) {
        netStatusBadge.className = 'badge status-received';
        netStatusBadge.innerHTML = '<span class="badge-dot" style="background:#059669"></span> Online (HTTP/TCP)';
      } else {
        netStatusBadge.className = 'badge status-failed';
        netStatusBadge.innerHTML = '<span class="badge-dot" style="background:#dc2626"></span> Offline (Queue Active)';
      }
    }
  }

  getQueue() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  saveQueue(queue) {
    localStorage.setItem(this.storageKey, JSON.stringify(queue));
    this.notifySubscribers();
  }

  enqueue(reportPayload, idempotencyKey) {
    const queue = this.getQueue();
    const item = {
      queue_id: `QUEUED-${Date.now()}-${Math.floor(Math.random()*1000)}`,
      idempotency_key: idempotencyKey,
      payload: reportPayload,
      status: 'Queued',
      attempts: 0,
      created_at: new Date().toISOString(),
      last_error: null
    };

    queue.push(item);
    this.saveQueue(queue);
    showToast(`Report saved to offline local queue (ID: ${item.queue_id}).`, 'warning');
    return item;
  }

  removeFromQueue(queueId) {
    let queue = this.getQueue();
    queue = queue.filter(item => item.queue_id !== queueId);
    this.saveQueue(queue);
  }

  notifySubscribers() {
    const queue = this.getQueue();
    const event = new CustomEvent('rurallinkQueueChanged', { detail: { count: queue.length, queue } });
    window.dispatchEvent(event);

    const badge = document.getElementById('queued-count-badge');
    if (badge) {
      badge.textContent = queue.length;
      badge.style.display = queue.length > 0 ? 'inline-flex' : 'none';
    }
  }

  /**
   * Automatically attempts to flush queued reports to the Flask REST API
   */
  async flushQueue() {
    if (this.isProcessing || !navigator.onLine) return;
    const queue = this.getQueue();
    if (queue.length === 0) return;

    this.isProcessing = true;
    console.log(`[Offline Queue] Initiating flush for ${queue.length} reports...`);

    for (const item of [...queue]) {
      try {
        const formData = new FormData();
        for (const [key, val] of Object.entries(item.payload)) {
          formData.append(key, val);
        }

        // Send with preserved idempotency key
        const result = await window.api.createReport(formData, item.idempotency_key);
        
        if (result.data && result.data.success) {
          console.log(`[Offline Queue] Flushed successfully: ${result.data.report.report_id}`);
          this.removeFromQueue(item.queue_id);
          showToast(`Offline report successfully transmitted! Server Report ID: ${result.data.report.report_id}`, 'success');
          
          // Trigger refresh of reports table if on clinic page
          if (typeof loadReports === 'function') {
            loadReports();
          }
        }
      } catch (err) {
        console.warn(`[Offline Queue] Flush attempt failed for ${item.queue_id}:`, err);
        item.attempts += 1;
        item.last_error = err.message;
        item.last_attempt = new Date().toISOString();
        this.saveQueue(queue);
      }
    }

    this.isProcessing = false;
  }
}

window.offlineQueue = new OfflineQueueManager();
