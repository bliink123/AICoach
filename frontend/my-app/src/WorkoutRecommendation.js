import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Grid,
  Box,
  Button,
  Divider,
  Paper,
  LinearProgress,
  Chip
} from '@mui/material';
import DirectionsRunIcon from '@mui/icons-material/DirectionsRun';
import TimerIcon from '@mui/icons-material/Timer';
import StraightenIcon from '@mui/icons-material/Straighten';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import BatteryChargingFullIcon from '@mui/icons-material/BatteryChargingFull';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8080';

const WorkoutRecommendation = () => {
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sleepData, setSleepData] = useState(null);

  const fetchRecommendation = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/workout-recommendation`);
      setRecommendation(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching workout recommendation:", err);
      setError("Failed to fetch workout recommendation. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const fetchSleepData = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/overall-sleep`);
      setSleepData(response.data);
    } catch (err) {
      console.error("Error fetching sleep data:", err);
    }
  };

  useEffect(() => {
    fetchRecommendation();
    fetchSleepData();
  }, []);

  const getReadinessColor = (readiness) => {
    if (!readiness) return '#9e9e9e';
    if (readiness >= 80) return '#4caf50';
    if (readiness >= 60) return '#8bc34a';
    if (readiness >= 40) return '#ffc107';
    return '#f44336';
  };

  const getIntensityLabel = (workout) => {
    if (!workout) return { label: 'Unknown', color: 'default' };
    
    const intensityMap = {
      'Recovery Run': { label: 'Low', color: 'success' },
      'Easy Run': { label: 'Low-Medium', color: 'info' },
      'Base Building Run': { label: 'Medium', color: 'primary' },
      'Tempo Run': { label: 'Medium-High', color: 'warning' },
      'Interval Session': { label: 'High', color: 'error' }
    };
    
    return intensityMap[workout] || { label: 'Medium', color: 'primary' };
  };

  return (
    <Card variant="outlined">
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <DirectionsRunIcon sx={{ mr: 1 }} /> ML-Powered Workout Recommendation
        </Typography>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error" sx={{ p: 2 }}>
            {error}
          </Typography>
        ) : recommendation ? (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Paper elevation={3} sx={{ p: 3, borderRadius: 2, mb: 3 }}>
                <Typography variant="h4" component="div" gutterBottom>
                  {recommendation.recommended_workout}
                </Typography>
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Chip 
                    label={getIntensityLabel(recommendation.recommended_workout).label + " Intensity"} 
                    color={getIntensityLabel(recommendation.recommended_workout).color}
                    sx={{ mr: 1 }}
                  />
                  {sleepData && sleepData.trainingReadiness && (
                    <Chip 
                      icon={<BatteryChargingFullIcon />} 
                      label={`Readiness: ${sleepData.trainingReadiness}`} 
                      sx={{ backgroundColor: getReadinessColor(sleepData.trainingReadiness), color: 'white' }}
                    />
                  )}
                </Box>
                
                <Typography variant="body1" color="text.secondary" paragraph>
                  {recommendation.workout_description}
                </Typography>
                
                <Divider sx={{ my: 2 }} />
                
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <StraightenIcon sx={{ mr: 1, color: 'primary.main' }} />
                      <Typography variant="body1">
                        <strong>Distance:</strong> {recommendation.expected_distance} km
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <TimerIcon sx={{ mr: 1, color: 'primary.main' }} />
                      <Typography variant="body1">
                        <strong>Duration:</strong> {recommendation.expected_duration} min
                      </Typography>
                    </Box>
                  </Grid>
                  {recommendation.expected_readiness_tomorrow && (
                    <Grid item xs={12} md={6}>
                      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>Expected Readiness Tomorrow:</strong> {recommendation.expected_readiness_tomorrow.toFixed(1)}
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={recommendation.expected_readiness_tomorrow} 
                          sx={{ 
                            height: 10, 
                            borderRadius: 5,
                            backgroundColor: '#e0e0e0',
                            '& .MuiLinearProgress-bar': {
                              backgroundColor: getReadinessColor(recommendation.expected_readiness_tomorrow)
                            }
                          }}
                        />
                      </Box>
                    </Grid>
                  )}
                </Grid>
              </Paper>
            </Grid>
            
            <Grid item xs={12}>
              <Paper elevation={2} sx={{ p: 2, borderRadius: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
                <Typography variant="h6" gutterBottom>
                  <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Recommendation Rationale
                </Typography>
                <Typography variant="body1">
                  {recommendation.rationale}
                </Typography>
              </Paper>
            </Grid>
            
            {sleepData && (
              <Grid item xs={12} mt={2}>
                <Typography variant="subtitle1" gutterBottom>
                  Recovery Metrics Influencing Today's Recommendation:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {sleepData.overallSleepScore && (
                    <Chip 
                      label={`Sleep Score: ${sleepData.overallSleepScore}`} 
                      color={sleepData.overallSleepScore > 70 ? "success" : sleepData.overallSleepScore > 50 ? "warning" : "error"}
                    />
                  )}
                  {sleepData.avgOvernightHrv && (
                    <Chip 
                      label={`HRV: ${sleepData.avgOvernightHrv}`} 
                      color={sleepData.avgOvernightHrv > 70 ? "success" : sleepData.avgOvernightHrv > 50 ? "warning" : "error"}
                    />
                  )}
                  {sleepData.bodyBatteryChange && (
                    <Chip 
                      label={`Battery Change: ${sleepData.bodyBatteryChange}`}
                      color={sleepData.bodyBatteryChange > 70 ? "success" : sleepData.bodyBatteryChange > 50 ? "warning" : "error"}
                    />
                  )}
                </Box>
              </Grid>
            )}
          </Grid>
        ) : (
          <Typography variant="body1" sx={{ p: 2 }}>
            No workout recommendation available. Please ensure your Garmin data is synced.
          </Typography>
        )}
        
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={fetchRecommendation} 
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            Refresh Recommendation
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default WorkoutRecommendation;