import os
import json
from datetime import date
from garminconnect import Garmin
from dotenv import load_dotenv
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables from the .env file
load_dotenv()

# Set up token storage file path
TOKEN_STORE = os.path.expanduser("~/.garmin_tokens.json")

def get_credentials():
    """Prompt user for credentials if not set in environment variables."""
    email = input("Enter your Garmin email: ")
    password = input("Enter your Garmin password: ")
    return email, password

def get_mfa():
    """Prompt for MFA code if required."""
    return input("Enter MFA code: ")

def init_api(email=None, password=None):
    """Initialize Garmin API with token caching to reduce login attempts."""
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

# Initialize the API using cached tokens if available
email = os.getenv("GARMIN_USERNAME")
password = os.getenv("GARMIN_PASSWORD")
client = init_api(email, password)

if client:
    # Fetch the latest 10 activities
    activities = client.get_activities(0, 10)
    print("Recent Activities:")
    for activity in activities:
        print(f"Activity ID: {activity['activityId']} - {activity['activityName']}")

    # Get today's date in ISO format (YYYY-MM-DD) and fetch sleep data for today
    today = date.today().isoformat()
    sleep_data = client.get_sleep_data(today)
    
    # Attempt to extract the overall sleep score from dailySleepDTO -> sleepScores -> overall
    print("\nExtracted Overall Sleep Score:")
    if isinstance(sleep_data, list):
        found = False
        for record in sleep_data:
            if isinstance(record, dict):
                daily = record.get("dailySleepDTO", {})
                sleep_scores = daily.get("sleepScores", {})
                overall = sleep_scores.get("overall", {})
                overall_value = overall.get("value")
                if overall_value is not None:
                    print(f"Overall Sleep Score: {overall_value}")
                    found = True
                else:
                    print("Overall sleep score not found in this record.")
            else:
                print("Unexpected record type:", type(record))
        if not found:
            print("No sleep record contained an overall sleep score.")
    elif isinstance(sleep_data, dict):
        daily = sleep_data.get("dailySleepDTO", {})
        sleep_scores = daily.get("sleepScores", {})
        overall = sleep_scores.get("overall", {})
        overall_value = overall.get("value")
        if overall_value is not None:
            print(f"Overall Sleep Score: {overall_value}")
        else:
            print("Overall sleep score not found in sleep_data.")
    else:
        print("Unexpected sleep data format:", type(sleep_data))
else:
    print("Failed to initialize Garmin API.")
