import os
import json
from datetime import date, timedelta, datetime
from flask import Flask, jsonify, request, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from garminconnect import Garmin
from dotenv import load_dotenv
import logging
from google import genai  # Gemini API client
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_login import LoginManager
from flask_login import login_user, logout_user, current_user, login_required



# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Set up token storage file path
TOKEN_STORE = os.path.expanduser("~/.garmin_tokens.json")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-default-secret-key")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  #Set to True when we depoly
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
CORS(app, supports_credentials=True)


# Configure SQLite database for caching and feedback
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_cache.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------------
# Database Models
# -------------------------
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

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Now that all models are defined, create the tables:
with app.app_context():
    db.create_all()

# -------------------------
# Authentication & API Initialization
# -------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None  # Disable default redirection

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

def get_credentials():
    email = input("Enter your Garmin email: ")
    password = input("Enter your Garmin password: ")
    return email, password

def get_mfa():
    return input("Enter MFA code: ")

def init_api(email=None, password=None):
    try:
        logger.info("Attempting token login using tokens from '%s'.", TOKEN_STORE)
        garmin = Garmin()  # Use tokens
        garmin.login(TOKEN_STORE)
    except Exception as err:
        logger.error("Token login failed: %s", err)
        print(f"Tokens not present or expired. Logging in with credentials. Tokens will be stored in '{TOKEN_STORE}'.")
        try:
            if not email or not password:
                email, password = get_credentials()
            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin.login()
            garmin.garth.dump(TOKEN_STORE)
            logger.info("Tokens stored in '%s'.", TOKEN_STORE)
        except Exception as err:
            logger.error("Credential login failed: %s", err)
            return None
    return garmin

# -------------------------
# Existing Helper Functions
# -------------------------
def get_training_readiness(date_str):
    try:
        training_data = garmin_client.get_training_readiness(date_str)
    except Exception as e:
        logger.error("Error fetching training readiness data: %s", e)
        training_data = None

    readiness = None
    if training_data:
        if isinstance(training_data, dict):
            readiness = training_data.get("score")
        elif isinstance(training_data, list):
            for record in training_data:
                if isinstance(record, dict):
                    readiness = record.get("score")
                    if readiness is not None:
                        break
    return readiness

def get_recovery_metrics(date_str):
    try:
        sleep_data = garmin_client.get_sleep_data(date_str)
    except Exception as e:
        logger.error("Error fetching sleep data: %s", e)
        sleep_data = None

    overall_value, avg_over_night_hrv, body_battery_change = None, None, None

    def extract_from_data(data):
        daily = data.get("dailySleepDTO", {})
        overall_val = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_hrv = daily.get("avgOvernightHrv") or data.get("avgOvernightHrv")
        battery = daily.get("bodyBatteryChange") or data.get("bodyBatteryChange")
        return overall_val, avg_hrv, battery

    if sleep_data:
        if isinstance(sleep_data, dict):
            overall_value, avg_over_night_hrv, body_battery_change = extract_from_data(sleep_data)
        elif isinstance(sleep_data, list):
            for record in sleep_data:
                if isinstance(record, dict):
                    overall_value, avg_over_night_hrv, body_battery_change = extract_from_data(record)
                    if overall_value is not None:
                        break

    training_readiness = get_training_readiness(date_str)
    return overall_value, avg_over_night_hrv, body_battery_change, training_readiness

def time_str_to_seconds(time_str):
    try:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    except Exception as e:
        logger.error("Error converting time string to seconds: %s", e)
        return None

