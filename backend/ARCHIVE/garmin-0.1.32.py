import os
import json
from datetime import date
from flask import Flask, jsonify
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
        logger.info("Attempting token login using token data from '%s'.", TOKEN_STORE)
        garmin = Garmin()  # Instantiate without credentials to use tokens
        garmin.login(TOKEN_STORE)
    except Exception as err:
        logger.error("Token login failed: %s", err)
        print(
            f"Login tokens not present or expired. Logging in with credentials.\n"
            f"Tokens will be stored in '{TOKEN_STORE}' for future use.\n"
        )
        try:
            if not email or not password:
                email, password = get_credentials()
            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin.login()
            # Store tokens for future use
            garmin.garth.dump(TOKEN_STORE)
            logger.info("Tokens stored successfully in '%s'.", TOKEN_STORE)
        except Exception as err:
            logger.error("Credential login failed: %s", err)
            return None
    return garmin

# Initialize Garmin client using credentials from .env
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

    overall_value = None
    avg_over_night_hrv = None
    body_battery_change = None

    def extract_values(data):
        daily = data.get("dailySleepDTO", {})
        overall_value = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_over_night_hrv = daily.get("avgOvernightHrv")
        body_battery_change = daily.get("bodyBatteryChange")
        # Fallback: if avgOvernightHrv or bodyBatteryChange are missing, try top level
        if avg_over_night_hrv is None:
            avg_over_night_hrv = data.get("avgOvernightHrv")
        if body_battery_change is None:
            body_battery_change = data.get("bodyBatteryChange")
        return overall_value, avg_over_night_hrv, body_battery_change

    try:
        if isinstance(sleep_data, dict):
            overall_value, avg_over_night_hrv, body_battery_change = extract_values(sleep_data)
        elif isinstance(sleep_data, list):
            for record in sleep_data:
                if isinstance(record, dict):
                    overall_value, avg_over_night_hrv, body_battery_change = extract_values(record)
                    if overall_value is not None:
                        break
        else:
            logger.error("Unexpected sleep data format: %s", type(sleep_data))
            return jsonify({"error": "Unexpected sleep data format"}), 500
    except Exception as e:
        logger.error("Error processing sleep data: %s", e)
        return jsonify({"error": "Error processing sleep data"}), 500

    result = {
        "overallSleepScore": overall_value if overall_value is not None else None,
        "avgOvernightHrv": avg_over_night_hrv if avg_over_night_hrv is not None else None,
        "bodyBatteryChange": body_battery_change if body_battery_change is not None else None
    }
    #uncomment below to get json dump if values are returning null
    #print("\nFull Raw Sleep Data:")
    #print(json.dumps(sleep_data, indent=4))
    return jsonify(result)

@app.route('/api/ai-coach', methods=['GET'])
def ai_coach():
    """Generate a workout recommendation based on recovery metrics using Gemini AI."""
    try:
        today = date.today().isoformat()
        sleep_data = garmin_client.get_sleep_data(today)
    except Exception as e:
        logger.error("Error fetching sleep data for AI coach: %s", e)
        return jsonify({"error": "Failed to retrieve sleep data"}), 500

    overall_value = None
    avg_over_night_hrv = None
    body_battery_change = None

    def extract_values(data):
        daily = data.get("dailySleepDTO", {})
        overall_value = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_over_night_hrv = daily.get("avgOvernightHrv")
        body_battery_change = daily.get("bodyBatteryChange")
        # Fallback: if avgOvernightHrv or bodyBatteryChange are missing, try top level
        if avg_over_night_hrv is None:
            avg_over_night_hrv = data.get("avgOvernightHrv")
        if body_battery_change is None:
            body_battery_change = data.get("bodyBatteryChange")
        return overall_value, avg_over_night_hrv, body_battery_change

    try:
        if isinstance(sleep_data, dict):
            overall_value, avg_over_night_hrv, body_battery_change = extract_values(sleep_data)
        elif isinstance(sleep_data, list):
            for record in sleep_data:
                if isinstance(record, dict):
                    overall_value, avg_over_night_hrv, body_battery_change = extract_values(record)
                    if overall_value is not None:
                        break
        else:
            logger.error("Unexpected sleep data format for AI coach: %s", type(sleep_data))
            return jsonify({"error": "Unexpected sleep data format"}), 500
    except Exception as e:
        logger.error("Error processing sleep data for AI coach: %s", e)
        return jsonify({"error": "Error processing sleep data"}), 500

    if overall_value is None or avg_over_night_hrv is None or body_battery_change is None:
        logger.error("Required recovery data not found")
        return jsonify({"error": "Required recovery data not found"}), 404

    prompt = (
        f"Based on an overall sleep score of {overall_value}, an average overnight HRV of {avg_over_night_hrv}, "
        f"and a body battery change of {body_battery_change}, please recommend an appropriate workout for today."
    )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_model = "gemini-2.0-flash-lite-preview-02-05"
    gemini_client = genai.Client(api_key=gemini_api_key)

    try:
        response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=prompt
        )
        recommendation = response.text
    except Exception as e:
        logger.error("Error calling Gemini API: %s", e)
        return jsonify({"error": "Failed to generate recommendation"}), 500

    return jsonify({
        "recommendation": recommendation,
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

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Welcome to the AICOACH API. Use /api/overall-sleep, /api/ai-coach, or /api/activities."})

if __name__ == '__main__':
    app.run(debug=True, port=8080)
