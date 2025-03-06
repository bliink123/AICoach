import os
import logging
from datetime import date
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from google import genai
from models import db

logger = logging.getLogger(__name__)

ai_coach_bp = Blueprint('ai_coach', __name__)

# Helper functions
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

@ai_coach_bp.route('/api/overall-sleep', methods=['GET'])
@login_required
def overall_sleep():
    """Get sleep and recovery metrics."""
    # Import here to avoid circular imports
    from garmin_data import batch_fetch_garmin_data
    from app import garmin_client
    
    today_str = date.today().isoformat()
    results = batch_fetch_garmin_data(current_user.id, today_str, garmin_client)
    
    # Extract needed metrics
    sleep_data = results.get('sleep', {})
    readiness_data = results.get('training_readiness', {})
    
    overall_value, avg_over_night_hrv, body_battery_change = None, None, None
    
    if isinstance(sleep_data, dict):
        daily = sleep_data.get("dailySleepDTO", {})
        overall_value = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_over_night_hrv = daily.get("avgOvernightHrv") or sleep_data.get("avgOvernightHrv")
        body_battery_change = daily.get("bodyBatteryChange") or sleep_data.get("bodyBatteryChange")
    
    training_readiness = None
    if isinstance(readiness_data, dict):
        training_readiness = readiness_data.get("score")
    
    return jsonify({
        "overallSleepScore": overall_value,
        "avgOvernightHrv": avg_over_night_hrv,
        "bodyBatteryChange": body_battery_change,
        "trainingReadiness": training_readiness
    })

@ai_coach_bp.route('/api/race-predictions', methods=['GET'])
@login_required
def race_predictions():
    """Get race predictions from Garmin data."""
    # Import here to avoid circular imports
    from garmin_data import batch_fetch_garmin_data
    from app import garmin_client
    from schedule import seconds_to_time_str
    
    today_str = date.today().isoformat()
    results = batch_fetch_garmin_data(current_user.id, today_str, garmin_client)
    race_data = results.get('race_predictions', {})
    
    if not race_data:
        return jsonify({"error": "Failed to retrieve race predictions"}), 500

    output = {}
    
    if isinstance(race_data, dict):
        output["time5K"] = seconds_to_time_str(race_data.get("time5K")) if race_data.get("time5K") else "N/A"
        output["time10K"] = seconds_to_time_str(race_data.get("time10K")) if race_data.get("time10K") else "N/A"
        output["timeHalfMarathon"] = seconds_to_time_str(race_data.get("timeHalfMarathon")) if race_data.get("timeHalfMarathon") else "N/A"
        output["timeMarathon"] = seconds_to_time_str(race_data.get("timeMarathon")) if race_data.get("timeMarathon") else "N/A"

    return jsonify(output)

@ai_coach_bp.route('/api/ai-coach', methods=['GET'])
@login_required
def ai_coach():
    """Get AI coach recommendations."""
    # Import needed functions from other modules
    from garmin_data import batch_fetch_garmin_data
    from schedule import (
        determine_race_phase, 
        get_training_plan_length,
        get_default_weekly_mileage,
        calculate_phase_multiplier,
        calculate_running_paces,
        seconds_to_time_str
    )
    from app import garmin_client
    
    # Get parameters from request
    training_distance = request.args.get("distance", "5K")
    experience_level = request.args.get("experienceLevel", "intermediate").lower()
    training_goal = request.args.get("trainingGoal", "pr").lower()
    race_date = request.args.get("raceDate", date.today().isoformat())
    race_phase = request.args.get("racePhase", "auto").lower()
    today_str = date.today().isoformat()

    # Fetch Garmin data
    results = batch_fetch_garmin_data(current_user.id, today_str, garmin_client)
    
    # Extract metrics
    sleep_data = results.get('sleep', {})
    readiness_data = results.get('training_readiness', {})
    race_data = results.get('race_predictions', {})
    
    overall_value, avg_over_night_hrv, body_battery_change = None, None, None
    
    if isinstance(sleep_data, dict):
        daily = sleep_data.get("dailySleepDTO", {})
        overall_value = daily.get("sleepScores", {}).get("overall", {}).get("value")
        avg_over_night_hrv = daily.get("avgOvernightHrv") or sleep_data.get("avgOvernightHrv")
        body_battery_change = daily.get("bodyBatteryChange") or sleep_data.get("bodyBatteryChange")
    
    training_readiness = None
    if isinstance(readiness_data, dict):
        training_readiness = readiness_data.get("score")
    
    # Get race prediction
    prediction_seconds = None
    if isinstance(race_data, dict):
        if training_distance == "5K":
            prediction_seconds = race_data.get("time5K")
        elif training_distance == "10K":
            prediction_seconds = race_data.get("time10K")
        elif training_distance == "HalfMarathon":
            prediction_seconds = race_data.get("timeHalfMarathon")
        elif training_distance == "Marathon":
            prediction_seconds = race_data.get("timeMarathon")
    
    if any(v is None for v in [overall_value, avg_over_night_hrv, body_battery_change, training_readiness, prediction_seconds]):
        logger.error("Required data not found")
        return jsonify({"error": "Required data not found"}), 404
    
    race_prediction = seconds_to_time_str(prediction_seconds)
    
    # Calculate training phase and weekly mileage
    try:
        race_date_obj = date.fromisoformat(race_date)
    except Exception as e:
        return jsonify({"error": "Invalid raceDate format. Use YYYY-MM-DD."}), 400
    
    weeks_until_race = max(0, (race_date_obj - date.today()).days // 7)
    
    if race_phase == "auto":
        race_phase = determine_race_phase(weeks_until_race, training_distance)
    
    total_weeks = get_training_plan_length(training_distance, experience_level)
    current_week = max(1, total_weeks - weeks_until_race)
    default_mileage = get_default_weekly_mileage(training_distance, experience_level, training_goal)
    phase_multiplier = calculate_phase_multiplier(race_phase, current_week, total_weeks)
    weekly_mileage = default_mileage * phase_multiplier

    # Calculate running paces
    running_paces = calculate_running_paces(race_prediction, training_distance)
    
    # Determine run type based on recovery metrics
    run_type = determine_run_type(overall_value, avg_over_night_hrv, body_battery_change, training_readiness)
    target_pace = running_paces.get(run_type) if running_paces and run_type in running_paces else None

    # Generate AI recommendation using Gemini
    # Calculate base pace for the prompt
    base_pace_seconds = prediction_seconds / {"5K": 5, "10K": 10, "HalfMarathon": 21.1, "Marathon": 42.2}.get(training_distance, 5)
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

    # Call Gemini API
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

    # Return combined response
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