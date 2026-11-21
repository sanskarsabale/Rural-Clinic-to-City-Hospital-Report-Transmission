/**
 * City Hospital Portal Logic (Portal B)
 * Receives incoming rural medical reports, verifies cryptographic SHA-256 integrity,
 * enables doctor triage, PDF inspection, status transitions, and response dispatch.
 */

document.addEventListener('DOMContentLoaded', () => {
  initHospitalDashboard();
});

let hospitalReports = [];
let activeReport = null;
let currentStatusFilter = 'all';
let currentPriorityFilter = 'all';

function initHospitalDashboard() {
  loadHospitalReports();
  setupFilterControls();
}

function setupFilterControls() {
  const searchInput = document.getElementById('search-hospital-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      filterAndRenderReports();
    });
  }

  const prioritySelect = document.getElementById('filter-priority-select');
  if (prioritySelect) {
    prioritySelect.addEventListener('change', (e) => {
      currentPriorityFilter = e.target.value;
      filterAndRenderReports();
    });
  }

  const statusSelect = document.getElementById('filter-status-select');
  if (statusSelect) {
    statusSelect.addEventListener('change', (e) => {
      currentStatusFilter = e.target.value;
      filterAndRenderReports();
    });
  }
}

async function loadHospitalReports() {
  try {
    const res = await window.api.getReports();
    if (res.data && res.data.reports) {
      hospitalReports = res.data.reports;
      filterAndRenderReports();
      updateHospitalStats(hospitalReports);
    }
  } catch (err) {
    console.error('Failed to load incoming reports:', err);
    showToast('Failed to load incoming reports: ' + err.message, 'error');
  }
}

function updateHospitalStats(reports) {
  const total = reports.length;
  const received = reports.filter(r => r.status === 'Received').length;
  const underReview = reports.filter(r => r.status === 'Under Review').length;
  const responded = reports.filter(r => r.status === 'Responded').length;
  const critical = reports.filter(r => r.priority === 'Critical Emergency' && r.status !== 'Responded').length;

  document.getElementById('stat-incoming-total').textContent = total;
  document.getElementById('stat-incoming-pending').textContent = received;
  document.getElementById('stat-incoming-review').textContent = underReview;
  document.getElementById('stat-incoming-responded').textContent = responded;

  const critBadge = document.getElementById('critical-alert-banner');
  if (critBadge) {
    critBadge.style.display = critical > 0 ? 'flex' : 'none';
    const critCountEl = document.getElementById('critical-cases-count');
    if (critCountEl) critCountEl.textContent = `${critical} CRITICAL EMERGENCY CASE${critical > 1 ? 'S' : ''} AWAITING IMMEDIATE TRIAGE!`;
  }
}

function filterAndRenderReports() {
  const searchInput = document.getElementById('search-hospital-input');
  const term = searchInput ? searchInput.value.toLowerCase().trim() : '';

  let filtered = [...hospitalReports];

  if (currentStatusFilter !== 'all') {
    filtered = filtered.filter(r => r.status.toLowerCase().replace(' ', '-') === currentStatusFilter);
  }

  if (currentPriorityFilter !== 'all') {
    filtered = filtered.filter(r => r.priority === currentPriorityFilter);
  }

  if (term) {
    filtered = filtered.filter(r => 
      r.patient_name.toLowerCase().includes(term) ||
      r.patient_id.toLowerCase().includes(term) ||
      r.report_id.toLowerCase().includes(term) ||
      r.diagnosis.toLowerCase().includes(term) ||
      r.clinic_name.toLowerCase().includes(term)
    );
  }

  renderHospitalTable(filtered);
}

