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
CORS(app)  # Enable CORS

# Configure SQLite database for feedback and schedule caching
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_cache.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------------
# Database Models
# -------------------------
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

with app.app_context():
    db.create_all()

# -------------------------
# Helper Functions
# -------------------------

def get_credentials():
    email = input("Enter your Garmin email: ")
    password = input("Enter your Garmin password: ")
    return email, password

def get_mfa():
    return input("Enter MFA code: ")

def init_api(email=None, password=None):
    try:
        logger.info("Attempting token login using tokens from '%s'.", TOKEN_STORE)
        garmin = Garmin()  # Instantiate to use tokens
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

def calculate_running_paces(race_prediction_str, training_distance="5K"):
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

def determine_run_type(overall, avg_hrv, battery_change, readiness):
    if overall < 60 or avg_hrv < 50 or battery_change < 50 or (readiness is not None and readiness < 50):
        return "Recovery"
    elif overall > 80 and avg_hrv > 70 and battery_change > 70 and (readiness is not None and readiness > 70):
        return "Threshold"
    else:
        return "Easy"

def get_race_prediction(garmin_client, date_str, training_distance="5K"):
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
# Advanced Periodization Helper Functions
# -------------------------

def determine_race_phase(weeks_until_race, training_distance):
    plan_length = {"5K": 12, "10K": 16, "HalfMarathon": 20, "Marathon": 24}.get(training_distance, 16)
    if weeks_until_race >= plan_length:
        return "base"
    elif weeks_until_race <= 2:
        return "taper"
    elif weeks_until_race <= plan_length // 5:
        return "peak"
    else:
        return "build"

def get_training_plan_length(training_distance, experience_level):
    base_length = {"5K": 12, "10K": 16, "HalfMarathon": 20, "Marathon": 24}.get(training_distance, 16)
    experience_multiplier = {"beginner": 1.0, "intermediate": 1.0, "advanced": 0.9}.get(experience_level, 1.0)
    return round(base_length * experience_multiplier)

def get_default_weekly_mileage(training_distance, experience_level, training_goal):
    base_mileage = {"5K": 40, "10K": 56, "HalfMarathon": 72, "Marathon": 88}.get(training_distance, 40)
    experience_multiplier = {"beginner": 0.8, "intermediate": 1.0, "advanced": 1.2}.get(experience_level, 1.0)
    goal_multiplier = {"finish": 0.9, "pr": 1.0, "compete": 1.1}.get(training_goal, 1.0)
    return base_mileage * experience_multiplier * goal_multiplier

def calculate_phase_multiplier(race_phase, current_week, total_weeks):
    if race_phase == "base":
        return 0.8 + (0.2 * current_week / (total_weeks * 0.3))
    elif race_phase == "build":
        return 0.9 + (0.3 * (current_week - (total_weeks * 0.3)) / (total_weeks * 0.5))
    elif race_phase == "peak":
        return 1.1 + (0.1 * (current_week - (total_weeks * 0.8)) / (total_weeks * 0.1))
    elif race_phase == "taper":
        weeks_in_taper = current_week - (total_weeks * 0.9)
        return 1.2 - (0.4 * weeks_in_taper / (total_weeks * 0.1))
    else:
        return 1.0
'''
def distribute_running_days(week_days, run_days, long_run_day):
    long_run_index = week_days.index(long_run_day)
    result = [long_run_day]
    remaining_days = [d for d in week_days if d != long_run_day]
    ordered_days = []
    for i in range(1, 4):
        before_idx = (long_run_index - i) % 7
        after_idx = (long_run_index + i) % 7
        if week_days[before_idx] not in ordered_days:
            ordered_days.append(week_days[before_idx])
        if week_days[after_idx] not in ordered_days:
            ordered_days.append(week_days[after_idx])
    for day in remaining_days:
        if day not in ordered_days:
            ordered_days.append(day)
    for day in ordered_days:
        if len(result) < run_days:
            result.append(day)
    return sorted(result, key=lambda d: week_days.index(d))
'''

def get_run_days_simple(week_days, run_days, long_run_day):
    """Simple method to get a set of run days, ensuring long_run_day is included."""
    selected_run_days = []
    if long_run_day not in week_days:
        raise ValueError("long_run_day must be in week_days")

    selected_run_days.append(long_run_day)  # Always include long run day

    # Select other run days (e.g., first few other days - adjust as needed)
    for day in week_days:
        if day != long_run_day and len(selected_run_days) < run_days:
            selected_run_days.append(day)

    return sorted(selected_run_days, key=lambda d: week_days.index(d)) # Keep sorted for consistency

