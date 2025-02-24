import os
import json
from datetime import date, datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from garminconnect import Garmin
from dotenv import load_dotenv
import logging
from google import genai  # Gemini API client
import requests
from flask_cors import CORS

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Set up token storage file path
TOKEN_STORE = os.path.expanduser("~/.garmin_tokens.json")

app = Flask(__name__)
CORS(app)  # Enable CORS for your app

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feedback.db'
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

def calculate_running_paces(race_prediction_str):
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
    # For a 5K, base pace = total seconds / 5
    base_pace = base_total_seconds / 5.0
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


def get_race_prediction(garmin_client, date_str):
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

    prediction = None
    if race_data:
        if isinstance(race_data, dict):
            prediction_seconds = race_data.get("time5K")
        elif isinstance(race_data, list):
            prediction_seconds = None
            for record in race_data:
                if isinstance(record, dict) and record.get("time5K") is not None:
                    prediction_seconds = record.get("time5K")
                    break
        if prediction_seconds is not None:
            prediction = seconds_to_time_str(prediction_seconds)
    return prediction

def determine_workout(overall, avg_hrv, battery_change, readiness):
    """
    Revised rule-based decision tree for workout recommendations.
    
    Assumptions (adjust thresholds as needed):
    - A low overall sleep score (< 60) or low avgOvernightHrv (< 50) or low bodyBatteryChange (< 50)
      indicates poor recovery, so recommend a recovery-focused (light) workout.
    - Moderate values (overall 60-80, avgOvernightHrv 50-70, bodyBatteryChange 50-70) suggest a balanced session.
    - High values (overall > 80, avgOvernightHrv > 70, bodyBatteryChange > 70) indicate good recovery,
      so recommend a high-intensity workout.
    """
    if overall < 60 or avg_hrv < 50 or battery_change < 30 or (readiness is not None and readiness < 50):
        return "Recovery - Light Activity (e.g., yoga, walking, gentle stretching)"
    elif overall >= 60 and overall <= 80 and avg_hrv >= 50 and avg_hrv <= 70 and battery_change >= 30 and battery_change <= 40 and (readiness is None or readiness >= 50):
        return "Moderate Workout - Balanced Cardio and Strength Session"
    elif overall > 80 and avg_hrv > 70 and battery_change > 40 and (readiness is not None and readiness > 70):
        return "High-Intensity Workout - Focus on Strength and Cardio"
    else:
        return "Moderate Workout - Adjust intensity as needed"

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
    Generate two workout recommendations:
    1. A rules-based recommendation using our decision tree.
    2. An AI-generated recommendation using Gemini.
    """
    today = date.today().isoformat()
    overall_value, avg_over_night_hrv, body_battery_change, training_readiness = get_recovery_metrics(today)
    race_prediction = get_race_prediction(garmin_client, today)

    # Validate that we have the necessary data.
    if (overall_value is None or avg_over_night_hrv is None or 
        body_battery_change is None or training_readiness is None or 
        race_prediction is None):
        logger.error("Required data not found")
        return jsonify({"error": "Required data not found"}), 404

    # Calculate rule-based running paces from race prediction
    running_paces = calculate_running_paces(race_prediction)

    # Rule-based recommendation
    rulesRecommendation = determine_workout(overall_value, avg_over_night_hrv, body_battery_change, training_readiness)

    # AI recommendation via Gemini
    prompt = (
        f"You are a super fitness trainer. My 5K race prediction is {race_prediction} "
        f"(approximately {seconds_to_time_str(time_str_to_seconds(race_prediction)/5)} per km). "
        f"My recovery metrics are: overall sleep score {overall_value}, average overnight HRV {avg_over_night_hrv}, "
        f"body battery change {body_battery_change}, and training readiness {training_readiness}. "
        f"instruction: [In less than 300 words, recommend one of the following run types with an appropriate pace and duration: Recovery, Easy, Threshold, and Long Run.]"
        f""
    )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_model = "gemini-2.0-flash"
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
        "rulesBasedRecommendation": rulesRecommendation,
        "aiCoachRecommendation": aiRecommendation,
        "overallSleepScore": overall_value,
        "avgOvernightHrv": avg_over_night_hrv,
        "bodyBatteryChange": body_battery_change,
        "trainingReadiness": training_readiness,
        "racePrediction": race_prediction 
    })

@app.route('/api/activities', methods=['GET'])
def get_activities():
    """Return the latest 10 activities."""
    try:
        activities = garmin_client.get_activities(0, 10)
        return jsonify(activities)
    except Exception as e:
        logger.error("Error fetching activities: %s", e)
        return jsonify({"error": "Failed to retrieve activities"}), 500

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
