import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib

from models import db, MLModel, Activity, UserPerformanceMetrics

logger = logging.getLogger(__name__)

ml_bp = Blueprint('ml', __name__)

def save_model(user_id, model_type, model, accuracy=None, data_count=None):
    """Save ML model to disk and record in database."""
    # Create models directory if it doesn't exist
    os.makedirs('models', exist_ok=True)
    
    # Get latest version for this model type
    latest = MLModel.query.filter_by(
        user_id=user_id, model_type=model_type
    ).order_by(MLModel.model_version.desc()).first()
    
    version = 1
    if latest:
        version = latest.model_version + 1
    
    # Create filename and path
    filename = f"user_{user_id}_{model_type}_v{version}.pkl"
    filepath = os.path.join('models', filename)
    
    # Save the model
    joblib.dump(model, filepath)
    
    # Record in database
    model_record = MLModel(
        user_id=user_id,
        model_type=model_type,
        model_version=version,
        model_file_path=filepath,
        accuracy_score=accuracy,
        training_data_count=data_count
    )
    
    db.session.add(model_record)
    db.session.commit()
    
    return model_record

def load_model(user_id, model_type):
    """Load the latest model for a user."""
    model_record = MLModel.query.filter_by(
        user_id=user_id, model_type=model_type
    ).order_by(MLModel.model_version.desc()).first()
    
    if not model_record:
        return None
    
    try:
        return joblib.load(model_record.model_file_path)
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None

def export_user_data_for_ml(user_id):
    """Export all user data for ML processing."""
    # Get all performance metrics
    metrics = UserPerformanceMetrics.query.filter_by(user_id=user_id).order_by(UserPerformanceMetrics.date).all()
    
    # Get all activities
    activities = Activity.query.filter_by(user_id=user_id).order_by(Activity.activity_date).all()
    
    # Create DataFrames
    metrics_df = pd.DataFrame([{
        'date': m.date,
        'vo2max': m.vo2max,
        'race_prediction_5k': m.race_prediction_5k,
        'race_prediction_10k': m.race_prediction_10k, 
        'race_prediction_half': m.race_prediction_half,
        'race_prediction_full': m.race_prediction_full,
        'avg_stress': m.avg_stress,
        'max_stress': m.max_stress,
        'resting_heart_rate': m.resting_heart_rate,
        'sleep_score': m.sleep_score,
        'body_battery_change': m.body_battery_change,
        'overnight_hrv': m.overnight_hrv,
        'training_readiness': m.training_readiness
    } for m in metrics])
    
    activities_df = pd.DataFrame([{
        'date': activity.activity_date.date(),
        'type': activity.activity_type,
        'distance': activity.distance,
        'duration': activity.duration,
        'avg_hr': activity.avg_hr,
        'max_hr': activity.max_hr,
        'avg_pace': activity.avg_pace,
        'calories': activity.calories,
        'training_effect_aerobic': activity.training_effect_aerobic,
        'training_effect_anaerobic': activity.training_effect_anaerobic
    } for activity in activities])
    
    return {
        'metrics': metrics_df,
        'activities': activities_df
    }

def prepare_training_impact_data(user_id):
    """
    Prepare data for training a model to predict how workouts impact recovery.
    Links each activity with the next day's recovery metrics.
    """
    # Get user data
    data = export_user_data_for_ml(user_id)
    activities_df = data['activities']
    metrics_df = data['metrics']
    
    # Make sure date columns are datetime
    activities_df['date'] = pd.to_datetime(activities_df['date'])
    metrics_df['date'] = pd.to_datetime(metrics_df['date'])
    
    # For each activity, find the next day's recovery metrics
    training_data = []
    
    for idx, activity in activities_df.iterrows():
        activity_date = activity['date']
        next_day = activity_date + pd.Timedelta(days=1)
        
        # Find metrics for the next day
        next_day_metrics = metrics_df[metrics_df['date'] == next_day]
        
        if not next_day_metrics.empty:
            # Create a training example
            training_example = {
                'activity_date': activity_date,
                'distance': activity['distance'],
                'duration': activity['duration'],
                'avg_hr': activity['avg_hr'],
                'training_effect_aerobic': activity['training_effect_aerobic'],
                'next_day_sleep_score': next_day_metrics.iloc[0]['sleep_score'],
                'next_day_hrv': next_day_metrics.iloc[0]['overnight_hrv'],
                'next_day_readiness': next_day_metrics.iloc[0]['training_readiness']
            }
            
            training_data.append(training_example)
    
    return pd.DataFrame(training_data)

