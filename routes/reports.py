import os
import time
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from models import db, Report, HospitalResponse, TransmissionLog, IdempotencyRecord, User
from utils.auth import login_required, role_required, get_current_user
from utils.security import allowed_file, compute_sha256, generate_ack_token, clean_filename
from utils.sample_pdf import generate_medical_report_pdf

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

VALID_STATUSES = ['Created', 'Queued', 'Sent', 'Received', 'Under Review', 'Responded', 'Failed']
VALID_PRIORITIES = ['Low', 'Normal', 'Urgent', 'Critical Emergency']

@reports_bp.route('', methods=['GET'])
@login_required
def get_reports():
    """
    Fetch reports filtered by user role and query parameters.
    - Rural Doctors see reports originating from their clinic.
    - Hospital Doctors see all incoming referrals from rural clinics.
    Supports query filters: status, priority, search (patient name or ID).
    """
    start_time = time.time()
    user = request.current_user
    
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    search_query = request.args.get('search')
    
    query = Report.query
    
    # Role-based scoping
    if user.role == 'rural_doctor':
        # Rural clinic doctor sees reports from their clinic or created by them
        query = query.filter((Report.created_by_user_id == user.user_id) | (Report.clinic_name == user.organization))
    # Hospital doctors see all reports directed to city hospital
    
    # Filter by Status
    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter_by(status=status_filter)
        
    # Filter by Priority
    if priority_filter and priority_filter in VALID_PRIORITIES:
        query = query.filter_by(priority=priority_filter)
        
    # Search query
    if search_query:
        search_term = f"%{search_query.strip()}%"
        query = query.filter(
            (Report.patient_name.ilike(search_term)) |
            (Report.patient_id.ilike(search_term)) |
            (Report.report_id.ilike(search_term)) |
            (Report.diagnosis.ilike(search_term))
        )
        
    reports = query.order_by(Report.created_at.desc()).all()
    rtt = round((time.time() - start_time) * 1000, 2)
    
    return jsonify({
        'success': True,
        'count': len(reports),
        'reports': [r.to_dict() for r in reports],
        'network_metrics': {
            'rtt_ms': rtt,
            'protocol': 'HTTP/1.1 REST',
            'role_scope': user.role
        }
    }), 200


