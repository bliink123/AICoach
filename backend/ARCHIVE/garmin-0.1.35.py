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

def extract_recovery_metrics(sleep_data):
    """
    Extract overallSleepScore, avgOvernightHrv, and bodyBatteryChange.
    First check inside dailySleepDTO; if not found, fall back to top-level.
    """
    overall_value = None
    avg_over_night_hrv = None
    body_battery_change = None

    def extract_from_data(data):
        daily = data.get("dailySleepDTO", {})
        overall_val = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_hrv = daily.get("avgOvernightHrv") or data.get("avgOvernightHrv")
        battery = daily.get("bodyBatteryChange") or data.get("bodyBatteryChange")
        return overall_val, avg_hrv, battery

    if isinstance(sleep_data, dict):
        overall_value, avg_over_night_hrv, body_battery_change = extract_from_data(sleep_data)
    elif isinstance(sleep_data, list):
        for record in sleep_data:
            if isinstance(record, dict):
                overall_value, avg_over_night_hrv, body_battery_change = extract_from_data(record)
                if overall_value is not None:
                    break
    return overall_value, avg_over_night_hrv, body_battery_change

def determine_workout(overall, avg_hrv, battery_change):
    """
    Revised rule-based decision tree for workout recommendations.
    
    Assumptions (adjust thresholds as needed):
    - A low overall sleep score (< 60) or low avgOvernightHrv (< 50) or low bodyBatteryChange (< 50)
      indicates poor recovery, so recommend a recovery-focused (light) workout.
    - Moderate values (overall 60-80, avgOvernightHrv 50-70, bodyBatteryChange 50-70) suggest a balanced session.
    - High values (overall > 80, avgOvernightHrv > 70, bodyBatteryChange > 70) indicate good recovery,
      so recommend a high-intensity workout.
    """
    if overall < 60 or avg_hrv < 50 or battery_change < 30:
        return "Recovery - Light Activity (e.g., yoga, walking, gentle stretching)"
    elif 60 <= overall <= 80 and 50 <= avg_hrv <= 70 and 30 <= battery_change <= 40:
        return "Moderate Workout - Balanced Cardio and Strength Session"
    elif overall > 80 and avg_hrv > 70 and battery_change > 40:
        return "High-Intensity Workout - Focus on Strength and Cardio"
    else:
        return "Moderate Workout - Adjust intensity as needed"

# Initialize the Garmin client using credentials from .env
GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)

@app.route('/api/overall-sleep', methods=['GET'])
def overall_sleep():
    """Return overall sleep score, avgOvernightHrv, and bodyBatteryChange."""
    try:
        today = date.today().isoformat()
        sleep_data = garmin_client.get_sleep_data(today)
    except Exception as e:
        logger.error("Error fetching sleep data: %s", e)
        return jsonify({"error": "Failed to retrieve sleep data"}), 500

    overall_value, avg_over_night_hrv, body_battery_change = extract_recovery_metrics(sleep_data)
    result = {
        "overallSleepScore": overall_value if overall_value is not None else None,
        "avgOvernightHrv": avg_over_night_hrv if avg_over_night_hrv is not None else None,
        "bodyBatteryChange": body_battery_change if body_battery_change is not None else None
    }
    return jsonify(result)

@app.route('/api/ai-coach', methods=['GET'])
def ai_coach():
    """
    Generate two workout recommendations:
    1. A rule-based recommendation using our decision tree.
    2. An AI-generated recommendation using Gemini.
    """
    try:
        today = date.today().isoformat()
        sleep_data = garmin_client.get_sleep_data(today)
    except Exception as e:
        logger.error("Error fetching sleep data for AI coach: %s", e)
        return jsonify({"error": "Failed to retrieve sleep data"}), 500

    overall_value, avg_over_night_hrv, body_battery_change = extract_recovery_metrics(sleep_data)

    if overall_value is None or avg_over_night_hrv is None or body_battery_change is None:
        logger.error("Required recovery data not found")
        return jsonify({"error": "Required recovery data not found"}), 404

    # Rule-based recommendation
    rulesRecommendation = determine_workout(overall_value, avg_over_night_hrv, body_battery_change)

    # AI recommendation via Gemini
    prompt = (
        f"Based on an overall sleep score of {overall_value}, an average overnight HRV of {avg_over_night_hrv}, "
        f"and a body battery change of {body_battery_change},"
        f"in 120 words please reccomnded a run if my fully recovered pace was 6min/km for 5k. "
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
        "rulesBasedRecommendation": rulesRecommendation,
        "aiCoachRecommendation": aiRecommendation,
        "overallSleepScore": overall_value,
        "avgOvernightHrv": avg_over_night_hrv,
        "bodyBatteryChange": body_battery_change
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
