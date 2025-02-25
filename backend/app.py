import os
import json
from datetime import date, datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from garminconnect import Garmin
from dotenv import load_dotenv
import logging
from google import genai  # Gemini API client
import requests

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Set up token storage file path
TOKEN_STORE = os.path.expanduser("~/.garmin_tokens.json")

app = Flask(__name__)
CORS(app)  # Enable CORS for your app

# Configure SQLite database for feedback and schedule caching
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_cache.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define Feedback model
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # e.g., 1-5 scale
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat()
        }

# New ScheduleCache model for caching generated schedules
class ScheduleCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    race_date = db.Column(db.String, nullable=False)
    training_distance = db.Column(db.String, nullable=False)
    race_phase = db.Column(db.String, nullable=False)
    current_mileage = db.Column(db.Float, nullable=False)
    run_days = db.Column(db.Integer, nullable=False)
    long_run_day = db.Column(db.String, nullable=False)
    schedule_json = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)    

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

def get_credentials():
    """Prompt user for credentials if not set in environment variables."""
    email = input("Enter your Garmin email: ")
    password = input("Enter your Garmin password: ")
    return email, password

def get_mfa():
    """Prompt for MFA code if required."""
    return input("Enter MFA code: ")

def init_api(email=None, password=None):
    """Initialize Garmin API with token caching."""
    try:
        logger.info("Attempting token login using tokens from '%s'.", TOKEN_STORE)
        garmin = Garmin()  # Instantiate without credentials to use tokens
        garmin.login(TOKEN_STORE)
    except Exception as err:
        logger.error("Token login failed: %s", err)
        print(f"Tokens not present or expired. Logging in with credentials. Tokens will be stored in '{TOKEN_STORE}'.")
        try:
            if not email or not password:
                email, password = get_credentials()
            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin.login()
            # Store tokens for future use
            garmin.garth.dump(TOKEN_STORE)
            logger.info("Tokens stored in '%s'.", TOKEN_STORE)
        except Exception as err:
            logger.error("Credential login failed: %s", err)
            return None
    return garmin

def get_training_readiness(date_str):
    """
    Retrieve training readiness data for the given date.
    Assumes training readiness is provided by a separate endpoint at the top level.
    """
    try:
        # Attempt to call a method to get training readiness data.
        # Replace this with the appropriate call if the method name is different.
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
    #print(json.dumps(training_data, indent=4)) #dumps JSON 
    return readiness

def get_recovery_metrics(date_str):
    """
    Retrieve sleep data for the given date and extract:
      - overallSleepScore
      - avgOvernightHrv
      - bodyBatteryChange
    Also retrieves training readiness from a separate endpoint.
    """
    try:
        sleep_data = garmin_client.get_sleep_data(date_str)
    except Exception as e:
        logger.error("Error fetching sleep data: %s", e)
        sleep_data = None

    overall_value = None
    avg_over_night_hrv = None
    body_battery_change = None

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

    # Retrieve training readiness separately
    training_readiness = get_training_readiness(date_str)
    return overall_value, avg_over_night_hrv, body_battery_change, training_readiness

def time_str_to_seconds(time_str):
    """Convert a mm:ss time string to seconds."""
    try:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    except Exception as e:
        logger.error("Error converting time string to seconds: %s", e)
        return None