@reports_bp.route('', methods=['POST'])
@login_required
@role_required('rural_doctor', 'admin')
def create_report():
    """
    Create and submit a medical report with optional PDF attachment.
    Demonstrates:
    - TCP/IP & HTTP 201 Created semantics
    - Duplicate request prevention via Idempotency-Key
    - Data integrity via SHA-256 hash calculation
    - Server acknowledgement (ACK token generation)
    """
    start_time = time.time()
    user = request.current_user
    
    # 1. Check for Idempotency-Key header to prevent duplicate transmission
    idempotency_key = request.headers.get('Idempotency-Key') or request.form.get('idempotency_key')
    
    if idempotency_key:
        existing_record = IdempotencyRecord.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_record:
            # Duplicate transmission detected!
            rtt = round((time.time() - start_time) * 1000, 2)
            log = TransmissionLog(
                report_id=existing_record.report_id,
                event_type='DUPLICATE_BLOCKED',
                http_method='POST',
                endpoint='/api/reports',
                status_code=409,
                round_trip_ms=rtt,
                client_ip=request.remote_addr,
                details=f"Duplicate request prevented by Idempotency-Key: {idempotency_key}"
            )
            db.session.add(log)
            db.session.commit()
            
            # Return 409 Conflict with cached duplicate details
            try:
                cached_data = json.loads(existing_record.response_body)
            except Exception:
                cached_data = {'report_id': existing_record.report_id}
                
            return jsonify({
                'success': False,
                'error': 'Conflict / Duplicate Request',
                'message': f"Duplicate transmission rejected: A report with this Idempotency-Key has already been processed.",
                'idempotency_key': idempotency_key,
                'existing_report_id': existing_record.report_id,
                'cached_report': cached_data
            }), 409

    # 2. Extract Data (handles multipart/form-data or application/json)
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # Validation
    required_fields = ['patient_id', 'patient_name', 'age', 'gender', 'symptoms', 'diagnosis']
    missing_fields = [f for f in required_fields if not data.get(f)]
    if missing_fields:
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': f"Missing required fields: {', '.join(missing_fields)}"
        }), 400

    try:
        age = int(data['age'])
        if age < 0 or age > 130:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'Age must be a valid integer between 0 and 130'
        }), 400

    priority = data.get('priority', 'Normal')
    if priority not in VALID_PRIORITIES:
        priority = 'Normal'

    # Create new Report instance
    new_report = Report(
        patient_id=data['patient_id'].strip().upper(),
        patient_name=data['patient_name'].strip(),
        age=age,
        gender=data['gender'].strip(),
        symptoms=data['symptoms'].strip(),
        diagnosis=data['diagnosis'].strip(),
        priority=priority,
        additional_notes=data.get('additional_notes', '').strip(),
        created_by_user_id=user.user_id,
        clinic_name=user.organization,
        status='Received',  # Server accepts transmission and marks Received
        received_at=datetime.utcnow(),
        idempotency_key=idempotency_key
    )

    # 3. Handle PDF file attachment
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    
    file_bytes = None
    pdf_filename = None
    
    # Check if a file was uploaded
    if 'file' in request.files and request.files['file'].filename:
        uploaded_file = request.files['file']
        if not allowed_file(uploaded_file.filename):
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': 'Only PDF files (.pdf) are permitted for report attachments'
            }), 400
            
        file_bytes = uploaded_file.read()
        # Verify PDF header magic bytes (%PDF)
        if not file_bytes.startswith(b'%PDF'):
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': 'Invalid file format: File header is not a valid PDF'
            }), 400
            
        pdf_filename = clean_filename(uploaded_file.filename, new_report.report_id)
        
    elif data.get('generate_sample_pdf') == 'true' or data.get('generate_sample_pdf') is True:
        # Generate realistic clinical diagnostic PDF automatically
        file_bytes = generate_medical_report_pdf(
            patient_name=new_report.patient_name,
            patient_id=new_report.patient_id,
            age=new_report.age,
            gender=new_report.gender,
            symptoms=new_report.symptoms,
            diagnosis=new_report.diagnosis,
            priority=new_report.priority,
            clinic_name=new_report.clinic_name,
            doctor_name=user.name
        )
        pdf_filename = f"{new_report.report_id}_Clinical_Report.pdf"

    if file_bytes:
        file_path = os.path.join(upload_dir, pdf_filename)
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
            
        new_report.pdf_filename = pdf_filename
        new_report.pdf_path = file_path
        new_report.pdf_size_bytes = len(file_bytes)
        new_report.sha256_checksum = compute_sha256(file_bytes)

    # 4. Generate Server Acknowledgement (ACK) Token
    ack_token = generate_ack_token(new_report.report_id)
    new_report.ack_token = ack_token
    
    db.session.add(new_report)
    db.session.flush() # Flush to get report_id committed in transaction

    # 5. Record in Idempotency cache if key was provided
    rtt = round((time.time() - start_time) * 1000, 2)
    report_dict = new_report.to_dict()
    
    if idempotency_key:
        idemp_record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            report_id=new_report.report_id,
            request_hash=compute_sha256(json.dumps(data, sort_keys=True)),
            response_status=201,
            response_body=json.dumps(report_dict)
        )
        db.session.add(idemp_record)

    # 6. Create Transmission Log
    log = TransmissionLog(
        report_id=new_report.report_id,
        event_type='REPORT_RECEIVED_AND_ACKED',
        http_method='POST',
        endpoint='/api/reports',
        status_code=201,
        round_trip_ms=rtt,
        client_ip=request.remote_addr,
        client_agent=request.headers.get('User-Agent', '')[:250],
        payload_checksum=new_report.sha256_checksum,
        ack_token=ack_token,
        details=f"Report {new_report.report_id} accepted from {user.name} ({user.organization}). PDF attached: {bool(file_bytes)}"
    )
    db.session.add(log)
    db.session.commit()

    # 7. Return 201 Created with comprehensive Server ACK packet
    return jsonify({
        'success': True,
        'message': 'Report received and verified by City Hospital server',
        'report': report_dict,
        'server_acknowledgement': {
            'status': 'ACK_ACCEPTED',
            'report_id': new_report.report_id,
            'ack_token': ack_token,
            'sha256_checksum': new_report.sha256_checksum,
            'timestamp': new_report.received_at.isoformat() if new_report.received_at else None,
            'delivery_guarantee': 'AT_LEAST_ONCE_IDEMPOTENT',
            'rtt_ms': rtt
        }
    }), 201


