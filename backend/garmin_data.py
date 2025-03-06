import os
import json
import logging
import time
from datetime import datetime, date, timedelta
from garminconnect import Garmin
from models import db, GarminDataCache, GarminDataArchive, Activity, UserPerformanceMetrics, User

logger = logging.getLogger(__name__)

# Set up token storage file path
TOKEN_STORE = os.path.expanduser("~/.garmin_tokens.json")

def get_credentials():
    email = input("Enter your Garmin email: ")
    password = input("Enter your Garmin password: ")
    return email, password

def get_mfa():
    return input("Enter MFA code: ")

def init_api(email=None, password=None):
    """Initialize Garmin API client"""
    try:
        logger.info("Attempting token login using tokens from '%s'.", TOKEN_STORE)
        garmin_client = Garmin()  # Use tokens
        garmin_client.login(TOKEN_STORE)
    except Exception as err:
        logger.error("Token login failed: %s", err)
        print(f"Tokens not present or expired. Logging in with credentials. Tokens will be stored in '{TOKEN_STORE}'.")
        try:
            if not email or not password:
                email, password = get_credentials()
            garmin_client = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin_client.login()
            garmin_client.garth.dump(TOKEN_STORE)
            logger.info("Tokens stored in '%s'.", TOKEN_STORE)
        except Exception as err:
            logger.error("Credential login failed: %s", err)
            return None
    return garmin_client

def is_cache_stale(cache_entry):
    """Check if a cache entry is stale based on data type."""
    if not cache_entry:
        return True
        
    cache_age = datetime.now() - cache_entry.last_updated
    
    # Different freshness rules for different data types
    if cache_entry.data_type in ['sleep', 'training_readiness', 'heart_rate', 'stress']:
        # These change daily - fresh for 4 hours if today's data, otherwise keep
        today = date.today()
        if cache_entry.data_date == today:
            return cache_age.total_seconds() > 4 * 3600  # 4 hours
        return False  # Historical data doesn't get stale
    
    elif cache_entry.data_type in ['vo2max', 'race_predictions']:
        # These change less frequently - fresh for 24 hours
        return cache_age.total_seconds() > 24 * 3600  # 24 hours
    
    # Default - 12 hours
    return cache_age.total_seconds() > 12 * 3600  # 12 hours

def store_garmin_data(user_id, data_type, date_str, data):
    """Store data in both cache and archive."""
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    data_json = json.dumps(data)
    
    # Write to cache (for API performance)
    cache_entry = GarminDataCache.query.filter_by(
        user_id=user_id, data_type=data_type, data_date=target_date
    ).first()
    
    if cache_entry:
        cache_entry.data_json = data_json
        cache_entry.last_updated = datetime.utcnow()
    else:
        cache_entry = GarminDataCache(
            user_id=user_id,
            data_type=data_type,
            data_date=target_date,
            data_json=data_json
        )
        db.session.add(cache_entry)
    
    # Always write to archive (for ML)
    # Check if we already have this exact data archived
    archive_entry = GarminDataArchive.query.filter_by(
        user_id=user_id, data_type=data_type, data_date=target_date
    ).first()
    
    if not archive_entry:
        archive_entry = GarminDataArchive(
            user_id=user_id,
            data_type=data_type,
            data_date=target_date,
            data_json=data_json
        )
        db.session.add(archive_entry)
    
    db.session.commit()

