from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat()
        }

class ScheduleCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    race_date = db.Column(db.String, nullable=False)
    training_distance = db.Column(db.String, nullable=False)
    race_phase = db.Column(db.String, nullable=False)
    current_mileage = db.Column(db.Float, nullable=False)
    run_days = db.Column(db.Integer, nullable=False)
    long_run_day = db.Column(db.String, nullable=False)
    experience_level = db.Column(db.String, nullable=True)
    training_goal = db.Column(db.String, nullable=True)
    schedule_json = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# New models for the enhanced functionality

class GarminDataCache(db.Model):
    """Short-term cache for API performance optimization."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)  # 'sleep', 'training_readiness', etc.
    data_date = db.Column(db.Date, nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'data_type', 'data_date', name='cache_constraint'),)

class GarminDataArchive(db.Model):
    """Long-term storage for ML data analysis."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)  # 'sleep', 'activity', etc.
    data_date = db.Column(db.Date, nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'data_type', 'data_date', name='archive_constraint'),)

class Activity(db.Model):
    """Storage for running activity data."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    garmin_activity_id = db.Column(db.String(50), nullable=False, unique=True)
    activity_type = db.Column(db.String(50))
    activity_date = db.Column(db.DateTime, nullable=False)
    distance = db.Column(db.Float)  # in meters
    duration = db.Column(db.Integer)  # in seconds
    avg_hr = db.Column(db.Integer)
    max_hr = db.Column(db.Integer)
    avg_pace = db.Column(db.Float)  # in seconds per meter
    calories = db.Column(db.Integer)
    training_effect_aerobic = db.Column(db.Float)
    training_effect_anaerobic = db.Column(db.Float)
    details_json = db.Column(db.Text)  # Store full details for ML processing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('activities', lazy=True))

class UserPerformanceMetrics(db.Model):
    """Extracted performance metrics for ML analysis."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # VO2max and race predictions
    vo2max = db.Column(db.Float)
    race_prediction_5k = db.Column(db.Integer)  # seconds
    race_prediction_10k = db.Column(db.Integer)  # seconds
    race_prediction_half = db.Column(db.Integer)  # seconds
    race_prediction_full = db.Column(db.Integer)  # seconds
    
    # Daily stress and recovery metrics
    avg_stress = db.Column(db.Float)
    max_stress = db.Column(db.Float)
    resting_heart_rate = db.Column(db.Integer)
    sleep_score = db.Column(db.Float)
    body_battery_change = db.Column(db.Integer)
    overnight_hrv = db.Column(db.Float)
    training_readiness = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('performance_metrics', lazy=True))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='user_date_metrics_constraint'),)

class MLModel(db.Model):
    """Storage for trained ML models."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # 'recovery_predictor', 'race_predictor', etc.
    model_version = db.Column(db.Integer, default=1)
    model_file_path = db.Column(db.String(255), nullable=False)
    accuracy_score = db.Column(db.Float)
    training_data_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('ml_models', lazy=True))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'model_type', 'model_version', name='model_constraint'),)