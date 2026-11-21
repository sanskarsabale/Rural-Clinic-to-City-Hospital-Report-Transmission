from functools import wraps
from datetime import datetime, timedelta
import jwt
from flask import request, jsonify, session, current_app
from models import User

def generate_token(user):
    """Generate JWT Token with user details and expiry"""
    payload = {
        'user_id': user.user_id,
        'email': user.email,
        'role': user.role,
        'organization': user.organization,
        'name': user.name,
        'exp': datetime.utcnow() + current_app.config['JWT_EXPIRATION_DELTA'],
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    """Decode and validate JWT Token"""
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def get_current_user():
    """Extract user from Authorization Bearer header or Flask session"""
    auth_header = request.headers.get('Authorization')
    token = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
    elif 'token' in session:
        token = session['token']
        
    if token:
        payload = decode_token(token)
        if payload:
            return User.query.get(payload.get('user_id'))
            
    # Fallback to session user_id
    if 'user_id' in session:
        return User.query.get(session['user_id'])
        
    return None

def login_required(f):
    """Decorator to enforce authenticated requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Valid authentication token or active session is required'
            }), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to enforce role-based access control (RBAC)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Authentication required'
                }), 401
            if user.role not in allowed_roles:
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': f'Access forbidden for role: {user.role}. Required roles: {", ".join(allowed_roles)}'
                }), 403
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator
