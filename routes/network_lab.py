import time
import os
from flask import Blueprint, request, jsonify, current_app, send_file
from models import db, Report, TransmissionLog, IdempotencyRecord, User
from utils.auth import login_required

network_lab_bp = Blueprint('network_lab', __name__, url_prefix='/api/network-lab')

@network_lab_bp.route('/stats', methods=['GET'])
def get_lab_stats():
    """
    Overview Data Communication metrics for dashboards & lab analysis.
    """
    total_reports = Report.query.count()
    status_counts = {
        'Received': Report.query.filter_by(status='Received').count(),
        'Under Review': Report.query.filter_by(status='Under Review').count(),
        'Responded': Report.query.filter_by(status='Responded').count(),
        'Queued': Report.query.filter_by(status='Queued').count(),
        'Failed': Report.query.filter_by(status='Failed').count(),
    }
    
    total_logs = TransmissionLog.query.count()
    duplicates_blocked = TransmissionLog.query.filter_by(event_type='DUPLICATE_BLOCKED').count()
    acks_issued = TransmissionLog.query.filter(TransmissionLog.ack_token != None).count()
    
    # Calculate average round-trip time (RTT)
    logs_with_rtt = TransmissionLog.query.filter(TransmissionLog.round_trip_ms != None).all()
    avg_rtt = round(sum(l.round_trip_ms for l in logs_with_rtt) / len(logs_with_rtt), 2) if logs_with_rtt else 0.0

    return jsonify({
        'success': True,
        'metrics': {
            'total_reports': total_reports,
            'status_distribution': status_counts,
            'transmission_logs_count': total_logs,
            'duplicates_prevented': duplicates_blocked,
            'server_acks_issued': acks_issued,
            'average_rtt_ms': avg_rtt,
            'protocol_stack': {
                'application': 'HTTP/1.1 REST (JSON & multipart/form-data)',
                'transport': 'TCP (Reliable, Ordered, Flow-Controlled)',
                'network': 'IPv4 / IPv6',
                'security': 'SHA-256 Hashes, Idempotency-Key Headers, JWT Bearer'
            }
        }
    }), 200


@network_lab_bp.route('/simulate-fault', methods=['POST'])
def simulate_fault():
    """
    Simulate network failures (503 Service Unavailable, 504 Timeout, or Delay)
    Enables live demonstration of client exponential backoff and offline queueing.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    fault_type = data.get('fault_type', 'drop')
    delay_seconds = float(data.get('delay_seconds', 2.0))

    if fault_type == 'delay':
        time.sleep(min(delay_seconds, 10.0))
        return jsonify({
            'success': True,
            'message': f"Simulated network latency of {delay_seconds} seconds injected successfully",
            'simulated_latency_ms': delay_seconds * 1000
        }), 200
        
    elif fault_type == 'timeout':
        return jsonify({
            'success': False,
            'error': 'Gateway Timeout (Simulated)',
            'code': 504,
            'message': 'Simulated TCP transmission timeout between rural edge and hospital core.'
        }), 504
        
    elif fault_type == 'drop':
        return jsonify({
            'success': False,
            'error': 'Service Unavailable (Simulated Packet Loss)',
            'code': 503,
            'message': 'Simulated link disruption: Server cannot receive packet. Client should enqueue and retry with exponential backoff.'
        }), 503

    return jsonify({'success': False, 'message': 'Unknown fault type'}), 400


@network_lab_bp.route('/wireshark-filters', methods=['GET'])
def get_wireshark_filters():
    """
    Wireshark Packet Analysis Reference & Filters Cheat Sheet
    """
    filters = [
        {
            'name': 'Filter RuralLink HTTP Traffic',
            'filter': 'http && tcp.port == 5000',
            'description': 'Captures all HTTP requests and responses between the browser and the Flask backend on port 5000.'
        },
        {
            'name': 'Filter Report Submissions (POST)',
            'filter': 'http.request.method == "POST" && http.request.uri contains "/api/reports"',
            'description': 'Isolates the actual transmission packet containing the patient metadata and multipart PDF payload.'
        },
        {
            'name': 'Filter Server Acknowledgements (201 Created)',
            'filter': 'http.response.code == 201',
            'description': 'Shows the Server ACK packet containing the SHA-256 checksum and ACK token returned to the rural clinic.'
        },
        {
            'name': 'Filter Duplicate Prevention (409 Conflict)',
            'filter': 'http.response.code == 409',
            'description': 'Captures the rejection packet when a duplicate Idempotency-Key is detected over the transport layer.'
        },
        {
            'name': 'Inspect TCP 3-Way Handshake',
            'filter': 'tcp.flags.syn == 1 && tcp.port == 5000',
            'description': 'Identifies SYN and SYN-ACK packets initiating the TCP connection before HTTP/REST data transfer.'
        },
        {
            'name': 'Filter Hospital Tele-Medicine Responses',
            'filter': 'http.request.uri contains "/response"',
            'description': 'Shows doctor advice transmission flowing from City Hospital back to Rural Clinic.'
        }
    ]

    return jsonify({
        'success': True,
        'capture_interface': 'Loopback Adapter (127.0.0.1) for local development, Ethernet/Wi-Fi for network testing',
        'filters': filters
    }), 200


@network_lab_bp.route('/export-postman', methods=['GET'])
def export_postman():
    """Download the pre-built Postman collection for live API testing"""
    filepath = os.path.join(current_app.config['BASE_DIR'], 'RuralLink.postman_collection.json')
    if os.path.isfile(filepath):
        return send_file(
            filepath,
            mimetype='application/json',
            as_attachment=True,
            download_name='RuralLink.postman_collection.json'
        )
    return jsonify({'success': False, 'message': 'Postman collection file not found'}), 404