def seconds_to_time_str(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def pace_str_to_minutes(pace_str):
    """
    Converts a pace string (mm:ss) to minutes (float).
    Example: "5:30" -> 5.5
    """
    try:
        if pace_str == "N/A":
            return None
        minutes, seconds = map(int, pace_str.split(':'))
        return minutes + (seconds / 60.0)
    except Exception as e:
        logger.error(f"Error parsing pace string: {pace_str} - {e}")
        return None

def calculate_running_paces(race_prediction_str, training_distance="5K"):
    """
    Given a race prediction for 5K as a string (e.g., "30:54"),
    calculate the base pace (seconds per km) and then compute:
      - Recovery Pace: base pace * 1.30
      - Easy Pace: base pace * 1.15
      - Threshold Pace: base pace * 1.04 (roughly base pace + ~15 seconds)
      - Long Run Pace: base pace * 1.20
    Returns a dictionary with paces in mm:ss per km format.
    """
    base_total_seconds = time_str_to_seconds(race_prediction_str)
    if base_total_seconds is None:
        return None

    distance_km = {"5K": 5, "10K": 10, "HalfMarathon": 21.1, "Marathon": 42.2}.get(training_distance, 5)
    base_pace = base_total_seconds / distance_km
    recovery_pace = base_pace * 1.30
    easy_pace = base_pace * 1.15
    threshold_pace = base_pace * 1.04
    long_run_pace = base_pace * 1.20

    return {
        "Recovery": seconds_to_time_str(recovery_pace),
        "Easy": seconds_to_time_str(easy_pace),
        "Threshold": seconds_to_time_str(threshold_pace),
        "LongRun": seconds_to_time_str(long_run_pace)
    }

def get_race_prediction(garmin_client, date_str, training_distance="5K"):
    """
    Retrieve race prediction data for the given date.
    Returns the 5K prediction as a mm:ss formatted string.
    """
    try:
        race_data = garmin_client.get_race_predictions()
        logger.info("Race prediction data: %s", json.dumps(race_data, indent=4))
    except Exception as e:
        logger.error("Error fetching race predictions: %s", e)
        race_data = None

    prediction_seconds = None
    if race_data:
        if isinstance(race_data, dict):
            if training_distance == "5K":
                prediction_seconds = race_data.get("time5K")
            elif training_distance == "10K":
                prediction_seconds = race_data.get("time10K")
            elif training_distance == "HalfMarathon":
                prediction_seconds = race_data.get("timeHalfMarathon")
            elif training_distance == "Marathon":
                prediction_seconds = race_data.get("timeMarathon")
        elif isinstance(race_data, list):
            for record in race_data:
                if isinstance(record, dict):
                    if training_distance == "5K" and record.get("time5K") is not None:
                        prediction_seconds = record.get("time5K")
                        break
                    elif training_distance == "10K" and record.get("time10K") is not None:
                        prediction_seconds = record.get("time10K")
                        break
                    elif training_distance == "HalfMarathon" and record.get("timeHalfMarathon") is not None:
                        prediction_seconds = record.get("timeHalfMarathon")
                        break
                    elif training_distance == "Marathon" and record.get("timeMarathon") is not None:
                        prediction_seconds = record.get("timeMarathon")
                        break
    if prediction_seconds is not None:
        return seconds_to_time_str(prediction_seconds)
    return None

# -------------------------
# Missing Helper Functions Definitions
# -------------------------
def determine_run_type(overall, avg_hrv, battery_change, readiness):
    """
    Determines run type based on recovery metrics.
    """
    if overall < 60 or avg_hrv < 50 or battery_change < 50 or (readiness is not None and readiness < 50):
        return "Recovery"
    elif overall > 80 and avg_hrv > 70 and battery_change > 70 and (readiness is not None and readiness > 70):
        return "Threshold"
    else:
        return "Easy"

def get_training_plan_length(training_distance, experience_level):
    """
    Returns recommended training plan length (in weeks) based on distance and experience level.
    """
    base_length = {"5K": 12, "10K": 16, "HalfMarathon": 20, "Marathon": 24}.get(training_distance, 16)
    experience_multiplier = {"beginner": 1.0, "intermediate": 1.0, "advanced": 0.9}.get(experience_level, 1.0)
    return round(base_length * experience_multiplier)

def generate_rest_day_details(rest_day_type):
    """
    Returns a detailed description for rest day activities.
    """
    if rest_day_type == "Active Recovery":
        return "Light activity such as walking, stretching, or easy cycling for 20-30 minutes."
    elif rest_day_type == "Strength Training":
        return "Running-specific strength exercises for 30-45 minutes."
    else:
        return "Complete rest day to allow full recovery."

def calculate_intensity_score(run_type, distance, pace_minutes):
    """
    Calculates an intensity score based on run type, distance, and pace.
    """
    if pace_minutes == "N/A" or pace_minutes is None:
        return 0
    intensity_factor = {"Recovery": 0.7, "Easy": 0.8, "Threshold": 1.0, "Intervals": 1.2, "LongRun": 0.85}.get(run_type, 0.8)
    return round(distance * intensity_factor * pace_minutes)

def determine_race_phase(weeks_until_race, training_distance):
    """
    Determines the race phase based on the weeks remaining until the race.
    - More than 10 weeks: "base" phase (building an aerobic foundation)
    - 6 to 10 weeks: "build" phase (gradually increasing quality and volume)
    - 3 to 5 weeks: "peak" phase (highest workload before taper)
    - Less than 3 weeks: "taper" phase (significantly reducing mileage for recovery)
    """
    if weeks_until_race > 10:
        return "base"
    elif 6 <= weeks_until_race <= 10:
        return "build"
    elif 3 <= weeks_until_race < 6:
        return "peak"
    else:
        return "taper"

def get_default_weekly_mileage(training_distance, experience_level, training_goal):
    """
    Returns the default weekly mileage (in km) based on the target race distance.
    These defaults are aligned with common training plans:
      - Marathon: ~50 km per week (typical for a beginner/intermediate)
      - Half Marathon: ~35 km per week
      - 10K: ~25 km per week
      - 5K: ~20 km per week
    These values may be further adjusted based on the runner's experience and training goal.
    """
    defaults = {
        "Marathon": 50,
        "Half Marathon": 35,
        "10K": 25,
        "5K": 20
    }
    return defaults.get(training_distance, 25)

def calculate_phase_multiplier(race_phase, current_week, total_weeks):
    """
    Calculates a multiplier for weekly mileage based on the current training phase:
      - Base Phase: Gradually increases from 0.8 up to ~1.0 by the end of the phase.
      - Build Phase: Slight increase in workload, reaching ~1.1 by the end.
      - Peak Phase: Maintains a high workload (e.g., multiplier of 1.1).
      - Taper Phase: Gradual reduction to approximately 60% of peak workload (multiplier ~0.6).
    """
    if race_phase == "base":
        return 0.8 + (0.2 * current_week / total_weeks)
    elif race_phase == "build":
        return 1.0 + (0.1 * current_week / total_weeks)
    elif race_phase == "peak":
        return 1.1
    elif race_phase == "taper":
        # Linear taper from 1.0 at the start of taper down to 0.6 at the end
        return 1.0 - (0.4 * (current_week / total_weeks))
    return 1.0

# -------------------------
# New Scheduling Helper Functions (Rule-Based, Phase-Aware)
# -------------------------
def get_run_days_simple(week_days, run_days, long_run_day):
    """Simple method to get a set of run days, ensuring long_run_day is included."""
    selected_run_days = []
    if long_run_day not in week_days:
        raise ValueError("long_run_day must be in week_days")
    selected_run_days.append(long_run_day)
    for day in week_days:
        if day != long_run_day and len(selected_run_days) < run_days:
            selected_run_days.append(day)
    return sorted(selected_run_days, key=lambda d: week_days.index(d))

def generate_workout_types_rule_based_phase_aware(race_phase, current_week, total_weeks, run_days, training_distance):
    """Generates workout types based on rules and race phase."""
    workout_rules_phase_aware = {
        "base": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Easy"],
            4: ["LongRun", "Easy", "Easy", "Easy"],
            5: ["LongRun", "Easy", "Easy", "Easy", "Easy"],
            6: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy"],
            7: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy", "Easy"],
        },
        "build": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Threshold"],
            4: ["LongRun", "Easy", "Easy", "Threshold"],
            5: ["LongRun", "Easy", "Easy", "Threshold", "Easy"],
            6: ["LongRun", "Easy", "Easy", "Threshold", "Easy", "Easy"],
            7: ["LongRun", "Easy", "Easy", "Threshold", "Easy", "Easy", "Easy"],
        },
        "peak": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Intervals"],
            4: ["LongRun", "Easy", "Intervals", "Threshold"],
            5: ["LongRun", "Easy", "Intervals", "Threshold", "Easy"],
            6: ["LongRun", "Easy", "Intervals", "Threshold", "Easy", "Recovery"],
            7: ["LongRun", "Easy", "Intervals", "Threshold", "Easy", "Recovery", "Easy"],
        },
        "taper": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Easy"],
            4: ["LongRun", "Easy", "Easy", "Easy"],
            5: ["LongRun", "Easy", "Easy", "Easy", "Easy"],
            6: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy"],
            7: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy", "Easy"],
        },
    }
    if race_phase in workout_rules_phase_aware and run_days in workout_rules_phase_aware[race_phase]:
        return workout_rules_phase_aware[race_phase][run_days]
    else:
        return ["Easy"] * run_days