def train_recovery_model(user_id):
    """Train a model to predict recovery metrics after a workout."""
    # Prepare training data
    df = prepare_training_impact_data(user_id)
    
    # Check if we have enough data
    if len(df) < 20:
        logger.info(f"Not enough data to train model for user {user_id}. Need at least 20 samples.")
        return None
    
    # Prepare features and targets
    X = df[['distance', 'duration', 'avg_hr', 'training_effect_aerobic']]
    y_sleep = df['next_day_sleep_score']
    y_readiness = df['next_day_readiness']
    
    # Train models
    sleep_model = RandomForestRegressor(n_estimators=100, random_state=42)
    readiness_model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    # Split data
    X_train, X_test, y_sleep_train, y_sleep_test = train_test_split(X, y_sleep, test_size=0.2, random_state=42)
    _, _, y_readiness_train, y_readiness_test = train_test_split(X, y_readiness, test_size=0.2, random_state=42)
    
    # Fit models
    sleep_model.fit(X_train, y_sleep_train)
    readiness_model.fit(X_train, y_readiness_train)
    
    # Evaluate
    sleep_accuracy = sleep_model.score(X_test, y_sleep_test)
    readiness_accuracy = readiness_model.score(X_test, y_readiness_test)
    
    # Save models
    save_model(user_id, 'sleep_impact', sleep_model, sleep_accuracy, len(df))
    save_model(user_id, 'readiness_impact', readiness_model, readiness_accuracy, len(df))
    
    logger.info(f"Models trained for user {user_id}:")
    logger.info(f"Sleep impact model accuracy: {sleep_accuracy:.2f}")
    logger.info(f"Readiness impact model accuracy: {readiness_accuracy:.2f}")
    
    return {
        'sleep_model': sleep_model,
        'readiness_model': readiness_model,
        'sleep_accuracy': sleep_accuracy,
        'readiness_accuracy': readiness_accuracy
    }

def train_race_prediction_model(user_id):
    """Train a model to predict race times based on recent training."""
    # Get user data
    data = export_user_data_for_ml(user_id)
    activities_df = data['activities']
    metrics_df = data['metrics']
    
    # Not enough data for reliable predictions
    if len(activities_df) < 30 or len(metrics_df) < 10:
        logger.info(f"Not enough data to train race prediction model for user {user_id}")
        return None
    
    # Create features from training history
    # Group activities by week
    activities_df['date'] = pd.to_datetime(activities_df['date'])
    activities_df['week'] = activities_df['date'].dt.isocalendar().week
    activities_df['year'] = activities_df['date'].dt.isocalendar().year
    
    # Calculate weekly training metrics
    weekly_metrics = activities_df.groupby(['year', 'week']).agg({
        'distance': 'sum',
        'duration': 'sum',
        'training_effect_aerobic': 'mean',
        'date': 'max'  # Get the last day of the week
    }).reset_index()
    
    # Calculate rolling averages (4-week training load)
    weekly_metrics = weekly_metrics.sort_values(['year', 'week'])
    weekly_metrics['rolling_distance'] = weekly_metrics['distance'].rolling(4).mean()
    weekly_metrics['rolling_duration'] = weekly_metrics['duration'].rolling(4).mean()
    weekly_metrics['rolling_te'] = weekly_metrics['training_effect_aerobic'].rolling(4).mean()
    
    # Join with race prediction metrics
    weekly_metrics['date'] = pd.to_datetime(weekly_metrics['date'])
    metrics_df['date'] = pd.to_datetime(metrics_df['date'])
    
    merged_data = pd.merge_asof(
        weekly_metrics.sort_values('date'), 
        metrics_df.sort_values('date')[['date', 'race_prediction_5k', 'vo2max']], 
        on='date',
        direction='forward'
    )
    
    # Drop rows with missing values
    merged_data = merged_data.dropna(subset=['rolling_distance', 'race_prediction_5k', 'vo2max'])
    
    if len(merged_data) < 10:
        logger.info(f"Not enough merged data points for user {user_id}")
        return None
    
    # Prepare training data
    X = merged_data[['rolling_distance', 'rolling_duration', 'rolling_te', 'vo2max']]
    y = merged_data['race_prediction_5k']  # Predict 5K time in seconds
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    accuracy = model.score(X_test, y_test)
    
    # Save model
    save_model(user_id, 'race_prediction', model, accuracy, len(merged_data))
    
    logger.info(f"Race prediction model trained for user {user_id} with accuracy: {accuracy:.2f}")
    
    return {
        'model': model,
        'accuracy': accuracy
    }

