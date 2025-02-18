import os
import json
from datetime import date
from garminconnect import Garmin
from dotenv import load_dotenv
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables from .env file
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

    # Get today's date in ISO format (YYYY-MM-DD)
    today = date.today()
    sleep_data = client.get_sleep_data(today.isoformat())

    # Define the list of keys we are interested in
    desired_keys = [

        "avgOvernightHrv",

        "bodyBatteryChange",

    ]

    print("\nTrimmed Sleep Data:")
    # If sleep_data is a list of records:
    if isinstance(sleep_data, list):
        for record in sleep_data:
            if isinstance(record, dict):
                trimmed = {key: record.get(key, "Not Available") for key in desired_keys}
                print(json.dumps(trimmed, indent=4))
            else:
                print("Unexpected data format:", record)
    # If sleep_data is a single dict (adjust if necessary)
    elif isinstance(sleep_data, dict):
        trimmed = {key: sleep_data.get(key, "Not Available") for key in desired_keys}
        print(json.dumps(trimmed, indent=4))
    else:
        print("Unexpected sleep data format:", type(sleep_data))
else:
    print("Failed to initialize Garmin API.")


#this old script returned     "avgOvernightHrv", "bodyBatteryChange"