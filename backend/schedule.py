import json
import logging
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, ScheduleCache

logger = logging.getLogger(__name__)

schedule_bp = Blueprint('schedule', __name__)

# Helper functions for schedule generation
def get_training_plan_length(training_distance, experience_level):
    """
    Returns recommended training plan length (in weeks) based on distance and experience level.
    """
    base_length = {"5K": 12, "10K": 16, "HalfMarathon": 20, "Marathon": 24}.get(training_distance, 16)
    experience_multiplier = {"beginner": 1.0, "intermediate": 1.0, "advanced": 0.9}.get(experience_level, 1.0)
    return round(base_length * experience_multiplier)

def determine_race_phase(weeks_until_race, training_distance):
    """
    Determines the race phase based on the weeks remaining until the race.
    - More than 10 weeks: "base" phase (building an aerobic foundation)
    - 6 to 10 weeks: "build" phase (gradually increasing quality and volume)
    - 3 to 5 weeks: "peak" phase (highest workload before taper)
    - Less than 3 weeks: "taper" phase (significantly reducing mileage for recovery)
    """
    if weeks_until_race > 10:
        return "base"
    elif 6 <= weeks_until_race <= 10:
        return "build"
    elif 3 <= weeks_until_race < 6:
        return "peak"
    else:
        return "taper"

def get_default_weekly_mileage(training_distance, experience_level, training_goal):
    """
    Returns the default weekly mileage (in km) based on the target race distance.
    These defaults are aligned with common training plans:
      - Marathon: ~50 km per week (typical for a beginner/intermediate)
      - Half Marathon: ~35 km per week
      - 10K: ~25 km per week
      - 5K: ~20 km per week
    These values may be further adjusted based on the runner's experience and training goal.
    """
    defaults = {
        "Marathon": 50,
        "Half Marathon": 35,
        "10K": 25,
        "5K": 20
    }
    
    # Apply experience level adjustments
    mileage = defaults.get(training_distance, 25)
    if experience_level == "beginner":
        mileage *= 0.85  # 15% less for beginners
    elif experience_level == "advanced":
        mileage *= 1.2   # 20% more for advanced runners
    
    # Apply training goal adjustments
    if training_goal == "finish":
        mileage *= 0.9   # 10% less for completion focus
    elif training_goal == "compete":
        mileage *= 1.1   # 10% more for competition focus
    
    return mileage

def calculate_phase_multiplier(race_phase, current_week, total_weeks):
    """
    Calculates a multiplier for weekly mileage based on the current training phase:
      - Base Phase: Gradually increases from 0.8 up to ~1.0 by the end of the phase.
      - Build Phase: Slight increase in workload, reaching ~1.1 by the end.
      - Peak Phase: Maintains a high workload (e.g., multiplier of 1.1).
      - Taper Phase: Gradual reduction to approximately 60% of peak workload (multiplier ~0.6).
    """
    if race_phase == "base":
        return 0.8 + (0.2 * current_week / total_weeks)
    elif race_phase == "build":
        return 1.0 + (0.1 * current_week / total_weeks)
    elif race_phase == "peak":
        return 1.1
    elif race_phase == "taper":
        # Linear taper from 1.0 at the start of taper down to 0.6 at the end
        return 1.0 - (0.4 * (current_week / total_weeks))
    return 1.0

def get_run_days_simple(week_days, run_days, long_run_day):
    """Simple method to get a set of run days, ensuring long_run_day is included."""
    selected_run_days = []
    if long_run_day not in week_days:
        raise ValueError("long_run_day must be in week_days")
    selected_run_days.append(long_run_day)
    for day in week_days:
        if day != long_run_day and len(selected_run_days) < run_days:
            selected_run_days.append(day)
    return sorted(selected_run_days, key=lambda d: week_days.index(d))

def generate_workout_types_rule_based_phase_aware(race_phase, current_week, total_weeks, run_days, training_distance):
    """Generates workout types based on rules and race phase."""
    workout_rules_phase_aware = {
        "base": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Easy"],
            4: ["LongRun", "Easy", "Easy", "Easy"],
            5: ["LongRun", "Easy", "Easy", "Easy", "Easy"],
            6: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy"],
            7: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy", "Easy"],
        },
        "build": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Threshold"],
            4: ["LongRun", "Easy", "Easy", "Threshold"],
            5: ["LongRun", "Easy", "Easy", "Threshold", "Easy"],
            6: ["LongRun", "Easy", "Easy", "Threshold", "Easy", "Easy"],
            7: ["LongRun", "Easy", "Easy", "Threshold", "Easy", "Easy", "Easy"],
        },
        "peak": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Intervals"],
            4: ["LongRun", "Easy", "Intervals", "Threshold"],
            5: ["LongRun", "Easy", "Intervals", "Threshold", "Easy"],
            6: ["LongRun", "Easy", "Intervals", "Threshold", "Easy", "Recovery"],
            7: ["LongRun", "Easy", "Intervals", "Threshold", "Easy", "Recovery", "Easy"],
        },
        "taper": {
            1: ["LongRun"],
            2: ["LongRun", "Easy"],
            3: ["LongRun", "Easy", "Easy"],
            4: ["LongRun", "Easy", "Easy", "Easy"],
            5: ["LongRun", "Easy", "Easy", "Easy", "Easy"],
            6: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy"],
            7: ["LongRun", "Easy", "Easy", "Easy", "Easy", "Easy", "Easy"],
        },
    }
    if race_phase in workout_rules_phase_aware and run_days in workout_rules_phase_aware[race_phase]:
        return workout_rules_phase_aware[race_phase][run_days]
    else:
        return ["Easy"] * run_days

