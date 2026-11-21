/**
 * Rural Clinic Portal Logic (Portal A)
 * Allows rural doctors to create medical reports, attach PDFs,
 * transmit reliably to City Hospital, track lifecycle, and inspect ACK tokens.
 */

document.addEventListener('DOMContentLoaded', () => {
  initClinicDashboard();
});

let reportsList = [];
let currentFilter = 'all';

function initClinicDashboard() {
  loadReports();
  setupReportForm();
  setupPatientIdGenerator();
  setupDropzone();

  // Listen for offline queue changes
  window.addEventListener('rurallinkQueueChanged', (e) => {
    updateOfflineQueueUI(e.detail);
  });
}

function setupPatientIdGenerator() {
  const patientIdInput = document.getElementById('patient-id');
  if (patientIdInput && !patientIdInput.value) {
    const randomNum = Math.floor(1000 + Math.random() * 9000);
    patientIdInput.value = `PAT-${randomNum}`;
  }
}

function regeneratePatientId() {
  const patientIdInput = document.getElementById('patient-id');
  if (patientIdInput) {
    const randomNum = Math.floor(1000 + Math.random() * 9000);
    patientIdInput.value = `PAT-${randomNum}`;
  }
}

function setupDropzone() {
  const dropzone = document.getElementById('file-dropzone');
  const fileInput = document.getElementById('report-pdf-file');
  const fileSelectedNotice = document.getElementById('file-selected-name');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      updateFileDisplay();
    }
  });

  fileInput.addEventListener('change', updateFileDisplay);

  function updateFileDisplay() {
    if (fileInput.files && fileInput.files[0]) {
      const file = fileInput.files[0];
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a valid PDF file (.pdf)', 'error');
        fileInput.value = '';
        fileSelectedNotice.textContent = '';
        return;
      }
      fileSelectedNotice.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      document.getElementById('gen-sample-pdf-check').checked = false;
    } else {
      fileSelectedNotice.textContent = '';
    }
  }
}

async function loadReports() {
  try {
    const res = await window.api.getReports();
    if (res.data && res.data.reports) {
      reportsList = res.data.reports;
      renderReportsTable(reportsList);
      updateStatsCards(reportsList);
    }
  } catch (err) {
    console.error('Failed to load reports:', err);
    showToast('Failed to load reports from server: ' + err.message, 'error');
  }
}

function updateStatsCards(reports) {
  const total = reports.length;
  const received = reports.filter(r => r.status === 'Received').length;
  const underReview = reports.filter(r => r.status === 'Under Review').length;
  const responded = reports.filter(r => r.status === 'Responded').length;
  const critical = reports.filter(r => r.priority === 'Critical Emergency').length;

  document.getElementById('stat-total-sent').textContent = total;
  document.getElementById('stat-received').textContent = received;
  document.getElementById('stat-under-review').textContent = underReview;
  document.getElementById('stat-responded').textContent = responded;
  
  const critEl = document.getElementById('stat-critical');
  if (critEl) critEl.textContent = critical;
}

function filterReports(status) {
  currentFilter = status;
  // Update filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === status);
  });

  if (status === 'all') {
    renderReportsTable(reportsList);
  } else {
    const filtered = reportsList.filter(r => r.status.toLowerCase().replace(' ', '-') === status);
    renderReportsTable(filtered);
  }
}

function searchReports(query) {
  const term = query.toLowerCase().trim();
  if (!term) {
    filterReports(currentFilter);
    return;
  }
  const filtered = reportsList.filter(r => 
    r.patient_name.toLowerCase().includes(term) ||
    r.patient_id.toLowerCase().includes(term) ||
    r.report_id.toLowerCase().includes(term) ||
    r.diagnosis.toLowerCase().includes(term)
  );
  renderReportsTable(filtered);
}