def seconds_to_time_str(seconds):
    """Convert seconds to a mm:ss format string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def calculate_running_paces(race_prediction_str, training_distance="5K"):
    """
    Given a race prediction as a string (e.g., "30:53") for a specific distance,
    calculate the base pace (seconds per km) and then compute:
      - Recovery Pace: base pace × 1.30
      - Easy Pace: base pace × 1.15
      - Threshold Pace: base pace × 1.04 (approx. base pace + ~15 seconds)
      - Long Run Pace: base pace × 1.20
    Returns a dictionary with paces in mm:ss per km format.
    """
    base_total_seconds = time_str_to_seconds(race_prediction_str)
    if base_total_seconds is None:
        return None

    # Determine distance factor based on training distance
    distance_km = {"5K": 5, "10K": 10, "HalfMarathon": 21.1, "Marathon": 42.2}.get(training_distance, 5)
    
    base_pace = base_total_seconds / distance_km  # seconds per km
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
    Retrieve race prediction data for the given date and training distance.
    Returns the prediction time in a mm:ss formatted string.
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

def determine_run_type(overall, avg_hrv, battery_change, readiness):
    """
    Determine the type of run based on recovery metrics.
    Returns one of: "Recovery", "Easy", or "Threshold".
    
    Criteria (example):
      - "Recovery": if overall < 60 or avg_hrv < 50 or battery_change < 50 or readiness < 50.
      - "Threshold": if overall > 80 and avg_hrv > 70 and battery_change > 70 and readiness > 70.
      - Otherwise: "Easy".
    """
    if overall < 60 or avg_hrv < 50 or battery_change < 50 or (readiness is not None and readiness < 50):
        return "Recovery"
    elif overall > 80 and avg_hrv > 70 and battery_change > 70 and (readiness is not None and readiness > 70):
        return "Threshold"
    else:
        return "Easy"

def determine_workout(overall, avg_hrv, battery_change, readiness, race_prediction):
    """
    Combine recovery metrics and race prediction to determine:
      - Run type based on recovery metrics (using determine_run_type)
      - Running paces based on race prediction
    Returns a dictionary with:
      - "runType"
      - "targetPace" (based on run type)
    """
    run_type = determine_run_type(overall, avg_hrv, battery_change, readiness)
    running_paces = calculate_running_paces(race_prediction)
    target_pace = running_paces.get(run_type) if running_paces and run_type in running_paces else None
    return {"runType": run_type, "targetPace": target_pace}

# Initialize the Garmin client using credentials from .env
GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)

@app.route('/api/overall-sleep', methods=['GET'])
def overall_sleep():
    """Return overall sleep score, avgOvernightHrv, bodyBatteryChange, and trainingReadiness."""
    today = date.today().isoformat()
    overall_value, avg_over_night_hrv, body_battery_change, training_readiness = get_recovery_metrics(today)
    result = {
        "overallSleepScore": overall_value if overall_value is not None else None,
        "avgOvernightHrv": avg_over_night_hrv if avg_over_night_hrv is not None else None,
        "bodyBatteryChange": body_battery_change if body_battery_change is not None else None,
        "trainingReadiness": training_readiness if training_readiness is not None else None
    }
    return jsonify(result)

@app.route('/api/ai-coach', methods=['GET'])
def ai_coach():
    """
    Generate running recommendations based on recovery metrics and race prediction.
    Accepts a query parameter 'distance' (e.g., "5K", "10K", "HalfMarathon", "Marathon").
    """
    training_distance = request.args.get("distance", "5K")  # default to 5K if not provided
    today = date.today().isoformat()
    
    overall_value, avg_over_night_hrv, body_battery_change, training_readiness = get_recovery_metrics(today)
    race_prediction = get_race_prediction(garmin_client, today, training_distance)
    
    if any(v is None for v in [overall_value, avg_over_night_hrv, body_battery_change, training_readiness, race_prediction]):
        logger.error("Required data not found")
        return jsonify({"error": "Required data not found"}), 404

    # Calculate running paces using the provided training distance
    running_paces = calculate_running_paces(race_prediction, training_distance)
    
    # Determine run type based solely on recovery metrics (this could be extended to use distance info too)
    run_type = determine_run_type(overall_value, avg_over_night_hrv, body_battery_change, training_readiness)
    target_pace = running_paces.get(run_type) if running_paces and run_type in running_paces else None

    # Build the Gemini prompt that includes race prediction and recovery metrics
    base_pace_seconds = time_str_to_seconds(race_prediction) / {"5K": 5, "10K": 10, "HalfMarathon": 21.1, "Marathon": 42.2}.get(training_distance, 5)
    base_pace_str = seconds_to_time_str(base_pace_seconds)
    prompt = (
        f"You are a super fitness trainer. My {training_distance} race prediction is {race_prediction} "
        f"(approximately {base_pace_str} per km). "
        f"My recovery metrics are: overall sleep score {overall_value}, average overnight HRV {avg_over_night_hrv}, "
        f"body battery change {body_battery_change}, and training readiness {training_readiness}. "
        f"instruction: [In less than 300 words, recommend one of the following run types with an appropriate pace and duration: Recovery, Easy, Threshold, and Long Run.]"
        f""
    )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_model = "gemini-2.0-flash-lite-preview-02-05"
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
        "trainingDistance": training_distance
    })

@app.route('/api/schedule', methods=['POST'])
def generate_schedule():
    """
    Expected JSON input:
    {
      "runDays": <integer>,
      "longRunDay": <string>,
      "trainingDistance": <string>,   // e.g., "5K", "10K", "HalfMarathon", "Marathon"
      "raceDate": <string>,           // e.g., "2025-04-15"
      "racePhase": <string>,          // e.g., "base", "build", "peak", "taper", or "auto"
      "currentMileage": <number>      // current weekly mileage in km (optional)
    }
    
    Returns a full weekly schedule including:
      - Day
      - WorkoutType
      - WorkoutDetails
      - TargetPace (min/km)
      - Duration (min)
      - Distance (km)
    """
    data = request.get_json()
    required_fields = ["runDays", "longRunDay", "trainingDistance", "raceDate", "racePhase"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "runDays, longRunDay, trainingDistance, raceDate, and racePhase are required"}), 400

    run_days = data.get("runDays")
    long_run_day = data.get("longRunDay").capitalize()
    training_distance = data.get("trainingDistance")
    race_date = data.get("raceDate")
    race_phase = data.get("racePhase").lower()
    current_mileage = data.get("currentMileage")  # in km

    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if long_run_day not in week_days:
        return jsonify({"error": f"Invalid longRunDay. Must be one of: {', '.join(week_days)}"}), 400

    # Determine default weekly mileage based on trainingDistance
    def get_default_weekly_mileage(training_distance):
        mapping = {"5K": 40, "10K": 56, "HalfMarathon": 72, "Marathon": 88}
        return mapping.get(training_distance, 40)
    default_mileage = get_default_weekly_mileage(training_distance)
    phase_multiplier = {"base": 0.9, "build": 1.0, "peak": 1.2, "taper": 0.8, "auto": 1.0}
    multiplier = phase_multiplier.get(race_phase, 1.0)
    weekly_mileage = current_mileage if current_mileage is not None else default_mileage * multiplier

    # Check for cached schedule (generated within last 24 hours)
    cached_schedule = ScheduleCache.query.filter_by(
        race_date=race_date,
        training_distance=training_distance,
        race_phase=race_phase,
        run_days=run_days,
        long_run_day=long_run_day,
        current_mileage=weekly_mileage
    ).order_by(ScheduleCache.timestamp.desc()).first()
    if cached_schedule and (datetime.utcnow() - cached_schedule.timestamp) < timedelta(hours=24):
        return jsonify({"schedule": json.loads(cached_schedule.schedule_json)})

    # Generate running days: select run_days from week ensuring long_run_day is included
    running_days = []
    for day in week_days:
        if len(running_days) < run_days:
            running_days.append(day)
    if long_run_day not in running_days:
        running_days[-1] = long_run_day
    running_days = sorted(running_days, key=lambda d: week_days.index(d))

    today_str = date.today().isoformat()
    race_prediction = get_race_prediction(garmin_client, today_str, training_distance)
    if not race_prediction:
        return jsonify({"error": "Race prediction data not found"}), 404
    running_paces = calculate_running_paces(race_prediction, training_distance)

    # Helper functions to determine run duration and distance dynamically
    def determine_run_duration(run_type, weekly_mileage):
        # Assume an average pace of 6 min/km to convert mileage to minutes.
        factors = {"Recovery": 0.10, "Easy": 0.15, "Threshold": 0.12, "LongRun": 0.25}
        total_minutes = weekly_mileage * 6
        return round(total_minutes * factors.get(run_type, 0))

    def determine_run_distance(run_type, weekly_mileage):
        factors = {"Recovery": 0.10, "Easy": 0.15, "Threshold": 0.12, "LongRun": 0.25}
        return round(weekly_mileage * factors.get(run_type, 0), 1)

    # For running days, assign run types; for non-running days, mark as Rest.
    default_run_types = ["Recovery", "Threshold", "Easy"]
    schedule = []
    type_index = 0

    for day in week_days:
        if day in running_days:
            if day == long_run_day:
                run_type = "LongRun"
            else:
                run_type = default_run_types[type_index % len(default_run_types)]
                type_index += 1

            target_pace = running_paces.get(run_type, "N/A")
            def pace_str_to_minutes(pace_str):
                try:
                    parts = pace_str.split(':')
                    return int(parts[0]) + int(parts[1]) / 60.0
                except Exception as e:
                    logger.error("Error parsing pace string: %s", e)
                    return None
            pace_minutes = pace_str_to_minutes(target_pace) if target_pace != "N/A" else None
            run_distance = weekly_mileage * ({"Recovery": 0.10, "Easy": 0.15, "Threshold": 0.12, "LongRun": 0.25}.get(run_type, 0))
            run_duration = round(run_distance * pace_minutes) if pace_minutes else "N/A"
            if run_type == "LongRun":
                details = "Long run: Steady pace for endurance building."
            elif run_type == "Recovery":
                details = "Recovery run: Easy pace to promote recovery."
            elif run_type == "Easy":
                details = "Easy run: Maintain a conversational pace."
            elif run_type == "Threshold":
                details = "Threshold run: Near race pace for lactate threshold improvement."
            else:
                details = ""
            schedule.append({
                "Day": day,
                "WorkoutType": run_type,
                "WorkoutDetails": details,
                "TargetPace": target_pace + " per km" if target_pace != "N/A" else target_pace,
                "Duration": f"{run_duration} minutes",
                "Distance": f"{round(run_distance,1)} km"
            })
        else:
            schedule.append({
                "Day": day,
                "WorkoutType": "Rest",
                "WorkoutDetails": "Rest or cross-training day",
                "TargetPace": "N/A",
                "Duration": "N/A",
                "Distance": "N/A"
            })

    # Cache the generated schedule
    schedule_json = json.dumps(schedule)
    new_cache = ScheduleCache(
        race_date=race_date,
        training_distance=training_distance,
        race_phase=race_phase,
        run_days=run_days,
        long_run_day=long_run_day,
        current_mileage=weekly_mileage,
        schedule_json=schedule_json
    )
    db.session.add(new_cache)
    db.session.commit()

    return jsonify({"schedule": schedule})

@app.route('/api/race-predictions', methods=['GET'])
def race_predictions():
    try:
        race_data = garmin_client.get_race_predictions()
        logger.info("Race prediction data: %s", json.dumps(race_data, indent=4))
    except Exception as e:
        logger.error("Error fetching race predictions: %s", e)
        return jsonify({"error": "Failed to retrieve race predictions"}), 500
    output = {}
    def seconds_to_time_str(seconds):
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
        output["time5K"] = seconds_to_time_str(race_data.get("time5K")) if race_data.get("time5K") else "N/A"
        output["time10K"] = seconds_to_time_str(race_data.get("time10K")) if race_data.get("time10K") else "N/A"
        output["timeHalfMarathon"] = seconds_to_time_str(race_data.get("timeHalfMarathon")) if race_data.get("timeHalfMarathon") else "N/A"
        output["timeMarathon"] = seconds_to_time_str(race_data.get("timeMarathon")) if race_data.get("timeMarathon") else "N/A"
    elif isinstance(race_data, list):
        for record in race_data:
            if isinstance(record, dict) and record.get("time5K") is not None:
                output["time5K"] = seconds_to_time_str(record.get("time5K"))
                output["time10K"] = seconds_to_time_str(record.get("time10K")) if record.get("time10K") else "N/A"
                output["timeHalfMarathon"] = seconds_to_time_str(record.get("timeHalfMarathon")) if record.get("timeHalfMarathon") else "N/A"
                output["timeMarathon"] = seconds_to_time_str(record.get("timeMarathon")) if record.get("timeMarathon") else "N/A"
                break

    return jsonify(output)        

# Endpoint to handle user feedback
@app.route('/api/feedback', methods=['POST'])
def post_feedback():
    """
    Accept user feedback. Expected JSON format:
    {
      "rating": 4,
      "comment": "Great workout recommendation!"
    }
    """
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

# Optional endpoint to view feedback (for debugging)
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
    return jsonify({"message": "Welcome to the AICOACH API. Use /api/overall-sleep, /api/ai-coach, /api/activities, or /api/feedback."})

if __name__ == '__main__':
    app.run(debug=True, port=8080)