def get_distance_factor(run_type, race_phase, current_week, total_weeks):
    base_factors = {"Recovery": 0.10, "Easy": 0.15, "Threshold": 0.12, "Intervals": 0.10, "LongRun": 0.25}
    factor = base_factors.get(run_type, 0.15)
    if run_type == "LongRun":
        if race_phase == "base":
            factor = 0.25 + (0.05 * current_week / (total_weeks * 0.3))
        elif race_phase == "build":
            factor = 0.30 - (0.02 * (current_week - (total_weeks * 0.3)) / (total_weeks * 0.5))
        elif race_phase == "peak":
            factor = 0.28
        elif race_phase == "taper":
            factor = 0.20 - (0.05 * (current_week - (total_weeks * 0.9)) / (total_weeks * 0.1))
    return factor

def generate_workout_details(run_type, race_phase, current_week, total_weeks, training_distance, distance):
    if run_type == "LongRun":
        if race_phase == "base":
            return f"Long run: {distance:.1f} km at an easy, conversational pace to build endurance."
        elif race_phase == "build":
            return f"Long run: {distance:.1f} km with the last 3-5 km at marathon pace."
        elif race_phase == "peak":
            if training_distance == "Marathon":
                return f"Long run: {distance:.1f} km with the middle {round(distance*0.5):.1f} km at race pace."
            else:
                return f"Long run: {distance:.1f} km with a progressive effort, finishing strong."
        else:
            return f"Shorter long run: {distance:.1f} km at an easy pace."
    elif run_type == "Recovery":
        return f"Recovery run: {distance:.1f} km at a very relaxed pace."
    elif run_type == "Easy":
        return f"Easy run: {distance:.1f} km at a comfortable, steady pace."
    elif run_type == "Threshold":
        if race_phase == "base":
            return f"Threshold: {distance:.1f} km including 2-3 x 5 min at threshold pace."
        elif race_phase == "build":
            return f"Threshold: {distance:.1f} km with 20 minutes at threshold pace."
        elif race_phase == "peak":
            return f"Threshold: {distance:.1f} km with 2 x 15 min at threshold pace."
        else:
            return f"Threshold: {distance:.1f} km with 10 minutes at threshold pace."
    elif run_type == "Intervals":
        if training_distance in ["5K", "10K"]:
            if race_phase == "base":
                return f"Intervals: {distance:.1f} km with 6-8 x 400m at 5K effort."
            elif race_phase == "build":
                return f"Intervals: {distance:.1f} km with 5-6 x 800m at 5K effort."
            elif race_phase == "peak":
                return f"Intervals: {distance:.1f} km with 5 x 1000m at 5K effort."
            else:
                return f"Intervals: {distance:.1f} km with 3-4 x 400m at 5K effort."
        else:
            if race_phase == "build":
                return f"Intervals: {distance:.1f} km with 6-8 x 400m at 10K effort."
            elif race_phase == "peak":
                return f"Intervals: {distance:.1f} km with 3-4 x 1 mile at 10K effort."
            else:
                return f"Intervals: {distance:.1f} km with 4-5 x 400m at 10K effort."
    return f"{run_type} run: {distance:.1f} km."