def recommend_workout(user_id):
    """Generate workout recommendations based on current recovery status."""
    # Import here to avoid circular imports
    from garmin_data import batch_fetch_garmin_data, daily_update_user_data, process_performance_metrics
    from app import garmin_client
    
    # Get today's recovery metrics
    today = date.today()
    metrics = UserPerformanceMetrics.query.filter_by(
        user_id=user_id, date=today
    ).first()
    
    if not metrics:
        # Try to fetch metrics now
        results = batch_fetch_garmin_data(user_id, today.isoformat(), garmin_client)
        if results:
            metrics = process_performance_metrics(user_id, results, today.isoformat())
    
    # Load the user's trained models
    readiness_model = load_model(user_id, 'readiness_impact')
    
    # Define potential workouts
    potential_workouts = [
        {
            'name': 'Recovery Run',
            'description': 'Easy effort, conversation pace',
            'distance': 5000,  # 5K in meters
            'duration': 1800,  # 30 minutes
            'avg_hr': 130,
            'training_effect_aerobic': 1.5,
            'intensity': 'low'
        },
        {
            'name': 'Base Building Run',
            'description': 'Steady effort, building endurance',
            'distance': 8000,  # 8K in meters
            'duration': 2700,  # 45 minutes
            'avg_hr': 145,
            'training_effect_aerobic': 2.5,
            'intensity': 'medium-low'
        },
        {
            'name': 'Tempo Run',
            'description': 'Comfortably hard effort, improves lactate threshold',
            'distance': 10000,  # 10K in meters
            'duration': 3600,  # 60 minutes
            'avg_hr': 160,
            'training_effect_aerobic': 3.5,
            'intensity': 'medium-high'
        },
        {
            'name': 'Interval Session',
            'description': 'High intensity repeats with recovery',
            'distance': 8000,  # 8K including warm-up/cool-down
            'duration': 2700,  # 45 minutes
            'avg_hr': 165,
            'training_effect_aerobic': 4.5,
            'intensity': 'high'
        }
    ]
    
    # If we have a model, predict recovery impact of each workout
    if readiness_model and metrics:
        current_readiness = metrics.training_readiness
        
        for workout in potential_workouts:
            # Format features to match training data
            features = [[
                workout['distance'], 
                workout['duration'], 
                workout['avg_hr'], 
                workout['training_effect_aerobic']
            ]]
            
            # Predict next day's readiness after this workout
            predicted_readiness = readiness_model.predict(features)[0]
            workout['predicted_readiness_impact'] = predicted_readiness
            
        # Find suitable workouts based on current recovery
        if current_readiness >= 70:
            # Well recovered - can handle higher intensity
            suitable_workouts = [w for w in potential_workouts if w['intensity'] in ['medium-high', 'high']]
            if not suitable_workouts:
                suitable_workouts = potential_workouts
        elif current_readiness >= 50:
            # Moderately recovered - medium intensity
            suitable_workouts = [w for w in potential_workouts if w['intensity'] in ['medium-low', 'medium-high']]
            if not suitable_workouts:
                suitable_workouts = potential_workouts
        else:
            # Low recovery - stick to easy workouts
            suitable_workouts = [w for w in potential_workouts if w['intensity'] in ['low', 'medium-low']]
            if not suitable_workouts:
                suitable_workouts = [potential_workouts[0]]  # Recovery run
                
        # Select workout with best recovery impact from suitable options
        recommended = max(suitable_workouts, key=lambda w: w.get('predicted_readiness_impact', 0))
        
        return {
            'current_readiness': current_readiness,
            'recommended_workout': recommended['name'],
            'workout_description': recommended['description'],
            'expected_duration': recommended['duration'] // 60,  # Convert to minutes
            'expected_distance': recommended['distance'] // 1000,  # Convert to km
            'expected_readiness_tomorrow': recommended.get('predicted_readiness_impact'),
            'rationale': f"Based on your current recovery status ({current_readiness:.1f}/100) and predicted impact on tomorrow's readiness."
        }
    
    # Fallback if no model or metrics available
    else:
        # Use a simple rule-based approach
        # Get recent activities 
        last_week = today - timedelta(days=7)
        recent_activities = Activity.query.filter(
            Activity.user_id == user_id,
            Activity.activity_date >= datetime.combine(last_week, datetime.min.time())
        ).order_by(Activity.activity_date.desc()).all()
        
        # Check if last workout was high intensity
        high_intensity_recent = False
        if recent_activities:
            last_activity = recent_activities[0]
            if last_activity.training_effect_aerobic and last_activity.training_effect_aerobic > 3.0:
                high_intensity_recent = True
        
        # Alternate between easy and harder workouts
        if high_intensity_recent:
            recommended = potential_workouts[0]  # Recovery run
        else:
            recommended = potential_workouts[2]  # Tempo run
        
        return {
            'recommended_workout': recommended['name'],
            'workout_description': recommended['description'],
            'expected_duration': recommended['duration'] // 60,
            'expected_distance': recommended['distance'] // 1000,
            'rationale': "Based on your recent training pattern. For more personalized recommendations, continue syncing with Garmin."
        }