def batch_fetch_garmin_data(user_id, date_str=None, garmin_client=None):
    """
    Fetch multiple data types from Garmin API in one coordinated batch.
    If date_str is None, fetches today's data.
    """
    if date_str is None:
        date_str = date.today().isoformat()
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    results = {}
    
    try:
        # Check what we already have in cache for this date
        cache_records = GarminDataCache.query.filter_by(
            user_id=user_id, 
            data_date=target_date
        ).all()
        
        cached_types = {record.data_type: record for record in cache_records}
        
        # Fetch sleep data if needed
        if 'sleep' not in cached_types or is_cache_stale(cached_types['sleep']):
            logger.info(f"Fetching sleep data for user {user_id} on {date_str}")
            sleep_data = garmin_client.get_sleep_data(date_str)
            if sleep_data:
                results['sleep'] = sleep_data
                store_garmin_data(user_id, 'sleep', date_str, sleep_data)
        else:
            results['sleep'] = json.loads(cached_types['sleep'].data_json)
            
        # Fetch training readiness if needed
        if 'training_readiness' not in cached_types or is_cache_stale(cached_types['training_readiness']):
            logger.info(f"Fetching training readiness for user {user_id} on {date_str}")
            try:
                readiness_data = garmin_client.get_training_readiness(date_str)
                if readiness_data:
                    # Process the data to ensure we extract the score properly
                    processed_data = {}
                    
                    if isinstance(readiness_data, dict):
                        processed_data = readiness_data
                    elif isinstance(readiness_data, list) and readiness_data:
                        # If it's a list, use the first item
                        processed_data = readiness_data[0] if isinstance(readiness_data[0], dict) else {}
                    
                    results['training_readiness'] = processed_data
                    store_garmin_data(user_id, 'training_readiness', date_str, processed_data)
            except Exception as e:
                logger.error(f"Error fetching training readiness: {e}")
        else:
            results['training_readiness'] = json.loads(cached_types['training_readiness'].data_json)
        
        # Fetch race predictions if needed
        if 'race_predictions' not in cached_types or is_cache_stale(cached_types['race_predictions']):
            logger.info(f"Fetching race predictions for user {user_id}")
            try:
                race_predictions = garmin_client.get_race_predictions()
                if race_predictions:
                    # Process the data to ensure we handle both list and dictionary formats
                    processed_data = {}
                    
                    if isinstance(race_predictions, dict):
                        processed_data = race_predictions
                        logger.info("Race prediction data (dict): %s", json.dumps(processed_data, indent=4))
                    elif isinstance(race_predictions, list) and race_predictions:
                        # If it's a list, extract relevant data from the first item
                        processed_data = race_predictions[0] if isinstance(race_predictions[0], dict) else {}
                        logger.info("Race prediction data (list->dict): %s", json.dumps(processed_data, indent=4))
                    
                    results['race_predictions'] = processed_data
                    store_garmin_data(user_id, 'race_predictions', date_str, processed_data)
            except Exception as e:
                logger.error(f"Error fetching race predictions: {e}")
        else:
            results['race_predictions'] = json.loads(cached_types['race_predictions'].data_json)

        # Fetch VO2max data if needed
        if 'vo2max' not in cached_types or is_cache_stale(cached_types['vo2max']):
            logger.info(f"Fetching VO2max data for user {user_id}")
            try:
                vo2max_data = garmin_client.get_user_profile()
                if vo2max_data and 'userVO2Max' in vo2max_data:
                    results['vo2max'] = vo2max_data
                    store_garmin_data(user_id, 'vo2max', date_str, vo2max_data)
            except Exception as e:
                logger.error(f"Error fetching VO2max data: {e}")
        else:
            results['vo2max'] = json.loads(cached_types['vo2max'].data_json)
        
        # Fetch heart rate data if needed
        if 'heart_rate' not in cached_types or is_cache_stale(cached_types['heart_rate']):
            logger.info(f"Fetching heart rate data for user {user_id} on {date_str}")
            try:
                heart_rate_data = garmin_client.get_heart_rates(date_str)
                if heart_rate_data:
                    results['heart_rate'] = heart_rate_data
                    store_garmin_data(user_id, 'heart_rate', date_str, heart_rate_data)
            except Exception as e:
                logger.error(f"Error fetching heart rate data: {e}")
        else:
            results['heart_rate'] = json.loads(cached_types['heart_rate'].data_json)
        
        # Fetch stress data if needed
        if 'stress' not in cached_types or is_cache_stale(cached_types['stress']):
            logger.info(f"Fetching stress data for user {user_id} on {date_str}")
            try:
                stress_data = garmin_client.get_stress_data(date_str)
                if stress_data:
                    results['stress'] = stress_data
                    store_garmin_data(user_id, 'stress', date_str, stress_data)
            except Exception as e:
                logger.error(f"Error fetching stress data: {e}")
        else:
            results['stress'] = json.loads(cached_types['stress'].data_json)
            
        # Only fetch activities for today or recent days
        today = date.today()
        if (today - target_date).days <= 7:
            # For activities, we check the Activity model instead of cache
            recent_activities = Activity.query.filter(
                Activity.user_id == user_id,
                Activity.activity_date >= datetime.combine(target_date, datetime.min.time()),
                Activity.activity_date < datetime.combine(target_date + timedelta(days=1), datetime.min.time())
            ).all()
            
            if not recent_activities:
                # Only fetch activities if we don't have them already
                try:
                    # Use a 30-day window instead of a specific day
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    start_timestamp = int(start_date.timestamp() * 1000)
                    end_timestamp = int(end_date.timestamp() * 1000)
                    
                    logger.info(f"Fetching activities for user {user_id} from {start_date} to {end_date}")
                    activities = garmin_client.get_activities(0, 10)  # Simpler call to get 10 most recent
                    
                    if activities:
                        results['activities'] = activities
                        # Process and store activities
                        for activity in activities:
                            process_and_store_activity(user_id, activity, garmin_client)
                    else:
                        logger.info(f"No activities found for user {user_id}")
                        results['activities'] = []
                except Exception as e:
                    logger.error(f"Error fetching activities: {e}")
                    results['activities'] = []
            else:
                results['activities'] = [
                    json.loads(activity.details_json) for activity in recent_activities
                    if activity.details_json
                ]
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch fetch: {e}")
        return results  # Return whatever we managed to fetch