@reports_bp.route('/<report_id>', methods=['GET'])
@login_required
def get_report_detail(report_id):
    """Retrieve full details of a specific report including audit logs and responses"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': f"Report with ID '{report_id}' was not found"
        }), 404

    # Security check: Rural doctors can only view their clinic's reports
    user = request.current_user
    if user.role == 'rural_doctor' and report.clinic_name != user.organization and report.created_by_user_id != user.user_id:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have authorization to view reports from other clinics'
        }), 403

    return jsonify({
        'success': True,
        'report': report.to_dict(include_logs=True)
    }), 200


@reports_bp.route('/<report_id>/status', methods=['PATCH'])
@login_required
def update_report_status(report_id):
    """
    Update the status of a report in the lifecycle:
    Created -> Queued -> Sent -> Received -> Under Review -> Responded -> Failed
    """
    start_time = time.time()
    report = Report.query.get(report_id)
    if not report:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': f"Report with ID '{report_id}' was not found"
        }), 404

    user = request.current_user
    data = request.get_json(silent=True) or request.form.to_dict()
    new_status = data.get('status')

    if not new_status or new_status not in VALID_STATUSES:
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': f"Invalid status: '{new_status}'. Allowed values: {', '.join(VALID_STATUSES)}"
        }), 400

    old_status = report.status
    report.status = new_status
    report.updated_at = datetime.utcnow()

    rtt = round((time.time() - start_time) * 1000, 2)
    log = TransmissionLog(
        report_id=report.report_id,
        event_type='STATUS_TRANSITION',
        http_method='PATCH',
        endpoint=f"/api/reports/{report_id}/status",
        status_code=200,
        round_trip_ms=rtt,
        client_ip=request.remote_addr,
        details=f"Status changed from [{old_status}] to [{new_status}] by {user.name} ({user.role})"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Report status updated to '{new_status}'",
        'report_id': report.report_id,
        'old_status': old_status,
        'new_status': new_status
    }), 200


@reports_bp.route('/<report_id>/response', methods=['POST'])
@login_required
@role_required('hospital_doctor', 'admin')
def add_hospital_response(report_id):
    """
    City Hospital doctor reviews report and transmits medical advice back to rural clinic.
    Transitions status to 'Responded'.
    """
    start_time = time.time()
    report = Report.query.get(report_id)
    if not report:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': f"Report with ID '{report_id}' was not found"
        }), 404

    user = request.current_user
    data = request.get_json(silent=True) or request.form.to_dict()

    if not data or 'clinical_assessment' not in data or 'prescription_advice' not in data:
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'Both clinical_assessment and prescription_advice are required'
        }), 400

    urgency_directive = data.get('urgency_directive', 'Proceed with Local Care')
    department = data.get('department', 'General Medicine')

    response_entry = HospitalResponse(
        report_id=report.report_id,
        doctor_id=user.user_id,
        doctor_name=user.name,
        hospital_name=user.organization,
        department=department,
        clinical_assessment=data['clinical_assessment'].strip(),
        prescription_advice=data['prescription_advice'].strip(),
        urgency_directive=urgency_directive
    )
    
    # Update report status to Responded
    report.status = 'Responded'
    report.updated_at = datetime.utcnow()
    
    db.session.add(response_entry)

    rtt = round((time.time() - start_time) * 1000, 2)
    log = TransmissionLog(
        report_id=report.report_id,
        event_type='HOSPITAL_RESPONSE_DISPATCHED',
        http_method='POST',
        endpoint=f"/api/reports/{report_id}/response",
        status_code=201,
        round_trip_ms=rtt,
        client_ip=request.remote_addr,
        details=f"City hospital response dispatched by {user.name} ({department}). Directive: {urgency_directive}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Hospital consultation response successfully transmitted to rural clinic',
        'response': response_entry.to_dict(),
        'report_status': report.status
    }), 201


@reports_bp.route('/<report_id>/ack', methods=['POST'])
@login_required
def acknowledge_report(report_id):
    """
    Explicit Server Acknowledgement (ACK) Endpoint.
    Used in reliable transport protocols to confirm packet receipt.
    """
    report = Report.query.get(report_id)
    if not report:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'Report not found'
        }), 404

    user = request.current_user
    
    if not report.ack_token:
        report.ack_token = generate_ack_token(report.report_id)
        db.session.commit()

    log = TransmissionLog(
        report_id=report.report_id,
        event_type='MANUAL_ACK_REQUESTED',
        http_method='POST',
        endpoint=f"/api/reports/{report_id}/ack",
        status_code=200,
        client_ip=request.remote_addr,
        ack_token=report.ack_token,
        details=f"Explicit ACK requested by {user.name}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'report_id': report.report_id,
        'ack_token': report.ack_token,
        'sha256_checksum': report.sha256_checksum,
        'status': report.status,
        'server_timestamp': datetime.utcnow().isoformat(),
        'protocol_confirmation': 'TCP_ACK_VERIFIED'
    }), 200


@reports_bp.route('/<report_id>/upload', methods=['POST'])
@login_required
def upload_report_pdf(report_id):
    """
    Dedicated endpoint for uploading or updating the PDF attachment of a report.
    Validates file format, calculates cryptographic checksum, and stores securely.
    """
    report = Report.query.get(report_id)
    if not report:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'Report not found'
        }), 404

    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'No file uploaded under key "file"'
        }), 400

    uploaded_file = request.files['file']
    if not allowed_file(uploaded_file.filename):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'Only PDF files are permitted'
        }), 400

    file_bytes = uploaded_file.read()
    if not file_bytes.startswith(b'%PDF'):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'File is corrupted or not a valid PDF'
        }), 400

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    
    clean_name = clean_filename(uploaded_file.filename, report.report_id)
    file_path = os.path.join(upload_dir, clean_name)
    
    with open(file_path, 'wb') as f:
        f.write(file_bytes)

    report.pdf_filename = clean_name
    report.pdf_path = file_path
    report.pdf_size_bytes = len(file_bytes)
    report.sha256_checksum = compute_sha256(file_bytes)
    report.updated_at = datetime.utcnow()

    log = TransmissionLog(
        report_id=report.report_id,
        event_type='PDF_UPLOADED',
        http_method='POST',
        endpoint=f"/api/reports/{report_id}/upload",
        status_code=200,
        client_ip=request.remote_addr,
        payload_checksum=report.sha256_checksum,
        details=f"Uploaded {clean_name} ({report.pdf_size_bytes} bytes). SHA-256: {report.sha256_checksum}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'PDF attachment successfully uploaded and verified',
        'report_id': report.report_id,
        'pdf_filename': clean_name,
        'pdf_size_bytes': report.pdf_size_bytes,
        'sha256_checksum': report.sha256_checksum
    }), 200


@reports_bp.route('/<report_id>/download', methods=['GET'])
@login_required
def download_report_pdf(report_id):
    """
    Secure PDF Download Endpoint.
    Validates user authentication, sets proper security headers, and verifies file integrity.
    """
    report = Report.query.get(report_id)
    if not report or not report.pdf_path or not os.path.isfile(report.pdf_path):
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'No PDF attachment found for this report'
        }), 404

    user = request.current_user
    
    # Role-based restriction: rural doctor can only download their own clinic's reports
    if user.role == 'rural_doctor' and report.clinic_name != user.organization and report.created_by_user_id != user.user_id:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'Unauthorized to download reports from other clinics'
        }), 403

    log = TransmissionLog(
        report_id=report.report_id,
        event_type='PDF_DOWNLOADED',
        http_method='GET',
        endpoint=f"/api/reports/{report_id}/download",
        status_code=200,
        client_ip=request.remote_addr,
        payload_checksum=report.sha256_checksum,
        details=f"PDF downloaded by {user.name} ({user.role})"
    )
    db.session.add(log)
    db.session.commit()

    # Stream the PDF with appropriate security & data communication headers
    response = send_file(
        report.pdf_path,
        mimetype='application/pdf',
        as_attachment=False,  # Display inline in browser viewer
        download_name=report.pdf_filename
    )
    response.headers['X-RuralLink-Report-ID'] = report.report_id
    response.headers['X-RuralLink-SHA256'] = report.sha256_checksum or 'UNKNOWN'
    response.headers['X-RuralLink-ACK'] = report.ack_token or 'NONE'
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return response


@reports_bp.route('/<report_id>/network-trace', methods=['GET'])
@login_required
def get_report_network_trace(report_id):
    """
    Data Communication Academic Feature:
    Returns the complete packet-level transmission trace and timeline for this report.
    Perfect for viva demonstration and Wireshark comparison!
    """
    report = Report.query.get(report_id)
    if not report:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'Report not found'
        }), 404

    logs = TransmissionLog.query.filter_by(report_id=report_id).order_by(TransmissionLog.created_at.asc()).all()
    
    trace_events = []
    for log in logs:
        trace_events.append({
            'timestamp': log.created_at.isoformat() if log.created_at else None,
            'event': log.event_type,
            'method': log.http_method,
            'endpoint': log.endpoint,
            'status_code': log.status_code,
            'rtt_ms': log.round_trip_ms,
            'client_ip': log.client_ip,
            'checksum': log.payload_checksum,
            'ack_token': log.ack_token,
            'details': log.details
        })

    return jsonify({
        'success': True,
        'report_id': report.report_id,
        'patient_name': report.patient_name,
        'status': report.status,
        'idempotency_key': report.idempotency_key,
        'sha256_checksum': report.sha256_checksum,
        'ack_token': report.ack_token,
        'trace_length': len(trace_events),
        'timeline': trace_events,
        'wireshark_filter': f'http contains "{report.report_id}" || http contains "{report.ack_token or ""}"'
    }), 200
