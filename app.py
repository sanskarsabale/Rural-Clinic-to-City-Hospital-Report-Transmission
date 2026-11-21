import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from config import config_by_name
from models import db, User, Report
from routes.auth import auth_bp
from routes.reports import reports_bp
from routes.network_lab import network_lab_bp
from utils.auth import get_current_user

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))
    app.config['BASE_DIR'] = os.path.abspath(os.path.dirname(__file__))

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(network_lab_bp)

    # Global Response Headers for Data Communication Demonstrations
    @app.after_request
    def add_data_comm_headers(response):
        response.headers['X-RuralLink-Version'] = '2.0.0-academic-btech'
        response.headers['X-DataComm-Transport'] = 'TCP/IP'
        response.headers['X-DataComm-App-Layer'] = 'HTTP/1.1 REST'
        response.headers['X-Server-Time'] = datetime.utcnow().isoformat() + 'Z'
        return response

    # Frontend Page Routes
    @app.route('/')
    def index():
        user = get_current_user()
        return render_template('index.html', user=user)

    @app.route('/login')
    def login_page():
        user = get_current_user()
        if user:
            if user.role == 'rural_doctor':
                return redirect(url_for('clinic_portal'))
            elif user.role == 'hospital_doctor':
                return redirect(url_for('hospital_portal'))
        return render_template('login.html')

    @app.route('/clinic')
    def clinic_portal():
        user = get_current_user()
        if not user:
            return redirect(url_for('login_page', next='/clinic'))
        if user.role not in ['rural_doctor', 'admin']:
            return redirect(url_for('hospital_portal'))
        return render_template('clinic.html', user=user)

    @app.route('/hospital')
    def hospital_portal():
        user = get_current_user()
        if not user:
            return redirect(url_for('login_page', next='/hospital'))
        if user.role not in ['hospital_doctor', 'admin']:
            return redirect(url_for('clinic_portal'))
        return render_template('hospital.html', user=user)

    @app.route('/network-lab')
    def network_lab_portal():
        user = get_current_user()
        return render_template('network_lab.html', user=user)

    # Custom Error Handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Bad Request', 'message': str(e)}), 400
        return render_template('index.html', error='Bad Request'), 400

    @app.errorhandler(401)
    def unauthorized_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Unauthorized', 'message': 'Authentication required'}), 401
        return redirect(url_for('login_page', next=request.path))

    @app.errorhandler(403)
    def forbidden_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Forbidden', 'message': 'Permission denied'}), 403
        return render_template('index.html', error='Access Forbidden'), 403

    @app.errorhandler(404)
    def not_found_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Not Found', 'message': 'Requested resource was not found'}), 404
        return render_template('index.html', error='Page Not Found'), 404

    @app.errorhandler(409)
    def conflict_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Conflict', 'message': 'Conflict or duplicate request detected'}), 409
        return render_template('index.html', error='Conflict'), 409

    @app.errorhandler(413)
    def payload_too_large_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Payload Too Large', 'message': 'PDF file exceeds 16MB limit'}), 413
        return render_template('index.html', error='File size exceeds limit (Max 16MB)'), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Internal Server Error', 'message': 'An unexpected server error occurred'}), 500
        return render_template('index.html', error='Internal Server Error'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        # Auto seed if no users exist
        if not User.query.first():
            print("Auto-seeding initial database...")
            from seed_data import seed_database
            seed_database()
            
    port = int(os.environ.get('PORT', 5000))
    print(f"===============================================================")
    print(f" RuralLink Server Online at http://127.0.0.1:{port}")
    print(f" Portal A (Rural Clinic) : http://127.0.0.1:{port}/clinic")
    print(f" Portal B (City Hospital): http://127.0.0.1:{port}/hospital")
    print(f" Data Comm Lab & Wireshark: http://127.0.0.1:{port}/network-lab")
    print(f"===============================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
