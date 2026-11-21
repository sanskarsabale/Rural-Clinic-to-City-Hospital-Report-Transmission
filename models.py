import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """User Model representing Rural Clinic Doctors and City Hospital Doctors"""
    __tablename__ = 'users'

    user_id = db.Column(db.String(36), primary_key=True, default=lambda: f"usr_{uuid.uuid4().hex[:12]}")
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # 'rural_doctor', 'hospital_doctor', 'admin'
    organization = db.Column(db.String(150), nullable=False)  # Clinic or Hospital Name
    license_number = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_reports = db.relationship('Report', backref='author', lazy=True)
    hospital_responses = db.relationship('HospitalResponse', backref='doctor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'organization': self.organization,
            'license_number': self.license_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Report(db.Model):
    """Patient Medical Report transmitted from Rural Clinic to City Hospital"""
    __tablename__ = 'reports'

    report_id = db.Column(db.String(36), primary_key=True, default=lambda: f"RPT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    patient_id = db.Column(db.String(50), nullable=False, index=True)
    patient_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(15), nullable=False)  # 'Male', 'Female', 'Other'
    symptoms = db.Column(db.Text, nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='Normal')  # 'Low', 'Normal', 'Urgent', 'Critical Emergency'
    additional_notes = db.Column(db.Text, nullable=True)
    
    # File Attachment Metadata
    pdf_filename = db.Column(db.String(255), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)
    pdf_size_bytes = db.Column(db.Integer, nullable=True, default=0)
    sha256_checksum = db.Column(db.String(64), nullable=True)  # Integrity verification

    # Status Lifecycle: Created -> Queued -> Sent -> Received -> Under Review -> Responded -> Failed
    status = db.Column(db.String(30), nullable=False, default='Created')
    
    # Data Communication Reliability Mechanism
    idempotency_key = db.Column(db.String(100), unique=True, nullable=True, index=True)
    ack_token = db.Column(db.String(64), nullable=True)
    
    # Sender details
    created_by_user_id = db.Column(db.String(36), db.ForeignKey('users.user_id'), nullable=False)
    clinic_name = db.Column(db.String(150), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    received_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    responses = db.relationship('HospitalResponse', backref='report', lazy=True, cascade='all, delete-orphan')
    transmission_logs = db.relationship('TransmissionLog', backref='report', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_logs=False):
        data = {
            'report_id': self.report_id,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'age': self.age,
            'gender': self.gender,
            'symptoms': self.symptoms,
            'diagnosis': self.diagnosis,
            'priority': self.priority,
            'additional_notes': self.additional_notes,
            'pdf_filename': self.pdf_filename,
            'pdf_size_bytes': self.pdf_size_bytes,
            'has_pdf': bool(self.pdf_filename),
            'sha256_checksum': self.sha256_checksum,
            'status': self.status,
            'idempotency_key': self.idempotency_key,
            'ack_token': self.ack_token,
            'created_by_user_id': self.created_by_user_id,
            'author_name': self.author.name if self.author else 'Unknown Doctor',
            'clinic_name': self.clinic_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'responses_count': len(self.responses),
            'latest_response': self.responses[-1].to_dict() if self.responses else None
        }
        if include_logs:
            data['transmission_logs'] = [log.to_dict() for log in self.transmission_logs]
        return data


class HospitalResponse(db.Model):
    """Doctor Response from City Hospital back to Rural Clinic"""
    __tablename__ = 'hospital_responses'

    response_id = db.Column(db.String(36), primary_key=True, default=lambda: f"RES-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    report_id = db.Column(db.String(36), db.ForeignKey('reports.report_id'), nullable=False, index=True)
    doctor_id = db.Column(db.String(36), db.ForeignKey('users.user_id'), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    hospital_name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False, default='General Medicine')
    clinical_assessment = db.Column(db.Text, nullable=False)
    prescription_advice = db.Column(db.Text, nullable=False)
    urgency_directive = db.Column(db.String(50), nullable=False, default='Proceed with Local Care')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'response_id': self.response_id,
            'report_id': self.report_id,
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor_name,
            'hospital_name': self.hospital_name,
            'department': self.department,
            'clinical_assessment': self.clinical_assessment,
            'prescription_advice': self.prescription_advice,
            'urgency_directive': self.urgency_directive,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TransmissionLog(db.Model):
    """Audit Trail & Network Packet Logs for Academic Data Communication Analysis"""
    __tablename__ = 'transmission_logs'

    log_id = db.Column(db.String(36), primary_key=True, default=lambda: f"LOG-{uuid.uuid4().hex[:12]}")
    report_id = db.Column(db.String(36), db.ForeignKey('reports.report_id'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'CREATED', 'TRANSMITTED', 'ACK_ISSUED', 'INTEGRITY_CHECK', 'STATUS_CHANGE', 'RESPONSE_SENT'
    http_method = db.Column(db.String(10), nullable=True)
    endpoint = db.Column(db.String(150), nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    round_trip_ms = db.Column(db.Float, nullable=True)
    client_ip = db.Column(db.String(45), nullable=True)
    client_agent = db.Column(db.String(255), nullable=True)
    payload_checksum = db.Column(db.String(64), nullable=True)
    ack_token = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'report_id': self.report_id,
            'event_type': self.event_type,
            'http_method': self.http_method,
            'endpoint': self.endpoint,
            'status_code': self.status_code,
            'round_trip_ms': self.round_trip_ms,
            'client_ip': self.client_ip,
            'payload_checksum': self.payload_checksum,
            'ack_token': self.ack_token,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class IdempotencyRecord(db.Model):
    """Prevents duplicate transmissions by caching request hashes and responses"""
    __tablename__ = 'idempotency_records'

    idempotency_key = db.Column(db.String(100), primary_key=True)
    report_id = db.Column(db.String(36), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    response_status = db.Column(db.Integer, nullable=False)
    response_body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
