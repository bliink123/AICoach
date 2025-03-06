import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Box,
  Button,
  Grid,
  Paper,
  Chip,
  Divider,
  IconButton,
  Container,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DirectionsRunIcon from '@mui/icons-material/DirectionsRun';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SpeedIcon from '@mui/icons-material/Speed';
import HeartBrokenIcon from '@mui/icons-material/HeartBroken';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import TimerIcon from '@mui/icons-material/Timer';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import FitnessCenterIcon from '@mui/icons-material/FitnessCenter';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TimelineIcon from '@mui/icons-material/Timeline';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8080';

const ActivityDetail = () => {
  const { activityId } = useParams();
  const navigate = useNavigate();
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchActivityDetail = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${API_BASE_URL}/api/activity/${activityId}`);
        setActivity(response.data);
        setError(null);
      } catch (err) {
        console.error("Error fetching activity details:", err);
        setError("Failed to fetch activity details. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    if (activityId) {
      fetchActivityDetail();
    }
  }, [activityId]);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const formatTime = (seconds) => {
    if (!seconds) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${remainingSeconds}s`;
    } else {
      return `${minutes}m ${remainingSeconds}s`;
    }
  };

  const formatPace = (paceInSecondsPerMeter) => {
    if (!paceInSecondsPerMeter) return 'N/A';
    
    // Convert to min/km
    const secondsPerKm = paceInSecondsPerMeter * 1000;
    const minutes = Math.floor(secondsPerKm / 60);
    const seconds = Math.floor(secondsPerKm % 60);
    
    return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
  };

  const formatDistance = (meters) => {
    if (!meters) return 'N/A';
    return `${(meters / 1000).toFixed(2)} km`;
  };

  const getActivityTypeLabel = (type) => {
    if (!type) return 'Run';
    
    // Convert snake_case to Title Case
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getTrainingEffectColor = (value) => {
    if (!value) return 'default';
    
    if (value < 2) return 'success'; // Easy recovery
    if (value < 3) return 'info';    // Maintains fitness
    if (value < 4) return 'warning'; // Improves fitness
    return 'error';                  // Highly improving
  };

  const getTrainingEffectDescription = (value, isAerobic) => {
    if (!value) return 'No data';
    
    if (isAerobic) {
      if (value < 1.0) return 'No aerobic benefit';
      if (value < 2.0) return 'Minor aerobic benefit';
      if (value < 3.0) return 'Maintaining aerobic fitness';
      if (value < 4.0) return 'Improving aerobic fitness';
      return 'Highly improving aerobic fitness';
    } else {
      if (value < 1.0) return 'No anaerobic benefit';
      if (value < 2.0) return 'Minor anaerobic benefit';
      if (value < 3.0) return 'Maintaining anaerobic fitness';
      if (value < 4.0) return 'Improving anaerobic fitness';
      return 'Highly improving anaerobic fitness';
    }
  };

  return (
    <Container sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton 
          aria-label="back"
          onClick={() => navigate(-1)}
          sx={{ mr: 2 }}
        >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">
          Activity Details
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      ) : activity ? (
        <>
          <Card variant="outlined" sx={{ mb: 4 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5">
                  {getActivityTypeLabel(activity.type)}
                </Typography>
                <Chip 
                  icon={<CalendarTodayIcon />} 
                  label={formatDate(activity.date)}
                  color="primary"
                  variant="outlined"
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper elevation={2} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <SpeedIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h5">{formatDistance(activity.distance)}</Typography>
                    <Typography variant="body2" color="text.secondary">Distance</Typography>
                  </Paper>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Paper elevation={2} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <AccessTimeIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h5">{formatTime(activity.duration)}</Typography>
                    <Typography variant="body2" color="text.secondary">Duration</Typography>
                  </Paper>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Paper elevation={2} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <TimerIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h5">{formatPace(activity.avgPace)}</Typography>
                    <Typography variant="body2" color="text.secondary">Average Pace</Typography>
                  </Paper>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Paper elevation={2} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <LocalFireDepartmentIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h5">{activity.calories || 'N/A'}</Typography>
                    <Typography variant="body2" color="text.secondary">Calories</Typography>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Heart Rate Data
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <MonitorHeartIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary="Average Heart Rate"
                        secondary={activity.avgHR ? `${activity.avgHR} bpm` : 'N/A'}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <HeartBrokenIcon color="error" />
                      </ListItemIcon>
                      <ListItemText
                        primary="Maximum Heart Rate"
                        secondary={activity.maxHR ? `${activity.maxHR} bpm` : 'N/A'}
                      />
                    </ListItem>
                  </List>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Training Effect
                  </Typography>
                  {(activity.trainingEffectAerobic || activity.trainingEffectAnaerobic) ? (
                    <List>
                      {activity.trainingEffectAerobic && (
                        <ListItem>
                          <ListItemIcon>
                            <FitnessCenterIcon color={getTrainingEffectColor(activity.trainingEffectAerobic)} />
                          </ListItemIcon>
                          <ListItemText
                            primary={`Aerobic Effect: ${activity.trainingEffectAerobic.toFixed(1)}`}
                            secondary={getTrainingEffectDescription(activity.trainingEffectAerobic, true)}
                          />
                        </ListItem>
                      )}
                      {activity.trainingEffectAnaerobic && (
                        <ListItem>
                          <ListItemIcon>
                            <WhatshotIcon color={getTrainingEffectColor(activity.trainingEffectAnaerobic)} />
                          </ListItemIcon>
                          <ListItemText
                            primary={`Anaerobic Effect: ${activity.trainingEffectAnaerobic.toFixed(1)}`}
                            secondary={getTrainingEffectDescription(activity.trainingEffectAnaerobic, false)}
                          />
                        </ListItem>
                      )}
                      <ListItem>
                        <Box sx={{ width: '100%', mt: 1 }}>
                          <Typography variant="body2" gutterBottom>Training Focus</Typography>
                          <Grid container spacing={1} sx={{ mt: 1 }}>
                            <Grid item xs>
                              <Typography align="center" variant="body2" color="text.secondary">Recovery</Typography>
                              <Box
                                sx={{
                                  height: 10,
                                  bgcolor: activity.trainingEffectAerobic < 2 ? 'success.main' : 'background.paper',
                                  borderRadius: 5,
                                  border: 1,
                                  borderColor: 'divider'
                                }}
                              />
                            </Grid>
                            <Grid item xs>
                              <Typography align="center" variant="body2" color="text.secondary">Base</Typography>
                              <Box
                                sx={{
                                  height: 10,
                                  bgcolor: (activity.trainingEffectAerobic >= 2 && activity.trainingEffectAerobic < 3) ? 'info.main' : 'background.paper',
                                  borderRadius: 5,
                                  border: 1,
                                  borderColor: 'divider'
                                }}
                              />
                            </Grid>
                            <Grid item xs>
                              <Typography align="center" variant="body2" color="text.secondary">Tempo</Typography>
                              <Box
                                sx={{
                                  height: 10,
                                  bgcolor: (activity.trainingEffectAerobic >= 3 && activity.trainingEffectAerobic < 4) ? 'warning.main' : 'background.paper',
                                  borderRadius: 5,
                                  border: 1,
                                  borderColor: 'divider'
                                }}
                              />
                            </Grid>
                            <Grid item xs>
                              <Typography align="center" variant="body2" color="text.secondary">Threshold</Typography>
                              <Box
                                sx={{
                                  height: 10,
                                  bgcolor: activity.trainingEffectAerobic >= 4 ? 'error.main' : 'background.paper',
                                  borderRadius: 5,
                                  border: 1,
                                  borderColor: 'divider'
                                }}
                              />
                            </Grid>
                          </Grid>
                        </Box>
                      </ListItem>
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No training effect data available for this activity.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {activity.detailedData && Object.keys(activity.detailedData).length > 0 && (
            <Card variant="outlined" sx={{ mt: 4 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Additional Information
                </Typography>
                <Grid container spacing={2}>
                  {activity.detailedData.elapsedDuration && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Elapsed Time: {formatTime(activity.detailedData.elapsedDuration)}
                      </Typography>
                    </Grid>
                  )}
                  {activity.detailedData.movingDuration && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Moving Time: {formatTime(activity.detailedData.movingDuration)}
                      </Typography>
                    </Grid>
                  )}
                  {activity.detailedData.elevationGain && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Elevation Gain: {activity.detailedData.elevationGain} m
                      </Typography>
                    </Grid>
                  )}
                  {activity.detailedData.elevationLoss && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Elevation Loss: {activity.detailedData.elevationLoss} m
                      </Typography>
                    </Grid>
                  )}
                  {activity.detailedData.avgStrideLength && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Avg Stride Length: {activity.detailedData.avgStrideLength} cm
                      </Typography>
                    </Grid>
                  )}
                  {activity.detailedData.avgVerticalOscillation && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Avg Vertical Oscillation: {activity.detailedData.avgVerticalOscillation} cm
                      </Typography>
                    </Grid>
                  )}
                  {activity.detailedData.avgGroundContactTime && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Avg Ground Contact Time: {activity.detailedData.avgGroundContactTime} ms
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          )}

          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <Button 
              variant="outlined" 
              startIcon={<ArrowBackIcon />}
              component={Link}
              to="/"
            >
              Back to Dashboard
            </Button>
          </Box>
        </>
      ) : (
        <Alert severity="info">
          Activity not found. The activity may have been deleted or you may not have access to it.
        </Alert>
      )}
    </Container>
  );
};

export default ActivityDetail;