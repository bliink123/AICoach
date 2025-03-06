import os
import threading
import time
from datetime import timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import models
from models import db, User, Feedback

# Import modules
from auth import auth, init_auth
from garmin_data import init_api, update_all_users_data, cleanup_old_cache
from ai_coach import ai_coach_bp
from schedule import schedule_bp
from ml import ml_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "your-default-secret-key")
    
    # Configure session
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True when we deploy
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_TYPE'] = 'filesystem'
    
    # Configure CORS
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:3000"}})

    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_cache.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Initialize modules
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = None  # Disable default redirection
    app.login_manager = login_manager
    
    # Initialize authentication
    app.register_blueprint(auth)
    init_auth(app)
    
    # Register blueprints
    app.register_blueprint(ai_coach_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(ml_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    # Feedback endpoint
    @app.route('/api/feedback', methods=['POST'])
    def post_feedback():
        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({"error": "Rating is required"}), 400
        try:
            feedback = Feedback(
                rating=data['rating'],
                comment=data.get('comment')
            )
            db.session.add(feedback)
            db.session.commit()
            return jsonify({"message": "Feedback submitted successfully", "feedback": feedback.to_dict()}), 201
        except Exception as e:
            logger.error("Error saving feedback: %s", e)
            db.session.rollback()
            return jsonify({"error": "Failed to save feedback"}), 500

    @app.route('/api/feedback', methods=['GET'])
    def get_feedback():
        try:
            all_feedback = Feedback.query.all()
            return jsonify([fb.to_dict() for fb in all_feedback])
        except Exception as e:
            logger.error("Error fetching feedback: %s", e)
            return jsonify({"error": "Failed to retrieve feedback"}), 500

    @app.route('/', methods=['GET'])
    def index():
        return jsonify({"message": "Welcome to the AICOACH API. Use /api/overall-sleep, /api/ai-coach, /api/schedule, or /api/feedback, or the new ML endpoints."})

    return app

def setup_scheduled_tasks(app):
    """Set up scheduled tasks for data fetching and model training."""
    
    def run_daily_tasks():
        while True:
            with app.app_context():
                try:
                    # Update data for all users
                    update_all_users_data(app.garmin_client)
                    
                    # Clean up old cache entries
                    cleanup_old_cache()
                    
                    # Train models for users with new data
                    from ml import train_recovery_model, train_race_prediction_model, export_user_data_for_ml
                    active_users = User.query.filter_by(is_active=True).all()
                    for user in active_users:
                        try:
                            # Only train if we have enough data
                            data = export_user_data_for_ml(user.id)
                            if len(data['activities']) >= 20:
                                train_recovery_model(user.id)
                            
                            if len(data['activities']) >= 30:
                                train_race_prediction_model(user.id)
                        except Exception as e:
                            logger.error(f"Error training models for user {user.id}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error in scheduled tasks: {e}")
                
                logger.info("Daily scheduled tasks completed")
                
            # Sleep for 24 hours
            time.sleep(24 * 60 * 60)
    
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_daily_tasks)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logger.info("Scheduled tasks initialized")

def update_activity_paces():
    """Update missing pace values for existing activities."""
    activities_without_pace = Activity.query.filter(Activity.avg_pace.is_(None)).all()
    
    logger.info(f"Found {len(activities_without_pace)} activities without pace")
    
    updated_count = 0
    for activity in activities_without_pace:
        if activity.distance and activity.duration and activity.distance > 0:
            activity.avg_pace = activity.duration / activity.distance
            updated_count += 1
    
    db.session.commit()
    logger.info(f"Updated pace for {updated_count} activities")

# Call this function once to update existing activities
# Add this to app.py or create a maintenance endpoint

# Create the application
app = create_app()

# Initialize Garmin API client
GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)
app.garmin_client = garmin_client

# Setup scheduled tasks
if not app.debug:
    setup_scheduled_tasks(app)

if __name__ == '__main__':
    app.run(debug=True, port=8080, host="localhost")