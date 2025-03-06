import logging
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from models import User, db

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'email' not in data or 'password' not in data:
        response = jsonify({"error": "Missing required fields"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400
    
    if User.query.filter(or_(User.username == data['username'], User.email == data['email'])).first():
        response = jsonify({"error": "User already exists"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400
    
    try:
        new_user = User(username=data['username'], email=data['email'])
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        logger.error("Registration error: %s", e)
        response = jsonify({"error": "Registration failed"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
    
    response = jsonify({"message": "User registered successfully"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, 201

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        # Make the session permanent
        session.permanent = True
        login_user(user, remember=True)
        return jsonify({"id": user.id, "username": user.username, "email": user.email}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)  # Remove user ID from the session
    return jsonify({"message": "Logged out successfully"}), 200

@auth.route('/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    })

def init_auth(app):
    login_manager = app.login_manager
    
    @login_manager.user_loader
    def load_user(user_id):
        logger.info(f"load_user called with user_id: {user_id}")
        try:
            user_id = int(user_id)
            user = User.query.get(user_id)
            if user:
                logger.info(f"User found: {user.username}")
            else:
                logger.info("User not found")
            return user
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid user_id: {user_id} - {e}")
            return None  # Handle the case where user_id is invalid

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Unauthorized access"}), 401
    
    return app