def process_and_store_activity(user_id, activity_data, garmin_client=None):
    """Process an activity from Garmin API and store in our database."""
    # Check if we already have this activity
    activity_id = activity_data.get("activityId")
    existing = Activity.query.filter_by(garmin_activity_id=activity_id).first()
    if existing:
        return existing
        
    # Filter for running activities
    activity_type = activity_data.get("activityType", {}).get("typeKey", "").lower()
    running_types = ["running", "treadmill_running", "trail_running", "track_running", "indoor_running"]
    
    if not any(run_type in activity_type for run_type in running_types):
        return None  # Not a running activity
    
    # Create activity record with basic data
    activity_date = datetime.strptime(activity_data.get("startTimeLocal"), "%Y-%m-%d %H:%M:%S")
    
    # Log the keys in activity_data to see what's available
    logger.info(f"Activity data keys: {activity_data.keys()}")
    
    # Check for pace in different possible formats
    avg_pace = None
    
    # Option 1: Direct pace value
    if "averagePace" in activity_data:
        avg_pace = activity_data.get("averagePace")
        logger.info(f"Found direct pace: {avg_pace}")
    
    # Option 2: Pace might be in a nested structure
    if avg_pace is None and "summaryDTO" in activity_data:
        summary = activity_data.get("summaryDTO", {})
        if "averagePace" in summary:
            avg_pace = summary.get("averagePace")
            logger.info(f"Found pace in summaryDTO: {avg_pace}")
    
    # Option 3: Calculate from distance and duration if available
    if avg_pace is None:
        distance = activity_data.get("distance")
        duration = activity_data.get("duration")
        
        if distance and duration and distance > 0:
            avg_pace = duration / distance  # seconds per meter
            logger.info(f"Calculated pace: {avg_pace} s/m")
    
    new_activity = Activity(
        user_id=user_id,
        garmin_activity_id=activity_id,
        activity_type=activity_type,
        activity_date=activity_date,
        distance=activity_data.get("distance"),
        duration=activity_data.get("duration"),
        avg_hr=activity_data.get("averageHR"),
        avg_pace=avg_pace,
        calories=activity_data.get("calories")
    )
    
    # Try to get detailed data if basic record doesn't have what we need
    if not new_activity.avg_hr or 'trainingEffect' not in activity_data:
        try:
            details = garmin_client.get_activity_details(activity_id)
            if details:
                # Update with more complete data
                new_activity.max_hr = details.get("maxHR")
                new_activity.training_effect_aerobic = details.get("aerobicTrainingEffect")
                new_activity.training_effect_anaerobic = details.get("anaerobicTrainingEffect")
                new_activity.details_json = json.dumps(details)
        except Exception as e:
            logger.error(f"Error fetching details for activity {activity_id}: {e}")
    else:
        # Basic data already has what we need
        new_activity.details_json = json.dumps(activity_data)
    
    # Save to database
    db.session.add(new_activity)
    db.session.commit()
    
    return new_activity