def get_distance_factor(run_type, race_phase, current_week, total_weeks):
    """Calculate what percentage of weekly mileage this run type should be based on phase and week"""
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
    """Generate detailed descriptions for each workout based on type, phase, and training distance."""
    if run_type == "LongRun":
        if race_phase == "base":
            return f"Long run: {distance:.1f} km at an easy, conversational pace to build endurance."
        elif race_phase == "build":
            return f"Long run: {distance:.1f} km with the last 3-5 km at marathon pace."
        elif race_phase == "peak":
            if training_distance == "Marathon":
                return f"Long run: {distance:.1f} km with the middle {round(distance*0.5):.1f} km at race pace."
            else:
                return f"Long run: {distance:.1f} km with a progressive effort, finishing strong."
        else:
            return f"Shorter long run: {distance:.1f} km at an easy pace."
    elif run_type == "Recovery":
        return f"Recovery run: {distance:.1f} km at a very relaxed pace."
    elif run_type == "Easy":
        return f"Easy run: {distance:.1f} km at a comfortable, steady pace."
    elif run_type == "Threshold":
        if race_phase == "base":
            return f"Threshold: {distance:.1f} km including 2-3 x 5 min at threshold pace."
        elif race_phase == "build":
            return f"Threshold: {distance:.1f} km with 20 minutes at threshold pace."
        elif race_phase == "peak":
            return f"Threshold: {distance:.1f} km with 2 x 15 min at threshold pace."
        else:
            return f"Threshold: {distance:.1f} km with 10 minutes at threshold pace."
    elif run_type == "Intervals":
        if training_distance in ["5K", "10K"]:
            if race_phase == "base":
                return f"Intervals: {distance:.1f} km with 6-8 x 400m at 5K effort."
            elif race_phase == "build":
                return f"Intervals: {distance:.1f} km with 5-6 x 800m at 5K effort."
            elif race_phase == "peak":
                return f"Intervals: {distance:.1f} km with 5 x 1000m at 5K effort."
            else:
                return f"Intervals: {distance:.1f} km with 3-4 x 400m at 5K effort."
        else:
            if race_phase == "build":
                return f"Intervals: {distance:.1f} km with 6-8 x 400m at 10K effort."
            elif race_phase == "peak":
                return f"Intervals: {distance:.1f} km with 3-4 x 1 mile at 10K effort."
            else:
                return f"Intervals: {distance:.1f} km with 4-5 x 400m at 10K effort."
    return f"{run_type} run: {distance:.1f} km."

def generate_rest_day_details(rest_day_type):
    """
    Returns a detailed description for rest day activities.
    """
    if rest_day_type == "Active Recovery":
        return "Light activity such as walking, stretching, or easy cycling for 20-30 minutes."
    elif rest_day_type == "Strength Training":
        return "Running-specific strength exercises for 30-45 minutes."
    else:
        return "Complete rest day to allow full recovery."

def calculate_intensity_score(run_type, distance, pace_minutes):
    """
    Calculates an intensity score based on run type, distance, and pace.
    """
    if pace_minutes == "N/A" or pace_minutes is None:
        return 0
    intensity_factor = {"Recovery": 0.7, "Easy": 0.8, "Threshold": 1.0, "Intervals": 1.2, "LongRun": 0.85}.get(run_type, 0.8)
    return round(distance * intensity_factor * pace_minutes)