def improve_run_schedule_rule_based(workout_types, long_run_day, week_days, run_days):
    """
    Improves run schedule by assigning workout types to specific days.
    LongRun is always placed on long_run_day, and rest days are auto-assigned.
    """
    final_schedule = {}
    final_schedule[long_run_day] = "LongRun"
    print(f"Initial schedule with LongRun: {final_schedule}") # DEBUG

    rest_days_needed = 7 - run_days
    print(f"Rest days needed: {rest_days_needed}") # DEBUG
    available_days = [day for day in week_days if day != long_run_day]
    print(f"Available days for rest: {available_days}") # DEBUG
    rest_days = []
    if rest_days_needed >= 2:
        print("Trying to assign preferred rest days (Monday, Friday)") # DEBUG
        for preferred in ["Monday", "Friday"]:
            if preferred in available_days and len(rest_days) < rest_days_needed:
                rest_days.append(preferred)
                available_days.remove(preferred)
                print(f"  Assigned preferred rest day: {preferred}, rest_days: {rest_days}, available_days: {available_days}") # DEBUG
    print(f"Rest days after preferred assignment: {rest_days}") # DEBUG
    print(f"Available days after preferred assignment: {available_days}") # DEBUG

    while len(rest_days) < rest_days_needed and available_days:
        rest_days.append(available_days.pop())
        print(f"  Assigned remaining rest day: {rest_days[-1]}, rest_days: {rest_days}, available_days: {available_days}") # DEBUG
    print(f"Final rest days assigned: {rest_days}") # DEBUG

    for day in rest_days:
        final_schedule[day] = "Rest"
    print(f"Schedule after rest days: {final_schedule}") # DEBUG

    remaining_run_days = [day for day in week_days if day not in final_schedule]
    print(f"Remaining run days for workouts: {remaining_run_days}") # DEBUG
    workout_types_filtered = [wt for wt in workout_types if wt != "LongRun"]
    print(f"Workout types to assign (excluding LongRun): {workout_types_filtered}") # DEBUG
    for idx, day in enumerate(remaining_run_days):
        workout_type = "Easy" # Default if workouts run out
        if idx < len(workout_types_filtered):
            workout_type = workout_types_filtered[idx]
        final_schedule[day] = workout_type
        print(f"  Assigned workout {workout_type} to {day}") # DEBUG
    print(f"Final schedule: {final_schedule}") # DEBUG
    return final_schedule

