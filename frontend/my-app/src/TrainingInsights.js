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
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InsightsIcon from '@mui/icons-material/Insights';
import FitnessCenterIcon from '@mui/icons-material/FitnessCenter';
import DirectionsRunIcon from '@mui/icons-material/DirectionsRun';
import SpeedIcon from '@mui/icons-material/Speed';
import BarChartIcon from '@mui/icons-material/BarChart';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import ScheduleIcon from '@mui/icons-material/Schedule';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8080';

const TrainingInsights = ({ trainingData }) => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [localTrainingData, setLocalTrainingData] = useState(trainingData);

  const fetchInsights = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training-insights`);
      setInsights(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching training insights:", err);
      setError("Failed to fetch training insights. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const fetchTrainingData = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training-data`);
      setLocalTrainingData(response.data);
    } catch (err) {
      console.error("Error fetching training data:", err);
    }
  };

  useEffect(() => {
    fetchInsights();
    if (!trainingData) {
      fetchTrainingData();
    }
  }, [trainingData]);

  const getMetricTrend = (metrics, key) => {
    if (!metrics || metrics.length < 2 || !key) return null;
    
    // Filter out null or undefined values
    const validMetrics = metrics.filter(m => m[key] !== null && m[key] !== undefined);
    if (validMetrics.length < 2) return null;
    
    const first = validMetrics[0][key];
    const last = validMetrics[validMetrics.length - 1][key];
    
    if (last > first) return "increasing";
    if (last < first) return "decreasing";
    return "stable";
  };

  const getInsightIcon = (index) => {
    const icons = [
      <TipsAndUpdatesIcon />,
      <DirectionsRunIcon />,
      <FitnessCenterIcon />,
      <SpeedIcon />,
      <BarChartIcon />
    ];
    return icons[index % icons.length];
  };

  return (
    <Card variant="outlined">
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <InsightsIcon sx={{ mr: 1 }} /> ML-Powered Training Insights
        </Typography>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error" sx={{ p: 2 }}>
            {error}
          </Typography>
        ) : (
          <Grid container spacing={3}>
            {insights?.insights?.length > 0 ? (
              <Grid item xs={12}>
                <Paper elevation={3} sx={{ p: 3, borderRadius: 2, mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Key Insights
                  </Typography>
                  <List>
                    {insights.insights.map((insight, index) => (
                      <ListItem key={index} alignItems="flex-start">
                        <ListItemIcon>
                          {getInsightIcon(index)}
                        </ListItemIcon>
                        <ListItemText
                          primary={insight}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
            ) : (
              <Grid item xs={12}>
                <Alert severity="info">
                  Continue logging your runs to receive personalized training insights.
                </Alert>
              </Grid>
            )}

            {insights?.stats && (
              <Grid item xs={12}>
                <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Training Statistics
                  </Typography>
                  
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                        <DirectionsRunIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h6">{insights.stats.total_runs || 0}</Typography>
                        <Typography variant="body2" color="text.secondary">Total Runs</Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                        <SpeedIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h6">{insights.stats.avg_weekly_distance?.toFixed(1) || 0} km</Typography>
                        <Typography variant="body2" color="text.secondary">Avg Weekly Distance</Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                        <BarChartIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h6">{insights.stats.max_weekly_distance?.toFixed(1) || 0} km</Typography>
                        <Typography variant="body2" color="text.secondary">Max Weekly Distance</Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                        <ScheduleIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h6">{insights.stats.avg_days_between_runs?.toFixed(1) || 0}</Typography>
                        <Typography variant="body2" color="text.secondary">Avg Days Between Runs</Typography>
                      </Box>
                    </Grid>
                  </Grid>
                  
                  <Box sx={{ mt: 3, p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>Training Balance</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body2" sx={{ minWidth: 120 }}>Easy Runs:</Typography>
                      <Box sx={{ width: '100%', mr: 1 }}>
                        <Box
                          sx={{
                            width: `${insights.stats.easy_run_percentage}%`,
                            height: 10,
                            bgcolor: 'success.main',
                            borderRadius: 5
                          }}
                        />
                      </Box>
                      <Typography variant="body2">{insights.stats.easy_run_percentage?.toFixed(1)}%</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ minWidth: 120 }}>Quality Runs:</Typography>
                      <Box sx={{ width: '100%', mr: 1 }}>
                        <Box
                          sx={{
                            width: `${100 - insights.stats.easy_run_percentage}%`,
                            height: 10,
                            bgcolor: 'warning.main',
                            borderRadius: 5
                          }}
                        />
                      </Box>
                      <Typography variant="body2">{(100 - insights.stats.easy_run_percentage)?.toFixed(1)}%</Typography>
                    </Box>
                  </Box>
                </Paper>
              </Grid>
            )}

            {localTrainingData && (
              <Grid item xs={12}>
                <Accordion defaultExpanded>
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    aria-controls="panel1a-content"
                    id="panel1a-header"
                  >
                    <Typography variant="h6">Performance Metrics</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      {localTrainingData.metrics && localTrainingData.metrics.length > 0 && (
                        <Grid item xs={12}>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle1" gutterBottom>Recent Trends</Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                              {getMetricTrend(localTrainingData.metrics, 'vo2max') && (
                                <Chip 
                                  icon={<FitnessCenterIcon />}
                                  label={`VO2max: ${getMetricTrend(localTrainingData.metrics, 'vo2max')}`}
                                  color={getMetricTrend(localTrainingData.metrics, 'vo2max') === 'increasing' ? 'success' : 
                                         getMetricTrend(localTrainingData.metrics, 'vo2max') === 'decreasing' ? 'error' : 'default'}
                                />
                              )}
                              {getMetricTrend(localTrainingData.metrics, 'sleep_score') && (
                                <Chip 
                                  label={`Sleep Score: ${getMetricTrend(localTrainingData.metrics, 'sleep_score')}`}
                                  color={getMetricTrend(localTrainingData.metrics, 'sleep_score') === 'increasing' ? 'success' : 
                                         getMetricTrend(localTrainingData.metrics, 'sleep_score') === 'decreasing' ? 'error' : 'default'}
                                />
                              )}
                              {getMetricTrend(localTrainingData.metrics, 'training_readiness') && (
                                <Chip 
                                  label={`Readiness: ${getMetricTrend(localTrainingData.metrics, 'training_readiness')}`}
                                  color={getMetricTrend(localTrainingData.metrics, 'training_readiness') === 'increasing' ? 'success' : 
                                         getMetricTrend(localTrainingData.metrics, 'training_readiness') === 'decreasing' ? 'error' : 'default'}
                                />
                              )}
                              {getMetricTrend(localTrainingData.metrics, 'resting_heart_rate') && (
                                <Chip 
                                  label={`Resting HR: ${getMetricTrend(localTrainingData.metrics, 'resting_heart_rate')}`}
                                  color={getMetricTrend(localTrainingData.metrics, 'resting_heart_rate') === 'decreasing' ? 'success' : 
                                         getMetricTrend(localTrainingData.metrics, 'resting_heart_rate') === 'increasing' ? 'error' : 'default'}
                                />
                              )}
                            </Box>
                          </Box>
                        </Grid>
                      )}

                      {localTrainingData.race_predictions && Object.keys(localTrainingData.race_predictions).length > 0 && (
                        <Grid item xs={12}>
                          <Typography variant="subtitle1" gutterBottom>Race Predictions</Typography>
                          <Grid container spacing={2}>
                            {localTrainingData.race_predictions['5k'] && (
                              <Grid item xs={6} sm={3}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                                  <Typography variant="h6">{localTrainingData.race_predictions['5k']}</Typography>
                                  <Typography variant="body2" color="text.secondary">5K</Typography>
                                </Box>
                              </Grid>
                            )}
                            {localTrainingData.race_predictions['10k'] && (
                              <Grid item xs={6} sm={3}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                                  <Typography variant="h6">{localTrainingData.race_predictions['10k']}</Typography>
                                  <Typography variant="body2" color="text.secondary">10K</Typography>
                                </Box>
                              </Grid>
                            )}
                            {localTrainingData.race_predictions['half_marathon'] && (
                              <Grid item xs={6} sm={3}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                                  <Typography variant="h6">{localTrainingData.race_predictions['half_marathon']}</Typography>
                                  <Typography variant="body2" color="text.secondary">Half Marathon</Typography>
                                </Box>
                              </Grid>
                            )}
                            {localTrainingData.race_predictions['marathon'] && (
                              <Grid item xs={6} sm={3}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                                  <Typography variant="h6">{localTrainingData.race_predictions['marathon']}</Typography>
                                  <Typography variant="body2" color="text.secondary">Marathon</Typography>
                                </Box>
                              </Grid>
                            )}
                          </Grid>
                        </Grid>
                      )}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Grid>
            )}
          </Grid>
        )}
        
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={fetchInsights} 
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            Refresh Insights
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TrainingInsights;