def improve_run_schedule_rule_based(workout_types, long_run_day, week_days, run_days):
    """
    Improves run schedule by assigning workout types to specific days.
    LongRun is always placed on long_run_day, and rest days are auto-assigned.
    """
    final_schedule = {}
    final_schedule[long_run_day] = "LongRun"
    logger.debug(f"Initial schedule with LongRun: {final_schedule}")

    rest_days_needed = 7 - run_days
    logger.debug(f"Rest days needed: {rest_days_needed}")
    available_days = [day for day in week_days if day != long_run_day]
    logger.debug(f"Available days for rest: {available_days}")
    rest_days = []
    if rest_days_needed >= 2:
        logger.debug("Trying to assign preferred rest days (Monday, Friday)")
        for preferred in ["Monday", "Friday"]:
            if preferred in available_days and len(rest_days) < rest_days_needed:
                rest_days.append(preferred)
                available_days.remove(preferred)
                logger.debug(f"  Assigned preferred rest day: {preferred}, rest_days: {rest_days}, available_days: {available_days}")
    logger.debug(f"Rest days after preferred assignment: {rest_days}")
    logger.debug(f"Available days after preferred assignment: {available_days}")

    while len(rest_days) < rest_days_needed and available_days:
        rest_days.append(available_days.pop())
        logger.debug(f"  Assigned remaining rest day: {rest_days[-1]}, rest_days: {rest_days}, available_days: {available_days}")
    logger.debug(f"Final rest days assigned: {rest_days}")

    for day in rest_days:
        final_schedule[day] = "Rest"
    logger.debug(f"Schedule after rest days: {final_schedule}")

    remaining_run_days = [day for day in week_days if day not in final_schedule]
    logger.debug(f"Remaining run days for workouts: {remaining_run_days}")
    workout_types_filtered = [wt for wt in workout_types if wt != "LongRun"]
    logger.debug(f"Workout types to assign (excluding LongRun): {workout_types_filtered}")
    for idx, day in enumerate(remaining_run_days):
        workout_type = "Easy" # Default if workouts run out
        if idx < len(workout_types_filtered):
            workout_type = workout_types_filtered[idx]
        final_schedule[day] = workout_type
        logger.debug(f"  Assigned workout {workout_type} to {day}")
    logger.debug(f"Final schedule: {final_schedule}")
    return final_schedule

def time_str_to_seconds(time_str):
    """Convert time string (MM:SS or HH:MM:SS) to seconds."""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        logger.error("Error converting time string to seconds: %s", e)
        return None

def seconds_to_time_str(seconds):
    """Convert seconds to time string (MM:SS or HH:MM:SS)."""
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    else:
        hours = int(seconds // 3600)
        remaining = seconds % 3600
        minutes = int(remaining // 60)
        secs = int(remaining % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"

def pace_str_to_minutes(pace_str):
    """
    Converts a pace string (mm:ss) to minutes (float).
    Example: "5:30" -> 5.5
    """
    try:
        if pace_str == "N/A":
            return None
        minutes, seconds = map(int, pace_str.split(':'))
        return minutes + (seconds / 60.0)
    except Exception as e:
        logger.error(f"Error parsing pace string: {pace_str} - {e}")
        return None

def calculate_running_paces(race_prediction_str, training_distance="5K"):
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

@schedule_bp.route('/api/schedule', methods=['POST'])
@login_required
def generate_schedule_endpoint():
    # Import here to avoid circular imports
    from garmin_data import batch_fetch_garmin_data
    
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

    # Check for cached schedule
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

    # Get race prediction using Garmin data
    from app import garmin_client  # Import here to avoid circular imports
    today_str = today.isoformat()
    
    results = batch_fetch_garmin_data(current_user.id, today_str, garmin_client)
    race_data = results.get('race_predictions', {})
    
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
    
    if prediction_seconds is None:
        return jsonify({"error": "Race prediction data not found"}), 404
        
    race_prediction = seconds_to_time_str(prediction_seconds)
    running_paces = calculate_running_paces(race_prediction, training_distance)
    
    # Generate workout types and schedule
    running_days = get_run_days_simple(week_days, run_days, long_run_day)
    workout_types = generate_workout_types_rule_based_phase_aware(race_phase, current_week, total_weeks, run_days, training_distance)
    final_schedule = improve_run_schedule_rule_based(workout_types, long_run_day, week_days, run_days)

    # Create detailed schedule
    schedule = []
    for day in week_days:
        if day in final_schedule:
            run_type = final_schedule[day]
            if run_type in ["Recovery", "Easy", "Threshold", "Intervals", "LongRun", "Rest", "Active Recovery", "Strength Training"]:
                target_pace = running_paces.get(run_type, "N/A")
                pace_minutes = pace_str_to_minutes(target_pace) if target_pace != "N/A" else None
                distance_factor = get_distance_factor(run_type, race_phase, current_week, total_weeks)
                run_distance = round(weekly_mileage * distance_factor, 1)
                run_duration = round(run_distance * pace_minutes) if pace_minutes else "N/A"
                if run_type in ["Rest", "Active Recovery", "Strength Training"]:
                    workout_details = generate_rest_day_details(run_type)
                else:
                    workout_details = generate_workout_details(run_type, race_phase, current_week, total_weeks, training_distance, run_distance)
                intensity_score = calculate_intensity_score(run_type, run_distance, pace_minutes)
                schedule.append({
                    "Day": day,
                    "WorkoutType": run_type,
                    "WorkoutDetails": workout_details,
                    "TargetPace": target_pace + " per km" if target_pace != "N/A" else target_pace,
                    "Duration": f"{run_duration} minutes" if run_duration != "N/A" else "N/A",
                    "Distance": f"{run_distance} km" if run_type not in ["Rest", "Active Recovery", "Strength Training"] else "N/A",
                    "IntensityScore": intensity_score if run_type not in ["Rest", "Active Recovery", "Strength Training"] else 0
                })
            else:
                schedule.append({
                    "Day": day,
                    "WorkoutType": run_type,
                    "WorkoutDetails": "Workout details not available.",
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
    
    # Cache the schedule
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