def get_training_insights(user_id):
    """Generate training insights based on historical data."""
    # Get user data
    data = export_user_data_for_ml(user_id)
    activities_df = data['activities']
    metrics_df = data['metrics']
    
    if len(activities_df) < 10:
        return {
            'insights': [
                "Continue logging your runs to receive personalized training insights.",
                "We recommend at least 3 runs per week for optimal improvement."
            ]
        }
    
    insights = []
    
    # Calculate weekly mileage
    activities_df['date'] = pd.to_datetime(activities_df['date'])
    activities_df['week'] = activities_df['date'].dt.isocalendar().week
    activities_df['year'] = activities_df['date'].dt.isocalendar().year
    
    weekly_distance = activities_df.groupby(['year', 'week'])['distance'].sum() / 1000  # Convert to km
    avg_weekly_distance = weekly_distance.mean()
    max_weekly_distance = weekly_distance.max()
    
    insights.append(f"Your average weekly distance is {avg_weekly_distance:.1f} km, with a peak of {max_weekly_distance:.1f} km.")
    
    # Analyze workout variety
    workout_counts = activities_df.groupby('training_effect_aerobic').size()
    easy_runs = workout_counts[workout_counts.index < 2.5].sum() if len(workout_counts[workout_counts.index < 2.5]) > 0 else 0
    medium_runs = workout_counts[(workout_counts.index >= 2.5) & (workout_counts.index < 3.5)].sum() if len(workout_counts[(workout_counts.index >= 2.5) & (workout_counts.index < 3.5)]) > 0 else 0
    hard_runs = workout_counts[workout_counts.index >= 3.5].sum() if len(workout_counts[workout_counts.index >= 3.5]) > 0 else 0
    
    total_runs = len(activities_df)
    easy_pct = easy_runs / total_runs * 100 if total_runs > 0 else 0
    
    if easy_pct < 70 and total_runs >= 10:
        insights.append(f"Only {easy_pct:.1f}% of your runs are easy runs. Consider adding more easy runs - most elite runners do 80% easy, 20% hard.")
    
    # Look at training consistency
    activities_df = activities_df.sort_values('date')
    activities_df['days_since_last'] = activities_df['date'].diff().dt.days
    
    avg_gap = activities_df['days_since_last'].mean()
    max_gap = activities_df['days_since_last'].max()
    
    if avg_gap > 3 and total_runs >= 5:
        insights.append(f"Your average gap between runs is {avg_gap:.1f} days. More consistent training (every 1-2 days) may improve results.")
    
    if max_gap > 7 and total_runs >= 5:
        insights.append(f"Your longest gap between runs was {max_gap:.0f} days. Try to avoid long breaks for optimal fitness development.")
    
    # Analyze performance trends if we have VO2max data
    if 'vo2max' in metrics_df.columns and not metrics_df['vo2max'].isnull().all():
        metrics_df = metrics_df.sort_values('date')
        first_vo2 = metrics_df['vo2max'].iloc[0] if not pd.isna(metrics_df['vo2max'].iloc[0]) else None
        last_vo2 = metrics_df['vo2max'].iloc[-1] if not pd.isna(metrics_df['vo2max'].iloc[-1]) else None
        
        if first_vo2 and last_vo2:
            change = last_vo2 - first_vo2
            if change > 0:
                insights.append(f"Your VO2max has improved by {change:.1f} points, showing your training is effective!")
            elif change < 0:
                insights.append(f"Your VO2max has decreased by {abs(change):.1f} points. This might be due to inconsistent training or other factors.")
    
    return {
        'insights': insights,
        'stats': {
            'total_runs': total_runs,
            'avg_weekly_distance': avg_weekly_distance,
            'max_weekly_distance': max_weekly_distance,
            'easy_run_percentage': easy_pct,
            'avg_days_between_runs': avg_gap
        }
    }