# -------------------------
# Missing Functions Previously Defined
# -------------------------
# get_training_plan_length, generate_rest_day_details, calculate_intensity_score have been defined above.

# -------------------------
# API Endpoints
# -------------------------

# Create the /register endpoint:
@app.route('/register', methods=['POST'])
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

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user, remember=True)  # Persistent login using Flask-Login
        session['user_id'] = user.id # add this line back in
        return jsonify({"id": user.id, "username": user.username, "email": user.email}), 200 # return the user on success
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)  # Remove user ID from the session
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    })

@app.route('/api/overall-sleep', methods=['GET'])
@login_required
def overall_sleep():
    today_str = date.today().isoformat()
    overall_value, avg_over_night_hrv, body_battery_change, training_readiness = get_recovery_metrics(today_str)
    return jsonify({
        "overallSleepScore": overall_value,
        "avgOvernightHrv": avg_over_night_hrv,
        "bodyBatteryChange": body_battery_change,
        "trainingReadiness": training_readiness
    })

@app.route('/api/race-predictions', methods=['GET'])
@login_required
def race_predictions():
    try:
        race_data = garmin_client.get_race_predictions()
        logger.info("Race prediction data: %s", json.dumps(race_data, indent=4))
    except Exception as e:
        logger.error("Error fetching race predictions: %s", e)
        return jsonify({"error": "Failed to retrieve race predictions"}), 500

    output = {}
    def seconds_to_time_str_local(seconds):
        seconds = int(seconds)
        if seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}:{secs:02d}"
        else:
            hours = seconds // 3600
            remainder = seconds % 3600
            minutes = remainder // 60
            secs = remainder % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"

    if isinstance(race_data, dict):
        output["time5K"] = seconds_to_time_str_local(race_data.get("time5K")) if race_data.get("time5K") else "N/A"
        output["time10K"] = seconds_to_time_str_local(race_data.get("time10K")) if race_data.get("time10K") else "N/A"
        output["timeHalfMarathon"] = seconds_to_time_str_local(race_data.get("timeHalfMarathon")) if race_data.get("timeHalfMarathon") else "N/A"
        output["timeMarathon"] = seconds_to_time_str_local(race_data.get("timeMarathon")) if race_data.get("timeMarathon") else "N/A"
    elif isinstance(race_data, list):
        for record in race_data:
            if isinstance(record, dict) and record.get("time5K") is not None:
                output["time5K"] = seconds_to_time_str_local(record.get("time5K"))
                output["time10K"] = seconds_to_time_str_local(record.get("time10K")) if record.get("time10K") else "N/A"
                output["timeHalfMarathon"] = seconds_to_time_str_local(record.get("timeHalfMarathon")) if record.get("timeHalfMarathon") else "N/A"
                output["timeMarathon"] = seconds_to_time_str_local(record.get("timeMarathon")) if record.get("timeMarathon") else "N/A"
                break

    return jsonify(output)

