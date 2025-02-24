import os
import json
from datetime import date
from garminconnect import Garmin
from dotenv import load_dotenv
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (ensure this file contains your GARMIN_USERNAME and GARMIN_PASSWORD)
load_dotenv()
TOKEN_STORE = os.path.expanduser("~/.garmin_tokens.json")

def get_credentials():
    email = input("Enter your Garmin email: ")
    password = input("Enter your Garmin password: ")
    return email, password

def init_api(email=None, password=None):
    try:
        logger.info("Attempting token login using tokens from '%s'.", TOKEN_STORE)
        garmin = Garmin()  # Instantiate without credentials to use tokens
        garmin.login(TOKEN_STORE)
    except Exception as err:
        logger.error("Token login failed: %s", err)
        print(f"Tokens not present or expired. Logging in with credentials. Tokens will be stored in '{TOKEN_STORE}'.")
        if not email or not password:
            email, password = get_credentials()
        try:
            garmin = Garmin(email=email, password=password, is_cn=False)
            garmin.login()
            garmin.garth.dump(TOKEN_STORE)
            logger.info("Tokens stored in '%s'.", TOKEN_STORE)
        except Exception as err:
            logger.error("Credential login failed: %s", err)
            return None
    return garmin

def seconds_to_time_str(seconds):
    """Convert seconds to a mm:ss format string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

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


if __name__ == '__main__':
    # Initialize Garmin client
    GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
    GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
    garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)
    
    if not garmin_client:
        logger.error("Failed to initialize Garmin client.")
        exit(1)
    
    today = date.today().isoformat()
    race_prediction = get_race_prediction(garmin_client, today)
    if race_prediction:
        print("Race Prediction for today (5K):", race_prediction)
    else:
        print("No race prediction data found for today.")

