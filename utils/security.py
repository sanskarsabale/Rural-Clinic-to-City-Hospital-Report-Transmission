import hashlib
import os
import secrets
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Validate if file extension is an allowed PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compute_sha256(data_or_path):
    """
    Computes a SHA-256 cryptographic hash.
    Accepts raw bytes, string, or file path.
    Essential for Data Communication data integrity verification.
    """
    hasher = hashlib.sha256()
    if isinstance(data_or_path, str):
        if os.path.isfile(data_or_path):
            with open(data_or_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        else:
            hasher.update(data_or_path.encode('utf-8'))
    elif isinstance(data_or_path, bytes):
        hasher.update(data_or_path)
    return hasher.hexdigest()

def generate_ack_token(report_id):
    """Generates a cryptographic acknowledgement token for verified receipt"""
    random_bytes = secrets.token_hex(8)
    token_source = f"ACK:{report_id}:{random_bytes}"
    return hashlib.sha256(token_source.encode('utf-8')).hexdigest()[:32]

def clean_filename(filename, report_id):
    """Sanitize and prefix filename with report ID for secure uniqueness"""
    base_clean = secure_filename(filename)
    if not base_clean.lower().endswith('.pdf'):
        base_clean += '.pdf'
    return f"{report_id}_{base_clean}"