@app.route('/api/ai-coach', methods=['GET'])
@login_required
def ai_coach():
    training_distance = request.args.get("distance", "5K")
    experience_level = request.args.get("experienceLevel", "intermediate").lower()
    training_goal = request.args.get("trainingGoal", "pr").lower()
    race_date = request.args.get("raceDate", date.today().isoformat())
    race_phase = request.args.get("racePhase", "auto").lower()
    today_str = date.today().isoformat()

    overall_value, avg_over_night_hrv, body_battery_change, training_readiness = get_recovery_metrics(today_str)
    race_prediction = get_race_prediction(garmin_client, today_str, training_distance)
    if any(v is None for v in [overall_value, avg_over_night_hrv, body_battery_change, training_readiness, race_prediction]):
        logger.error("Required data not found")
        return jsonify({"error": "Required data not found"}), 404

    try:
        race_date_obj = date.fromisoformat(race_date)
    except Exception as e:
        return jsonify({"error": "Invalid raceDate format. Use YYYY-MM-DD."}), 400
    weeks_until_race = max(0, (race_date_obj - date.today()).days // 7)
    total_weeks = get_training_plan_length(training_distance, experience_level)
    #current_week = max(1, total_weeks - weeks_until_race)
    current_week = 1
    default_mileage = get_default_weekly_mileage(training_distance, experience_level, training_goal)
    phase_multiplier = calculate_phase_multiplier(race_phase, current_week, total_weeks)
    weekly_mileage = default_mileage * phase_multiplier

    running_paces = calculate_running_paces(race_prediction, training_distance)
    run_type = determine_run_type(overall_value, avg_over_night_hrv, body_battery_change, training_readiness)
    target_pace = running_paces.get(run_type) if running_paces and run_type in running_paces else None

    base_pace_seconds = time_str_to_seconds(race_prediction) / {"5K": 5, "10K": 10, "HalfMarathon": 21.1, "Marathon": 42.2}.get(training_distance, 5)
    base_pace_str = seconds_to_time_str(base_pace_seconds)
    prompt = (
        f"You are a super fitness coach. My {training_distance} race prediction is {race_prediction} "
        f"(approximately {base_pace_str} per km). My recovery metrics are: overall sleep score {overall_value}, "
        f"average overnight HRV {avg_over_night_hrv}, body battery change {body_battery_change}, and training readiness {training_readiness}. "
        f"Additionally, I am looking for a recommendation for what my workout should be today, based on the recovery data you have. "
        f"I am in week {current_week} of a {total_weeks}-week training plan aimed at {training_goal} (experience level: {experience_level}). "
        f"My race phase is '{race_phase}', and my recommended weekly mileage is approximately {round(weekly_mileage,1)} km. "
        f"Based on this information, in 400 words, please recommend one run type (Recovery, Easy, Threshold, or Long Run) with the appropriate pace, duration, "
        f"and any adjustments to my training plan to improve performance while ensuring adequate recovery."
    )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_model = "gemini-2.0-flash-lite"
    gemini_client = genai.Client(api_key=gemini_api_key)

    try:
        response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=prompt
        )
        aiRecommendation = response.text
    except Exception as e:
        logger.error("Error calling Gemini API: %s", e)
        return jsonify({"error": "Failed to generate AI recommendation"}), 500

    return jsonify({
        "rulesBasedRunType": run_type,
        "rulesBasedTargetPace": target_pace,
        "rulesBasedRunningPaces": running_paces,
        "aiCoachRecommendation": aiRecommendation,
        "overallSleepScore": overall_value,
        "avgOvernightHrv": avg_over_night_hrv,
        "bodyBatteryChange": body_battery_change,
        "trainingReadiness": training_readiness,
        "racePrediction": race_prediction,
        "trainingDistance": training_distance,
        "periodization": {
            "racePhase": race_phase,
            "currentWeek": current_week,
            "totalWeeks": total_weeks,
            "recommendedWeeklyMileage": round(weekly_mileage,1)
        }
    })