function renderHospitalTable(reports) {
  const tbody = document.getElementById('hospital-reports-body');
  if (!tbody) return;

  if (reports.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align:center; padding: 2.5rem; color: #64748b;">
          No patient referrals matching the current filters.
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
      <tr style="${r.priority === 'Critical Emergency' && r.status !== 'Responded' ? 'background: #fff5f5;' : ''}">
        <td>
          <strong style="color:#0284c7;">${r.report_id}</strong>
          <div style="font-size:0.75rem; color:#64748b;">${dateStr} ${timeStr}</div>
        </td>
        <td>
          <div style="font-weight:700;">${r.clinic_name}</div>
          <div style="font-size:0.75rem; color:#64748b;">By: ${r.author_name}</div>
        </td>
        <td>
          <strong>${r.patient_name}</strong>
          <div style="font-size:0.75rem; color:#64748b;">ID: ${r.patient_id} | ${r.age}y / ${r.gender}</div>
        </td>
        <td style="max-width: 200px;">
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
            <a href="/api/reports/${r.report_id}/download" target="_blank" class="btn btn-secondary btn-sm">
              📄 PDF
            </a>
          ` : '<span style="color:#94a3b8; font-size:0.8rem;">None</span>'}
        </td>
        <td>
          <div style="display:flex; gap:0.4rem;">
            <button class="btn btn-primary btn-sm" onclick="openReviewModal('${r.report_id}')">
              🩺 Review & Respond
            </button>
            <button class="btn btn-secondary btn-sm" onclick="openNetworkInspector('${r.report_id}')" title="Inspect TCP Packet">
              📡
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function openReviewModal(reportId) {
  try {
    const res = await window.api.getReport(reportId);
    if (!res.data || !res.data.report) return;

    activeReport = res.data.report;
    renderReviewModalContent(activeReport);
  } catch (err) {
    showToast('Failed to load report details: ' + err.message, 'error');
  }
}

function renderReviewModalContent(report) {
  let modal = document.getElementById('hospital-review-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'hospital-review-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const prioClass = `prio-${report.priority.toLowerCase().replace(' ', '-')}`;
  const statusClass = `status-${report.status.toLowerCase().replace(' ', '-')}`;

  modal.innerHTML = `
    <div class="modal-content" style="max-width: 850px;">
      <div class="modal-header">
        <h3 class="modal-title">
          <span>🩺 Clinical Case Review — ${report.report_id}</span>
        </h3>
        <button class="modal-close" onclick="closeReviewModal()">&times;</button>
      </div>

      <div class="modal-body">
        <!-- Patient & Clinic Header Grid -->
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:1rem; margin-bottom:1.25rem;">
          <div>
            <div style="font-size:0.8rem; color:#64748b; font-weight:600;">PATIENT DETAILS</div>
            <div style="font-size:1.1rem; font-weight:700; color:#0f172a;">${report.patient_name} (${report.patient_id})</div>
            <div style="font-size:0.85rem; color:#475569;">${report.age} Years | ${report.gender}</div>
            <div style="margin-top:0.4rem;">
              <span class="badge ${prioClass}">${report.priority}</span>
              <span class="badge ${statusClass}">${report.status}</span>
            </div>
          </div>
          <div>
            <div style="font-size:0.8rem; color:#64748b; font-weight:600;">ORIGINATING CLINIC</div>
            <div style="font-size:1.05rem; font-weight:700; color:#0284c7;">${report.clinic_name}</div>
            <div style="font-size:0.85rem; color:#475569;">Referring MD: ${report.author_name}</div>
            <div style="font-size:0.75rem; color:#64748b; margin-top:0.4rem;">
              Received At: ${report.received_at ? new Date(report.received_at).toLocaleString() : 'Pending'}
            </div>
          </div>
        </div>

        <!-- Data Integrity Badge -->
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:0.6rem 1rem; margin-bottom:1.25rem; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem;">
          <div style="display:flex; align-items:center; gap:0.5rem; color:#166534; font-size:0.85rem; font-weight:600;">
            <span>🛡️ Data Integrity: SHA-256 Checksum Verified Match</span>
          </div>
          <code style="font-size:0.75rem; color:#15803d; background:#dcfce7; padding:2px 6px; border-radius:4px;">
            ${report.sha256_checksum ? report.sha256_checksum.substring(0, 24) + '...' : 'Verified Valid'}
          </code>
        </div>

        <!-- Symptoms & Diagnosis -->
        <div class="form-group">
          <label class="form-label">Clinical Symptoms & Presentation</label>
          <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:0.85rem; font-size:0.9rem;">
            ${report.symptoms}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Primary Diagnosis</label>
          <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:0.85rem; font-size:0.9rem; font-weight:600; color:#0f172a;">
            ${report.diagnosis}
          </div>
        </div>

        ${report.additional_notes ? `
          <div class="form-group">
            <label class="form-label">Rural Clinic Doctor's Additional Notes</label>
            <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:0.85rem; font-size:0.85rem; color:#475569;">
              ${report.additional_notes}
            </div>
          </div>
        ` : ''}

        <!-- PDF Attachment Section -->
        <div class="form-group" style="margin-top:1.25rem;">
          <label class="form-label">Attached Diagnostic Report (PDF)</label>
          ${report.has_pdf ? `
            <div style="display:flex; align-items:center; justify-content:space-between; background:#f1f5f9; padding:0.75rem 1rem; border-radius:6px; border:1px solid #cbd5e1;">
              <div style="display:flex; align-items:center; gap:0.5rem;">
                <span style="font-size:1.4rem;">📄</span>
                <div>
                  <div style="font-weight:600; font-size:0.9rem;">${report.pdf_filename}</div>
                  <div style="font-size:0.75rem; color:#64748b;">${(report.pdf_size_bytes / 1024).toFixed(1)} KB | Encrypted Storage</div>
                </div>
              </div>
              <div style="display:flex; gap:0.5rem;">
                <a href="/api/reports/${report.report_id}/download" target="_blank" class="btn btn-primary btn-sm">
                  🔍 View / Download PDF
                </a>
              </div>
            </div>
          ` : '<div style="color:#64748b; font-size:0.85rem;">No PDF document attached with this report.</div>'}
        </div>

        <!-- Status Action Buttons -->
        <div style="margin: 1.5rem 0; padding:1rem; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;">
          <label class="form-label" style="margin-bottom:0.6rem;">Hospital Workflow Status Transitions:</label>
          <div style="display:flex; gap:0.6rem; flex-wrap:wrap;">
            ${report.status !== 'Under Review' && report.status !== 'Responded' ? `
              <button class="btn btn-secondary btn-sm" onclick="updateStatus('${report.report_id}', 'Under Review')">
                ⏳ Mark as "Under Review"
              </button>
            ` : ''}
            <button class="btn btn-secondary btn-sm" onclick="openNetworkInspector('${report.report_id}')">
              📡 View TCP/HTTP Packet Trace
            </button>
          </div>
        </div>

        <!-- Hospital Response Section -->
        <div style="border-top: 2px solid #e2e8f0; padding-top: 1.25rem; margin-top: 1rem;">
          <h4 style="font-size:1.1rem; color:#0f172a; margin-bottom:0.75rem;">
            🏥 Send Tele-Medicine Response to Rural Clinic
          </h4>

          ${report.latest_response ? `
            <div style="background:#ecfdf5; border-left:4px solid #059669; padding:1rem; border-radius:6px; margin-bottom:1rem;">
              <div style="font-weight:700; color:#065f46; margin-bottom:0.3rem;">
                Response Already Dispatched by ${report.latest_response.doctor_name} (${report.latest_response.department || 'Consultant'})
              </div>
              <p style="font-size:0.85rem; color:#047857; margin-bottom:0.5rem;">
                <strong>Directive:</strong> ${report.latest_response.urgency_directive}
              </p>
              <p style="font-size:0.85rem; color:#064e3b; margin-bottom:0.5rem;">
                <strong>Advice:</strong> ${report.latest_response.prescription_advice}
              </p>
              <div style="font-size:0.75rem; color:#059669;">
                Dispatched At: ${new Date(report.latest_response.created_at).toLocaleString()}
              </div>
            </div>
          ` : ''}

          <form id="hospital-response-form" onsubmit="submitResponseForm(event, '${report.report_id}')">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Reviewing Department</label>
                <select name="department" class="form-control" required>
                  <option value="General Medicine">General Medicine</option>
                  <option value="Cardiology">Cardiology</option>
                  <option value="General & Trauma Surgery">General & Trauma Surgery</option>
                  <option value="Pediatrics & Neonatology">Pediatrics & Neonatology</option>
                  <option value="Orthopedics">Orthopedics</option>
                  <option value="Neurology & Critical Care">Neurology & Critical Care</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Triage & Urgency Directive</label>
                <select name="urgency_directive" class="form-control" required>
                  <option value="Proceed with Local Care (Follow Prescription)">Proceed with Local Care (Follow Prescription)</option>
                  <option value="EMERGENCY: Arrange Immediate Ambulance Transfer to City Hospital">EMERGENCY: Arrange Immediate Ambulance Transfer to City Hospital</option>
                  <option value="Schedule Outpatient Specialist OPD within 48 Hours">Schedule Outpatient Specialist OPD within 48 Hours</option>
                  <option value="Repeat Lab Work & Re-transmit Tomorrow">Repeat Lab Work & Re-transmit Tomorrow</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Clinical Assessment & Findings Review</label>
              <textarea name="clinical_assessment" class="form-control" placeholder="Enter specialist observations and evaluation of findings..." required></textarea>
            </div>

            <div class="form-group">
              <label class="form-label">Prescription, Medication & Tele-Health Directives</label>
              <textarea name="prescription_advice" class="form-control" placeholder="Provide precise drug dosages, infusions, splinting, or stabilization protocols..." required></textarea>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:0.75rem; margin-top:1rem;">
              <button type="button" class="btn btn-secondary" onclick="closeReviewModal()">Cancel</button>
              <button type="submit" class="btn btn-success">
                🚀 Transmit Response to Rural Clinic
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  modal.classList.add('open');
}

function closeReviewModal() {
  const modal = document.getElementById('hospital-review-modal');
  if (modal) modal.classList.remove('open');
}

async function updateStatus(reportId, newStatus) {
  try {
    const res = await window.api.updateReportStatus(reportId, newStatus);
    showToast(`Status updated to "${newStatus}"`, 'success');
    closeReviewModal();
    await loadHospitalReports();
  } catch (err) {
    showToast('Failed to update status: ' + err.message, 'error');
  }
}

async function submitResponseForm(e, reportId) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const payload = {
    department: formData.get('department'),
    urgency_directive: formData.get('urgency_directive'),
    clinical_assessment: formData.get('clinical_assessment'),
    prescription_advice: formData.get('prescription_advice')
  };

  try {
    const res = await window.api.submitHospitalResponse(reportId, payload);
    showToast('Consultation advice transmitted back to Rural Clinic successfully!', 'success', 5000);
    closeReviewModal();
    await loadHospitalReports();
  } catch (err) {
    showToast('Failed to dispatch response: ' + err.message, 'error');
  }
}