def generate_workout_types(race_phase, current_week, total_weeks, run_days, training_distance):
    workout_types = []
    workout_types.append("LongRun") # Long run always included

    if race_phase == "base":
        workout_types.extend(["Easy"] * (run_days - 1))
    elif race_phase == "build":
        if run_days >= 3:
            workout_types.append("Threshold")
            workout_types.extend(["Easy"] * (run_days - 2))
        else:
            workout_types.extend(["Easy"] * (run_days - 1))
    elif race_phase == "peak":
        if run_days >= 4:
            workout_types.extend(["Threshold", "Intervals"])
            workout_types.extend(["Easy"] * (run_days - 3))
        elif run_days >= 3:
            workout_types.append("Threshold")
            workout_types.extend(["Easy"] * (run_days - 2))
        else:
            workout_types.extend(["Easy"] * (run_days - 1))
    elif race_phase == "taper":
        if run_days >= 3:
            workout_types.append("Intervals")
            workout_types.extend(["Easy"] * (run_days - 2))
        else:
            workout_types.extend(["Easy"] * (run_days - 1))

    final_types = list(workout_types) # Copy to avoid modifying original

    while len(final_types) > run_days: # Adjust removal priority
        if "Recovery" in final_types: # Remove Recovery first (if present)
            final_types.remove("Recovery")
        elif "Easy" in final_types: # Then remove Easy
            final_types.remove("Easy")

    return final_types

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
            return f"Long run: {distance} km at an easy, conversational pace to build endurance."
        elif race_phase == "build":
            return f"Long run: {distance} km with the last 3-5 km at marathon pace."
        elif race_phase == "peak":
            if training_distance == "Marathon":
                return f"Long run: {distance} km with the middle {round(distance*0.5)} km at race pace."
            else:
                return f"Long run: {distance} km with a progressive effort, finishing strong."
        else:
            return f"Shorter long run: {distance} km at an easy pace."
    elif run_type == "Recovery":
        return f"Recovery run: {distance} km at a very relaxed pace."
    elif run_type == "Easy":
        return f"Easy run: {distance} km at a comfortable, steady pace."
    elif run_type == "Threshold":
        if race_phase == "base":
            return f"Threshold: {distance} km including 2-3 x 5 min at threshold pace."
        elif race_phase == "build":
            return f"Threshold: {distance} km with 20 minutes at threshold pace."
        elif race_phase == "peak":
            return f"Threshold: {distance} km with 2 x 15 min at threshold pace."
        else:
            return f"Threshold: {distance} km with 10 minutes at threshold pace."
    elif run_type == "Intervals":
        if training_distance in ["5K", "10K"]:
            if race_phase == "base":
                return f"Intervals: {distance} km with 6-8 x 400m at 5K effort."
            elif race_phase == "build":
                return f"Intervals: {distance} km with 5-6 x 800m at 5K effort."
            elif race_phase == "peak":
                return f"Intervals: {distance} km with 5 x 1000m at 5K effort."
            else:
                return f"Intervals: {distance} km with 3-4 x 400m at 5K effort."
        else:
            if race_phase == "build":
                return f"Intervals: {distance} km with 6-8 x 400m at 10K effort."
            elif race_phase == "peak":
                return f"Intervals: {distance} km with 3-4 x 1 mile at 10K effort."
            else:
                return f"Intervals: {distance} km with 4-5 x 400m at 10K effort."
    return f"{run_type} run: {distance} km."

def calculate_intensity_score(run_type, distance, pace_minutes):
    if pace_minutes == "N/A" or pace_minutes is None:
        return 0
    intensity_factor = {"Recovery": 0.7, "Easy": 0.8, "Threshold": 1.0, "Intervals": 1.2, "LongRun": 0.85}.get(run_type, 0.8)
    return round(distance * intensity_factor * pace_minutes)

def suggest_rest_day_activity(day_index, running_days, week_days):
    running_indices = [week_days.index(day) for day in running_days]
    is_after_hard = any(((day_index - 1) % 7) == idx for idx in running_indices)
    if is_after_hard:
        return "Active Recovery"
    elif day_index % 2 == 0:
        return "Strength Training"
    else:
        return "Rest"

def generate_rest_day_details(rest_day_type):
    if rest_day_type == "Active Recovery":
        return "Light activity such as walking, stretching, or easy cycling for 20-30 minutes."
    elif rest_day_type == "Strength Training":
        return "Running-specific strength exercises for 30-45 minutes."
    else:
        return "Complete rest day to allow full recovery."

def pace_str_to_minutes(pace_str):
    try:
        parts = pace_str.split(':')
        return int(parts[0]) + int(parts[1]) / 60.0
    except Exception as e:
        logger.error("Error parsing pace string: %s", e)
        return None

# -------------------------
# API Endpoints
# -------------------------