# API Endpoints
@ml_bp.route('/api/workout-recommendation', methods=['GET'])
@login_required
def workout_recommendation_endpoint():
    """Get personalized workout recommendation."""
    try:
        recommendation = recommend_workout(current_user.id)
        return jsonify(recommendation)
    except Exception as e:
        logger.error(f"Error generating workout recommendation: {e}")
        return jsonify({"error": "Failed to generate recommendation"}), 500

@ml_bp.route('/api/training-insights', methods=['GET'])
@login_required
def training_insights_endpoint():
    """Get personalized training insights."""
    try:
        insights = get_training_insights(current_user.id)
        return jsonify(insights)
    except Exception as e:
        logger.error(f"Error generating training insights: {e}")
        return jsonify({"error": "Failed to generate insights"}), 500

@ml_bp.route('/api/train-models', methods=['POST'])
@login_required
def train_models_endpoint():
    """Manually trigger ML model training."""
    try:
        # Train recovery model
        recovery_results = train_recovery_model(current_user.id)
        
        # Train race prediction model
        race_results = train_race_prediction_model(current_user.id)
        
        return jsonify({
            "message": "Models trained successfully",
            "recovery_model": {
                "trained": recovery_results is not None,
                "accuracy": recovery_results['sleep_accuracy'] if recovery_results else None
            },
            "race_model": {
                "trained": race_results is not None,
                "accuracy": race_results['accuracy'] if race_results else None
            }
        })
    except Exception as e:
        logger.error(f"Error training models: {e}")
        return jsonify({"error": "Failed to train models"}), 500

@ml_bp.route('/api/recent-running-activities', methods=['GET'])
@login_required
def recent_running_activities():
    """Get user's recent running activities."""
    try:
        # Get recent activities from the database
        recent_activities = Activity.query.filter_by(
            user_id=current_user.id
        ).order_by(Activity.activity_date.desc()).limit(10).all()
        
        activities_list = []
        for activity in recent_activities:
            # Print debug info about the pace
            logger.info(f"Activity {activity.garmin_activity_id} pace: {activity.avg_pace}")
            
            activities_list.append({
                "id": activity.garmin_activity_id,
                "type": activity.activity_type,
                "date": activity.activity_date.isoformat(),
                "distance": activity.distance,
                "duration": activity.duration,
                "averagePace": activity.avg_pace,
                "averageHR": activity.avg_hr,
                "calories": activity.calories
            })
        
        return jsonify(activities_list)
    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        return jsonify({"error": "Failed to fetch activities"}), 500

