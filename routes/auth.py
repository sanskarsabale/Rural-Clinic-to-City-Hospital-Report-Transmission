import time
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from models import db, User, TransmissionLog
from utils.auth import generate_token, login_required, get_current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Doctor Authentication Endpoint
    Validates credentials, generates JWT token and session cookie.
    Logs authentication attempt in transmission audit log.
    """
    start_time = time.time()
    data = request.get_json(silent=True) or request.form.to_dict()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'Both email and password are required'
        }), 400

    email = data['email'].strip().lower()
    password = data['password']
    
    user = User.query.filter_by(email=email).first()
    
    # Calculate round trip execution time for DC demonstration
    rtt = round((time.time() - start_time) * 1000, 2)
    
    if not user or not user.check_password(password):
        # Log failed attempt
        log = TransmissionLog(
            event_type='AUTH_FAILURE',
            http_method='POST',
            endpoint='/api/auth/login',
            status_code=401,
            round_trip_ms=rtt,
            client_ip=request.remote_addr,
            client_agent=request.headers.get('User-Agent', '')[:250],
            details=f"Failed login attempt for email: {email}"
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Invalid email or password'
        }), 401

    # Issue JWT Token
    token = generate_token(user)
    
    # Set session for browser portal
    session['user_id'] = user.user_id
    session['role'] = user.role
    session['name'] = user.name
    session['organization'] = user.organization
    session['token'] = token
    session.permanent = True

    # Log successful authentication
    log = TransmissionLog(
        event_type='AUTH_SUCCESS',
        http_method='POST',
        endpoint='/api/auth/login',
        status_code=200,
        round_trip_ms=rtt,
        client_ip=request.remote_addr,
        client_agent=request.headers.get('User-Agent', '')[:250],
        details=f"Successful login: {user.name} ({user.role}) from {user.organization}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Welcome back, {user.name}",
        'token': token,
        'user': user.to_dict(),
        'network_metrics': {
            'rtt_ms': rtt,
            'transport_protocol': 'TCP/IP',
            'app_layer_protocol': 'HTTP/1.1 REST',
            'auth_mechanism': 'Bearer JWT (HMAC-SHA256)'
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Clear user session and invalidate local state"""
    user = get_current_user()
    user_name = user.name if user else 'Anonymous'
    
    session.clear()
    
    log = TransmissionLog(
        event_type='AUTH_LOGOUT',
        http_method='POST',
        endpoint='/api/auth/logout',
        status_code=200,
        client_ip=request.remote_addr,
        details=f"User {user_name} logged out"
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_profile():
    """Retrieve current authenticated doctor profile and permissions"""
    user = request.current_user
    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 200