function renderReportsTable(reports) {
  const tbody = document.getElementById('reports-table-body');
  if (!tbody) return;

  if (reports.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align:center; padding: 2rem; color: #64748b;">
          No reports found matching your criteria.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = reports.map(r => {
    const statusClass = `status-${r.status.toLowerCase().replace(' ', '-')}`;
    const prioClass = `prio-${r.priority.toLowerCase().replace(' ', '-')}`;
    const dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString() : 'N/A';
    const timeStr = r.created_at ? new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

    return `
      <tr>
        <td>
          <strong style="color:#0284c7;">${r.report_id}</strong>
          <div style="font-size:0.75rem; color:#64748b;">${dateStr} ${timeStr}</div>
        </td>
        <td>
          <strong>${r.patient_name}</strong>
          <div style="font-size:0.75rem; color:#64748b;">ID: ${r.patient_id} | ${r.age}y / ${r.gender}</div>
        </td>
        <td style="max-width: 220px;">
          <div style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${r.diagnosis}</div>
          <div style="font-size:0.75rem; color:#64748b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${r.symptoms}</div>
        </td>
        <td>
          <span class="badge ${prioClass}">
            <span class="badge-dot" style="background: currentColor;"></span>
            ${r.priority}
          </span>
        </td>
        <td>
          <span class="badge ${statusClass}">
            <span class="badge-dot" style="background: currentColor;"></span>
            ${r.status}
          </span>
        </td>
        <td>
          ${r.has_pdf ? `
            <a href="/api/reports/${r.report_id}/download" target="_blank" class="btn btn-secondary btn-sm" title="View Secure PDF">
              📄 PDF (${Math.round((r.pdf_size_bytes || 0) / 1024)} KB)
            </a>
          ` : '<span style="color:#94a3b8; font-size:0.8rem;">None</span>'}
        </td>
        <td>
          ${r.latest_response ? `
            <button class="btn btn-success btn-sm" onclick="viewHospitalResponse('${r.report_id}')">
              ✅ Response (${r.latest_response.department || 'City Hospital'})
            </button>
          ` : `
            <span style="color:#94a3b8; font-size:0.8rem;">Awaiting Review</span>
          `}
        </td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openNetworkInspector('${r.report_id}')" title="Inspect TCP/HTTP Packets">
            📡 Trace & ACK
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function setupReportForm() {
  const form = document.getElementById('create-report-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Check if network fault simulation is turned on
    const simFault = document.getElementById('sim-fault-toggle') ? document.getElementById('sim-fault-toggle').checked : false;

    // Show transmission animation
    const tracker = document.getElementById('transmission-tracker');
    if (tracker) tracker.style.display = 'block';

    updateStep(1, 'active'); // Step 1: Packing JSON & computing SHA-256

    const formData = new FormData(form);
    const idempotencyKey = `IDEMP-${window.api.generateUUID()}`;

    // Extract payload dictionary for offline queue fallback
    const payloadObj = {};
    for (const [key, val] of formData.entries()) {
      if (typeof val === 'string') payloadObj[key] = val;
    }

    try {
      await new Promise(r => setTimeout(r, 400));
      updateStep(1, 'done');
      updateStep(2, 'active'); // Step 2: Idempotency Key & TCP Transport

      await new Promise(r => setTimeout(r, 400));
      updateStep(2, 'done');
      updateStep(3, 'active'); // Step 3: Transmitting via HTTP REST / Port 5000

      if (simFault) {
        // User deliberately requested network fault to demonstrate retry / offline queue
        throw new Error('Simulated Network Link Failure (503 Service Unavailable). Transport layer disconnected.');
      }

      // Live transmission with exponential backoff retry support
      const result = await window.api.createReport(formData, idempotencyKey, ({ attempt, delay }) => {
        showToast(`Transmission attempt ${attempt} delayed. Retrying in ${(delay/1000).toFixed(1)}s (Exponential Backoff)...`, 'warning');
      });

      updateStep(3, 'done');
      updateStep(4, 'done'); // Step 4: Server ACK Verified

      showToast(`Report accepted by City Hospital server! ACK Token: ${result.data.server_acknowledgement.ack_token.substring(0, 10)}...`, 'success', 5000);

      // Reset form
      form.reset();
      regeneratePatientId();
      document.getElementById('file-selected-name').textContent = '';
      document.getElementById('gen-sample-pdf-check').checked = true;

      // Reload reports table
      await loadReports();

      setTimeout(() => {
        if (tracker) tracker.style.display = 'none';
        resetSteps();
      }, 4000);

    } catch (err) {
      console.warn('Transmission failed:', err);
      updateStep(3, 'failed');

      // Offline queue store-and-forward fallback
      window.offlineQueue.enqueue(payloadObj, idempotencyKey);
      showToast('Report enqueued locally. Will auto-retry once network is reachable.', 'warning', 6000);

      setTimeout(() => {
        if (tracker) tracker.style.display = 'none';
        resetSteps();
      }, 3000);
    }
  });
}

function updateStep(stepNum, state) {
  const el = document.getElementById(`step-${stepNum}`);
  if (!el) return;
  el.className = `tracker-step ${state}`;
}

function resetSteps() {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`step-${i}`);
    if (el) el.className = 'tracker-step';
  }
}

function updateOfflineQueueUI(detail) {
  const queuePanel = document.getElementById('offline-queue-panel');
  const queueList = document.getElementById('offline-queue-list');
  if (!queuePanel || !queueList) return;

  if (detail.count > 0) {
    queuePanel.style.display = 'block';
    queueList.innerHTML = detail.queue.map(item => `
      <div style="background:#fff; border:1px solid #fed7aa; border-radius:6px; padding:0.75rem; margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong>${item.payload.patient_name || 'Patient'}</strong> (ID: ${item.payload.patient_id})
          <div style="font-size:0.75rem; color:#9a3412;">Status: Queued | Attempts: ${item.attempts} | Idempotency: ${item.idempotency_key}</div>
        </div>
        <button class="btn btn-sm btn-primary" onclick="retryQueueItem('${item.queue_id}')">
          🔄 Retry Now
        </button>
      </div>
    `).join('');
  } else {
    queuePanel.style.display = 'none';
  }
}

function retryQueueItem(queueId) {
  showToast('Retrying queued transmission...', 'info');
  window.offlineQueue.flushQueue();
}

function viewHospitalResponse(reportId) {
  const report = reportsList.find(r => r.report_id === reportId);
  if (!report || !report.latest_response) {
    showToast('No hospital response recorded yet for this report', 'info');
    return;
  }

  const res = report.latest_response;
  let modal = document.getElementById('response-viewer-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'response-viewer-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">
          <span>🏥 City Hospital Medical Response</span>
        </h3>
        <button class="modal-close" onclick="document.getElementById('response-viewer-modal').classList.remove('open')">&times;</button>
      </div>
      <div class="modal-body">
        <div style="background:#ecfdf5; border-left:4px solid #059669; padding:0.75rem 1rem; margin-bottom:1rem; border-radius:4px;">
          <strong>Consulting Specialist:</strong> ${res.doctor_name} (${res.department || 'City Hospital'})<br>
          <strong>Hospital:</strong> ${res.hospital_name}<br>
          <strong>Transmitted At:</strong> ${new Date(res.created_at).toLocaleString()}
        </div>

        <div class="form-group">
          <label class="form-label">Urgency Directive</label>
          <div style="font-weight:700; color:#0f172a; font-size:1.05rem;">${res.urgency_directive}</div>
        </div>

        <div class="form-group">
          <label class="form-label">Clinical Assessment</label>
          <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:0.75rem; border-radius:6px; font-size:0.9rem;">
            ${res.clinical_assessment}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Prescription & Management Directives</label>
          <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:0.75rem; border-radius:6px; font-size:0.9rem;">
            ${res.prescription_advice}
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="document.getElementById('response-viewer-modal').classList.remove('open')">Close</button>
      </div>
    </div>
  `;
  modal.classList.add('open');
}