@app.route('/api/overall-sleep', methods=['GET'])
def overall_sleep():
    today = date.today().isoformat()
    overall_value, avg_over_night_hrv, body_battery_change, training_readiness = get_recovery_metrics(today)
    result = {
        "overallSleepScore": overall_value,
        "avgOvernightHrv": avg_over_night_hrv,
        "bodyBatteryChange": body_battery_change,
        "trainingReadiness": training_readiness
    }
    return jsonify(result)

@app.route('/api/race-predictions', methods=['GET'])
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

    # Calculate periodization parameters
    try:
        race_date_obj = date.fromisoformat(race_date)
    except Exception as e:
        return jsonify({"error": "Invalid raceDate format. Use YYYY-MM-DD."}), 400
    weeks_until_race = max(0, (race_date_obj - date.today()).days // 7)
    total_weeks = get_training_plan_length(training_distance, experience_level)
    current_week = max(1, total_weeks - weeks_until_race)
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
        f"Additionally, I am in week {current_week} of a {total_weeks}-week training plan aimed at {training_goal} (experience level: {experience_level}). "
        f"My race phase is '{race_phase}', and my recommended weekly mileage is approximately {round(weekly_mileage,1)} km. "
        f"Based on this information, in 400 words or less, please recommend one run type (Recovery, Easy, Threshold, or Long Run) with the appropriate pace, duration, "
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
def generate_schedule():
    """
    Generates a personalized weekly running schedule based on user input.
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
    workout_types = generate_workout_types(race_phase, current_week, total_weeks, run_days, training_distance)

    # Find the index of the long run day in running_days
    try:
        long_run_index_in_running_days = running_days.index(long_run_day)
    except ValueError:
        return jsonify({"error": "Long run day not found in running days"}), 400
    
    workout_types.insert(long_run_index_in_running_days, workout_types.pop(0))

    schedule = []
    final_schedule = {}
    hard_workouts = ["LongRun", "Threshold", "Intervals"]

    #1. Create all workouts
    all_workouts = []
    for i, workout in enumerate(workout_types):
        all_workouts.append(workout)

    # Ensure we only have one LongRun in the workout types
    long_run_count = all_workouts.count("LongRun")
    if long_run_count > 1:
        # Remove extra LongRuns, replace with Easy runs
        for i in range(long_run_count - 1):
            long_run_index = all_workouts.index("LongRun", 1 if i > 0 else 0)
            all_workouts[long_run_index] = "Easy"

    #2. Place Long Run first
    final_schedule = {}
    final_schedule[long_run_day] = "LongRun"
    # Remove LongRun from all_workouts if it exists (as we've already placed it)
    if "LongRun" in all_workouts:
        all_workouts.remove("LongRun")

    #3. Determine optimal rest day distribution
    rest_days_needed = 7 - run_days
    hard_workouts = ["Threshold", "Intervals"]  # Remove LongRun as it's already placed

    # Find the long run index in week_days
    long_run_index = week_days.index(long_run_day)

    # We'll score each potential rest day configuration
    potential_rest_configs = []

    # Get all remaining available days (excluding long run day)
    available_days = [day for day in week_days if day != long_run_day]

    # For each possible combination of rest days
    from itertools import combinations
    for rest_combo in combinations(available_days, rest_days_needed):
        score = 0
    '''
    # Prefer rest day after long run (existing)
    next_day_after_long = week_days[(long_run_index + 1) % 7]
    if next_day_after_long in rest_combo:
        score += 10
    '''
    # **Prefer rest day BEFORE long run (NEW)**
    day_before_long = week_days[(long_run_index - 1) % 7] # Use modulo for week wrap-around
    if day_before_long in rest_combo:
        score += 8  # Slightly lower score than after, adjust weighting as needed


    # Avoid consecutive rest days (existing)
    for i in range(len(week_days)):
        current = week_days[i]
        next_day = week_days[(i + 1) % 7]
        if current in rest_combo and next_day in rest_combo:
            score -= 8

        
        # Prefer even distribution (check spaces between rest days)
        rest_indices = [week_days.index(day) for day in rest_combo]
        rest_indices.sort()
        
        if len(rest_indices) > 1:
            gaps = []
            for i in range(len(rest_indices)):
                next_idx = (i + 1) % len(rest_indices)
                gap = (rest_indices[next_idx] - rest_indices[i]) % 7
                gaps.append(gap)
            
            # Calculate variance - lower is better (more even distribution)
            mean_gap = sum(gaps) / len(gaps)
            variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            
            # Award points for more even distribution
            score += 10 / (1 + variance)
        
        potential_rest_configs.append((rest_combo, score))

    # Choose the best rest day configuration
    potential_rest_configs.sort(key=lambda x: x[1], reverse=True)
    best_rest_days = potential_rest_configs[0][0]

    # Assign rest days
    for day in best_rest_days:
        final_schedule[day] = "Rest"

    # Get remaining run days that need workouts assigned
    remaining_run_days = [day for day in week_days if day != long_run_day and day not in best_rest_days]

    #4. Place hard workouts with optimal spacing
    remaining_hard_workouts = [w for w in all_workouts if w in hard_workouts]

    if remaining_hard_workouts:
        # Find optimal days for hard workouts (maximize distance from long run and each other)
        day_scores = []
        for day in remaining_run_days:
            # Calculate distance from long run day
            day_idx = week_days.index(day)
            long_idx = week_days.index(long_run_day)
            dist = min((day_idx - long_idx) % 7, (long_idx - day_idx) % 7)
            day_scores.append((day, dist))
        
        # Sort by distance (descending)
        day_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Place hard workouts
        for hard_workout in remaining_hard_workouts:
            if day_scores:
                best_day = day_scores[0][0]
                final_schedule[best_day] = hard_workout
                all_workouts.remove(hard_workout)
                remaining_run_days.remove(best_day)
                day_scores.pop(0)

    #5. Place recovery runs after hard workouts including long run (Prioritized for Long Run)
    hard_days = [day for day, workout_type in final_schedule.items()
                if workout_type in ["LongRun", "Threshold", "Intervals"]]

    recovery_workouts_available = [w for w in all_workouts if w == "Recovery"]
    recovery_workouts_placed = 0

    # Prioritize Recovery after Long Run FIRST
    if final_schedule.get(long_run_day) == "LongRun": # Check if LongRun is actually scheduled
        long_run_idx = week_days.index(long_run_day)
        next_day_idx = (long_run_idx + 1) % 7
        next_day_after_long_run = week_days[next_day_idx]

        if run_days >= 3: # Or your chosen threshold
            if "Recovery" in all_workouts:
                final_schedule[next_day_after_long_run] = "Recovery"
                all_workouts.remove("Recovery")
                remaining_run_days.remove(next_day_after_long_run)
                recovery_workouts_placed += 1


    # Then place Recovery after other hard workouts (Threshold, Intervals)
    for hard_day in hard_days:
        if hard_day == long_run_day: # Skip long run as we already handled it above
            continue

        hard_idx = week_days.index(hard_day)
        next_day_idx = (hard_idx + 1) % 7
        next_day = week_days[next_day_idx]

        if next_day in remaining_run_days and recovery_workouts_placed < len(recovery_workouts_available):
            if "Recovery" in all_workouts:
                final_schedule[next_day] = "Recovery"
                all_workouts.remove("Recovery")
                remaining_run_days.remove(next_day)
                recovery_workouts_placed += 1

    #6. Fill remaining run days with other workouts or Easy runs
    for day in remaining_run_days:
        if all_workouts:
            final_schedule[day] = all_workouts.pop(0)
        else:
            final_schedule[day] = "Easy"

    #7. Final check - ensure only one long run is scheduled
    long_run_count = sum(1 for workout_type in final_schedule.values() if workout_type == "LongRun")
    if long_run_count > 1:
        # This should never happen with the fixes above, but as a safety measure
        for day, workout_type in final_schedule.items():
            if workout_type == "LongRun" and day != long_run_day:
                final_schedule[day] = "Easy"

    for day in week_days:
        if day in final_schedule:
            run_type = final_schedule[day]
            if run_type in ["Recovery", "Easy", "Threshold", "Intervals", "LongRun"]:
                target_pace = running_paces.get(run_type, "N/A")
                pace_minutes = pace_str_to_minutes(target_pace) if target_pace != "N/A" else None
                distance_factor = get_distance_factor(run_type, race_phase, current_week, total_weeks)
                run_distance = round(weekly_mileage * distance_factor, 1)
                run_duration = round(run_distance * pace_minutes) if pace_minutes else "N/A"
                workout_details = generate_workout_details(run_type, race_phase, current_week, total_weeks, training_distance, run_distance)
                intensity_score = calculate_intensity_score(run_type, run_distance, pace_minutes)
                schedule.append({
                    "Day": day,
                    "WorkoutType": run_type,
                    "WorkoutDetails": workout_details,
                    "TargetPace": target_pace + " per km" if target_pace != "N/A" else target_pace,
                    "Duration": f"{run_duration} minutes" if run_duration != "N/A" else "N/A",
                    "Distance": f"{run_distance} km",
                    "IntensityScore": intensity_score
                })
            else:
                schedule.append({
                    "Day": day,
                    "WorkoutType": run_type,
                    "WorkoutDetails": generate_rest_day_details(run_type),
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
    # Ensure Garmin client is initialized before running
    GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
    GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
    garmin_client = init_api(GARMIN_USERNAME, GARMIN_PASSWORD)
    app.run(debug=True, port=8080)