@app.route('/api/schedule', methods=['POST'])
@login_required
def generate_schedule_endpoint():
    data = request.get_json()
    required_fields = ["runDays", "longRunDay", "trainingDistance", "raceDate", "racePhase"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "runDays, longRunDay, trainingDistance, raceDate, and racePhase are required"}), 400

    run_days = data.get("runDays")
    long_run_day = data.get("longRunDay").capitalize()
    training_distance = data.get("trainingDistance")
    race_date = data.get("raceDate")
    race_phase = data.get("racePhase").lower()
    current_mileage = data.get("currentMileage")
    experience_level = data.get("experienceLevel", "intermediate").lower()
    training_goal = data.get("trainingGoal", "pr").lower()

    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if long_run_day not in week_days:
        return jsonify({"error": f"Invalid longRunDay. Must be one of: {', '.join(week_days)}"}), 400

    today = date.today()
    try:
        race_date_obj = date.fromisoformat(race_date)
    except Exception as e:
        return jsonify({"error": "Invalid raceDate format. Use YYYY-MM-DD."}), 400
    weeks_until_race = max(0, (race_date_obj - today).days // 7)

    if race_phase == "auto":
        race_phase = determine_race_phase(weeks_until_race, training_distance)

    total_weeks = get_training_plan_length(training_distance, experience_level)
    current_week = max(1, total_weeks - weeks_until_race)
    default_mileage = get_default_weekly_mileage(training_distance, experience_level, training_goal)
    phase_multiplier = calculate_phase_multiplier(race_phase, current_week, total_weeks)
    cycle_multiplier = 1.0
    if current_week % 4 == 0:
        cycle_multiplier = 0.8
    elif current_week % 4 == 3:
        cycle_multiplier = 1.1
    weekly_mileage = current_mileage if current_mileage is not None else default_mileage * phase_multiplier * cycle_multiplier

    cached_schedule = ScheduleCache.query.filter_by(
        race_date=race_date,
        training_distance=training_distance,
        race_phase=race_phase,
        run_days=run_days,
        long_run_day=long_run_day,
        current_mileage=weekly_mileage,
        experience_level=experience_level,
        training_goal=training_goal
    ).order_by(ScheduleCache.timestamp.desc()).first()
    if cached_schedule and (datetime.utcnow() - cached_schedule.timestamp) < timedelta(hours=24):
        return jsonify(json.loads(cached_schedule.schedule_json))

    running_days = get_run_days_simple(week_days, run_days, long_run_day)
    today_str = today.isoformat()
    race_prediction = get_race_prediction(garmin_client, today_str, training_distance)
    if not race_prediction:
        return jsonify({"error": "Race prediction data not found"}), 404
    running_paces = calculate_running_paces(race_prediction, training_distance)
    workout_types = generate_workout_types_rule_based_phase_aware(race_phase, current_week, total_weeks, run_days, training_distance)
    final_schedule = improve_run_schedule_rule_based(workout_types, long_run_day, week_days, run_days)

    schedule = []
    for day in week_days:
        if day in final_schedule:
            run_type = final_schedule[day]
            if run_type in ["Recovery", "Easy", "Threshold", "Intervals", "LongRun", "Rest", "Active Recovery", "Strength Training"]:
                target_pace = running_paces.get(run_type, "N/A")
                pace_minutes = pace_str_to_minutes(target_pace) if target_pace != "N/A" else None
                distance_factor = get_distance_factor(run_type, race_phase, current_week, total_weeks)
                run_distance = round(weekly_mileage * distance_factor, 1)
                run_duration = round(run_distance * pace_minutes) if pace_minutes else "N/A"
                if run_type in ["Rest", "Active Recovery", "Strength Training"]:
                    workout_details = generate_rest_day_details(run_type)
                else:
                    workout_details = generate_workout_details(run_type, race_phase, current_week, total_weeks, training_distance, run_distance)
                intensity_score = calculate_intensity_score(run_type, run_distance, pace_minutes)
                schedule.append({
                    "Day": day,
                    "WorkoutType": run_type,
                    "WorkoutDetails": workout_details,
                    "TargetPace": target_pace + " per km" if target_pace != "N/A" else target_pace,
                    "Duration": f"{run_duration} minutes" if run_duration != "N/A" else "N/A",
                    "Distance": f"{run_distance} km" if run_type not in ["Rest", "Active Recovery", "Strength Training"] else "N/A",
                    "IntensityScore": intensity_score if run_type not in ["Rest", "Active Recovery", "Strength Training"] else 0
                })
            else:
                schedule.append({
                    "Day": day,
                    "WorkoutType": run_type,
                    "WorkoutDetails": "Workout details not available.",
                    "TargetPace": "N/A",
                    "Duration": "N/A",
                    "Distance": "N/A",
                    "IntensityScore": 0
                })
        else:
            schedule.append({
                "Day": day,
                "WorkoutType": "Rest",
                "WorkoutDetails": generate_rest_day_details("Rest"),
                "TargetPace": "N/A",
                "Duration": "N/A",
                "Distance": "N/A",
                "IntensityScore": 0
            })

    weekly_intensity = sum(item.get("IntensityScore", 0) for item in schedule if isinstance(item.get("IntensityScore"), (int, float)))
    schedule_summary = {
        "weeklyMileage": round(weekly_mileage, 1),
        "weeklyIntensity": weekly_intensity,
        "currentWeek": current_week,
        "totalWeeks": total_weeks,
        "racePhase": race_phase,
        "weeksUntilRace": weeks_until_race
    }
    full_response = {
        "schedule": schedule,
        "summary": schedule_summary
    }
    
    schedule_json = json.dumps(full_response)
    
    new_cache = ScheduleCache(
        race_date=race_date,
        training_distance=training_distance,
        race_phase=race_phase,
        run_days=run_days,
        long_run_day=long_run_day,
        current_mileage=weekly_mileage,
        experience_level=experience_level,
        training_goal=training_goal,
        schedule_json=schedule_json
    )
    db.session.add(new_cache)
    db.session.commit()

    return jsonify(full_response)

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
    return jsonify({"message": "Welcome to the AICOACH API. Use /api/overall-sleep, /api/ai-coach, /api/schedule, or /api/feedback."})

if __name__ == '__main__':
    GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
    GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
    garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)
    app.run(debug=True, port=8080, host="localhost")