@ml_bp.route('/api/activity/<activity_id>', methods=['GET'])
@login_required
def activity_details(activity_id):
    """Get detailed information about a specific running activity."""
    try:
        # Get from database
        activity = Activity.query.filter_by(garmin_activity_id=activity_id).first()
        
        # If not in database, try to fetch and store
        if not activity:
            # Import here to avoid circular imports
            from garmin_data import process_and_store_activity
            from app import garmin_client
            
            activity = process_and_store_activity(current_user.id, garmin_client.get_activity_details(activity_id), garmin_client)
                
        if not activity:
            return jsonify({"error": "Activity not found"}), 404
                
        # Return activity details
        details = json.loads(activity.details_json) if activity.details_json else {}
            
        response = {
            "id": activity.garmin_activity_id,
            "type": activity.activity_type,
            "date": activity.activity_date.isoformat(),
            "distance": activity.distance,
            "duration": activity.duration,
            "avgHR": activity.avg_hr,
            "maxHR": activity.max_hr,
            "avgPace": activity.avg_pace,
            "calories": activity.calories,
            "trainingEffectAerobic": activity.training_effect_aerobic,
            "trainingEffectAnaerobic": activity.training_effect_anaerobic,
            "detailedData": details
        }
                
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching activity details: {e}")
        return jsonify({"error": "Failed to fetch activity details"}), 500

@ml_bp.route('/api/training-data', methods=['GET'])
@login_required
def training_data_endpoint():
    """Get comprehensive training data for the user."""
    try:
        # Import here to avoid circular imports
        from garmin_data import daily_update_user_data
        from app import garmin_client
        
        # Fetch the latest data from Garmin
        today = date.today().isoformat()
        daily_update_user_data(current_user.id, today, garmin_client)
        
        # Get performance metrics for the last 30 days
        thirty_days_ago = date.today() - timedelta(days=30)
        metrics = UserPerformanceMetrics.query.filter(
            UserPerformanceMetrics.user_id == current_user.id,
            UserPerformanceMetrics.date >= thirty_days_ago
        ).order_by(UserPerformanceMetrics.date).all()
        
        # Format metrics for response
        metrics_data = [{
            "date": m.date.isoformat(),
            "vo2max": m.vo2max,
            "sleep_score": m.sleep_score,
            "training_readiness": m.training_readiness,
            "resting_heart_rate": m.resting_heart_rate
        } for m in metrics]
        
        # Get race predictions
        latest_metrics = UserPerformanceMetrics.query.filter_by(
            user_id=current_user.id
        ).order_by(UserPerformanceMetrics.date.desc()).first()
        
        race_predictions = {}
        if latest_metrics:
            # Import the time conversion functions
            from schedule import seconds_to_time_str
            
            # Convert seconds back to time format
            if latest_metrics.race_prediction_5k:
                race_predictions['5k'] = seconds_to_time_str(latest_metrics.race_prediction_5k)
            
            if latest_metrics.race_prediction_10k:
                race_predictions['10k'] = seconds_to_time_str(latest_metrics.race_prediction_10k)
            
            if latest_metrics.race_prediction_half:
                race_predictions['half_marathon'] = seconds_to_time_str(latest_metrics.race_prediction_half)
            
            if latest_metrics.race_prediction_full:
                race_predictions['marathon'] = seconds_to_time_str(latest_metrics.race_prediction_full)
        
        # Get recent activities
        recent_activities = Activity.query.filter_by(
            user_id=current_user.id
        ).order_by(Activity.activity_date.desc()).limit(10).all()
        
        activities_data = [{
            "id": a.garmin_activity_id,
            "date": a.activity_date.isoformat(),
            "type": a.activity_type,
            "distance": a.distance,
            "duration": a.duration,
            "avg_hr": a.avg_hr
        } for a in recent_activities]
        
        return jsonify({
            "metrics": metrics_data,
            "race_predictions": race_predictions,
            "recent_activities": activities_data
        })
    except Exception as e:
        logger.error(f"Error getting training data: {e}")
        return jsonify({"error": "Failed to retrieve training data"}), 500