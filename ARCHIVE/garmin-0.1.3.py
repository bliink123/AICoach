import os
import json
from datetime import date
from flask import Flask, jsonify
from garminconnect import Garmin
from dotenv import load_dotenv
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables from the .env file
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
        print(f"Trying to login using token data from '{TOKEN_STORE}'...\n")
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
            print(f"Tokens stored in '{TOKEN_STORE}'.\n")
        except Exception as err:
            logger.error("Login failed: %s", err)
            return None
    return garmin

# Initialize the Garmin client using credentials from .env
GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)

@app.route('/api/overall-sleep', methods=['GET'])
def overall_sleep():
    # Get today's date in ISO format (YYYY-MM-DD)
    today = date.today().isoformat()
    sleep_data = garmin_client.get_sleep_data(today)
    
    overall_value = None
    avg_over_night_hrv = None
    body_battery_change = None

    def extract_values(data):
        # First, try to extract from dailySleepDTO
        daily = data.get("dailySleepDTO", {})
        overall_value = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_over_night_hrv = daily.get("avgOvernightHrv")
        body_battery_change = daily.get("bodyBatteryChange")
        # If any of these values aren't found, try at the top level
        if avg_over_night_hrv is None:
            avg_over_night_hrv = data.get("avgOvernightHrv")
        if body_battery_change is None:
            body_battery_change = data.get("bodyBatteryChange")
        return overall_value, avg_over_night_hrv, body_battery_change

    if isinstance(sleep_data, dict):
        overall_value, avg_over_night_hrv, body_battery_change = extract_values(sleep_data)
    elif isinstance(sleep_data, list):
        for record in sleep_data:
            if isinstance(record, dict):
                overall_value, avg_over_night_hrv, body_battery_change = extract_values(record)
                if overall_value is not None:
                    break

    # Instead of erroring if any value is missing, return what is available (or null)
    result = {
        "overallSleepScore": overall_value if overall_value is not None else None,
        "avgOvernightHrv": avg_over_night_hrv if avg_over_night_hrv is not None else None,
        "bodyBatteryChange": body_battery_change if body_battery_change is not None else None
    }

    # You can choose to return an error if any key is missing, but here we return nulls.
    return jsonify(result)

@app.route('/api/activities', methods=['GET'])
def get_activities():
    # Fetch the latest 10 activities
    activities = garmin_client.get_activities(0, 10)
    return jsonify(activities)

if __name__ == '__main__':
    app.run(debug=True)