def process_performance_metrics(user_id, results, date_str):
    """Extract and store performance metrics from API results."""
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Check if we already have metrics for this date
    existing = UserPerformanceMetrics.query.filter_by(
        user_id=user_id, date=target_date
    ).first()
    
    if existing:
        metrics = existing
    else:
        metrics = UserPerformanceMetrics(user_id=user_id, date=target_date)
    
    # Extract VO2max
    if 'vo2max' in results:
        vo2max_data = results['vo2max']
        if isinstance(vo2max_data, dict):
            metrics.vo2max = vo2max_data.get('userVO2Max')
    
    # Extract race predictions
    if 'race_predictions' in results:
        race_data = results['race_predictions']
        if isinstance(race_data, dict):
            # Store times in seconds for consistency
            if 'time5K' in race_data:
                metrics.race_prediction_5k = race_data.get('time5K')
            if 'time10K' in race_data:
                metrics.race_prediction_10k = race_data.get('time10K')
            if 'timeHalfMarathon' in race_data:
                metrics.race_prediction_half = race_data.get('timeHalfMarathon')
            if 'timeMarathon' in race_data:
                metrics.race_prediction_full = race_data.get('timeMarathon')
    
    # Extract stress data
    if 'stress' in results:
        stress_data = results['stress']
        if isinstance(stress_data, dict):
            metrics.avg_stress = stress_data.get('avgStressLevel')
            metrics.max_stress = stress_data.get('maxStressLevel')
    
    # Extract heart rate data
    if 'heart_rate' in results:
        hr_data = results['heart_rate']
        if isinstance(hr_data, dict):
            metrics.resting_heart_rate = hr_data.get('restingHeartRate')
    
    # Extract sleep and recovery data
    if 'sleep' in results:
        sleep_data = results['sleep']
        if isinstance(sleep_data, dict):
            daily_sleep = sleep_data.get('dailySleepDTO', {})
            metrics.sleep_score = daily_sleep.get('sleepScores', {}).get('overall', {}).get('value')
            metrics.overnight_hrv = daily_sleep.get('avgOvernightHrv')
            metrics.body_battery_change = daily_sleep.get('bodyBatteryChange')
    
    # Extract training readiness
    if 'training_readiness' in results:
        readiness_data = results['training_readiness']
        if isinstance(readiness_data, dict):
            metrics.training_readiness = readiness_data.get('score')
    
    # Save to database
    if not existing:
        db.session.add(metrics)
    db.session.commit()
    
    return metrics

def daily_update_user_data(user_id, date_str=None, garmin_client=None):
    """Complete daily update of all user data."""
    if date_str is None:
        date_str = date.today().isoformat()
    
    # Fetch all data from Garmin API
    results = batch_fetch_garmin_data(user_id, date_str, garmin_client)
    
    # Process performance metrics
    if results:
        process_performance_metrics(user_id, results, date_str)
    
    return results

def cleanup_old_cache():
    """Remove cache entries older than 90 days."""
    cutoff_date = date.today() - timedelta(days=90)
    old_entries = GarminDataCache.query.filter(GarminDataCache.data_date < cutoff_date).all()
    
    for entry in old_entries:
        db.session.delete(entry)
    
    db.session.commit()
    logger.info(f"Cleaned up {len(old_entries)} old cache entries")

def update_all_users_data(garmin_client):
    """
    Daily scheduled task to update all users' data once.
    Run this early morning to get previous day's sleep and activity data.
    """
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    active_users = User.query.filter_by(is_active=True).all()
    
    for user in active_users:
        try:
            daily_update_user_data(user.id, yesterday, garmin_client)
            # Sleep a bit between users to avoid hitting API limits
            time.sleep(5)
        except Exception as e:
            logger.error(f"Failed to update data for user {user.id}: {e}")