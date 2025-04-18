import React, { useEffect, useState, useContext } from 'react';
import axios from 'axios';
import {
  Container,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Snackbar,
  Grid,
  TextField,
  MenuItem,
  Divider,
  Tabs,
  Tab,
  Box
} from '@mui/material';
import Feedback from './Feedback';
import Schedule from './Schedule';
import WorkoutRecommendation from './WorkoutRecommendation';
import TrainingInsights from './TrainingInsights';
import ActivityList from './ActivityList';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AuthContext } from './AuthContext';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8080';

const trainingDistances = [
  { value: "5K", label: "5K" },
  { value: "10K", label: "10K" },
  { value: "HalfMarathon", label: "Half Marathon" },
  { value: "Marathon", label: "Marathon" }
];

const formatValue = (value) => value || "N/A";

function Dashboard() {
  const { user, logout } = useContext(AuthContext);
  const [sleepData, setSleepData] = useState(null);
  const [racePredictions, setRacePredictions] = useState(null);
  const [aiData, setAiData] = useState(null);
  const [trainingDistance, setTrainingDistance] = useState(() => localStorage.getItem('trainingDistance') || "5K");
  const [loading, setLoading] = useState({ sleep: false, race: false, ai: false, insights: false, recommendations: false });
  const [error, setError] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState(0);
  const [trainingData, setTrainingData] = useState(null);

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  const fetchSleepData = async () => {
    setLoading(prev => ({ ...prev, sleep: true }));
    try {
      const response = await axios.get(`${API_BASE_URL}/api/overall-sleep`);
      setSleepData(response.data);
    } catch (err) {
      console.error("Error fetching sleep data:", err);
      setError("Error fetching sleep data from the server.");
      setSnackbarOpen(true);
    } finally {
      setLoading(prev => ({ ...prev, sleep: false }));
    }
  };

  const fetchRacePredictions = async () => {
    setLoading(prev => ({ ...prev, race: true }));
    try {
      const response = await axios.get(`${API_BASE_URL}/api/race-predictions`);
      setRacePredictions(response.data);
    } catch (err) {
      console.error("Error fetching race predictions:", err);
      setError("Error fetching race predictions from the server.");
      setSnackbarOpen(true);
    } finally {
      setLoading(prev => ({ ...prev, race: false }));
    }
  };

  const fetchAiData = async (distance) => {
    setLoading(prev => ({ ...prev, ai: true }));
    try {
      const response = await axios.get(`${API_BASE_URL}/api/ai-coach?distance=${distance}`);
      setAiData(response.data);
    } catch (err) {
      console.error("Error fetching AI data:", err);
      setError("Error fetching AI data from the server.");
      setSnackbarOpen(true);
    } finally {
      setLoading(prev => ({ ...prev, ai: false }));
    }
  };

  const fetchTrainingData = async () => {
    setLoading(prev => ({ ...prev, insights: true }));
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training-data`);
      setTrainingData(response.data);
    } catch (err) {
      console.error("Error fetching training data:", err);
      setError("Error fetching training data from the server.");
      setSnackbarOpen(true);
    } finally {
      setLoading(prev => ({ ...prev, insights: false }));
    }
  };

  const trainModels = async () => {
    setLoading(prev => ({ ...prev, recommendations: true }));
    try {
      const response = await axios.post(`${API_BASE_URL}/api/train-models`);
      setSnackbarOpen(true);
      setError(`Models trained successfully! Recovery model accuracy: ${
        response.data.recovery_model.accuracy ? 
        (response.data.recovery_model.accuracy * 100).toFixed(1) + '%' : 
        'Not enough data'
      }, Race model accuracy: ${
        response.data.race_model.accuracy ? 
        (response.data.race_model.accuracy * 100).toFixed(1) + '%' : 
        'Not enough data'
      }`);
    } catch (err) {
      console.error("Error training models:", err);
      setError("Error training models. Please try again later.");
      setSnackbarOpen(true);
    } finally {
      setLoading(prev => ({ ...prev, recommendations: false }));
    }
  };

  const fetchData = async () => {
    setError(null);
    await Promise.all([
      fetchSleepData(), 
      fetchRacePredictions(), 
      fetchAiData(trainingDistance),
      fetchTrainingData()
    ]);
  };

  useEffect(() => {
    fetchData();
    localStorage.setItem('trainingDistance', trainingDistance);
  }, [trainingDistance]);

  const handleRefresh = () => {
    fetchData();
  };

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  return (
    <Container sx={{ padding: "20px" }}>
      <Typography variant="h1" align="center" gutterBottom>
        AICOACH Dashboard
      </Typography>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <TextField
            select
            label="Training Distance"
            value={trainingDistance}
            onChange={(e) => setTrainingDistance(e.target.value)}
            sx={{ width: 200 }}
          >
            {trainingDistances.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>

          <Button
            variant="contained" size="large"
            onClick={handleRefresh}
            sx={{
              textTransform: "none",
              marginLeft: "20px"
            }}
          >
            Refresh Data
          </Button>

          <Button
            variant="outlined" 
            size="large"
            onClick={trainModels}
            sx={{
              textTransform: "none",
              marginLeft: "20px"
            }}
            disabled={loading.recommendations}
          >
            {loading.recommendations ? <CircularProgress size={24} /> : "Train ML Models"}
          </Button>
        </Box>

        <Button variant="outlined" size='large' onClick={logout}>
          Logout
        </Button>
      </Box>

      {(loading.sleep || loading.race || loading.ai) && (
        <Grid container justifyContent="center" sx={{ margin: "20px 0" }}>
          <CircularProgress />
        </Grid>
      )}

      {!loading.sleep && !loading.race && !loading.ai && error && (
        <Typography variant="body1" color="error" align="center">
          {error}
        </Typography>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined" elevation={8}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Sleep & Recovery Data
              </Typography>
              {loading.sleep ? (
                <CircularProgress />
              ) : sleepData ? (
                <>
                  <Typography variant="body1">
                    <strong>Overall Sleep Score:</strong> {formatValue(sleepData.overallSleepScore)}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Avg Overnight HRV:</strong> {formatValue(sleepData.avgOvernightHrv)}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Body Battery Change:</strong> {formatValue(sleepData.bodyBatteryChange)}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Training Readiness:</strong> {formatValue(sleepData.trainingReadiness)}
                  </Typography>
                </>
              ) : (
                <Typography variant="body2">No sleep data available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card variant="outlined" elevation={8}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Race Predictions
              </Typography>
              {loading.race ? (
                <CircularProgress />
              ) : racePredictions ? (
                <>
                  <Typography variant="body1">
                    <strong>5K Prediction:</strong> {formatValue(racePredictions.time5K)}
                  </Typography>
                  <Typography variant="body1">
                    <strong>10K Prediction:</strong> {formatValue(racePredictions.time10K)}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Half Marathon Prediction:</strong> {formatValue(racePredictions.timeHalfMarathon)}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Marathon Prediction:</strong> {formatValue(racePredictions.timeMarathon)}
                  </Typography>
                </>
              ) : (
                <Typography variant="body2">No race prediction data available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Tabs value={selectedTab} onChange={handleTabChange} centered variant="fullWidth" sx={{ mb: 2 }}>
            <Tab label="AI Coach" />
            <Tab label="ML Recommendation" />
            <Tab label="Training Insights" />
            <Tab label="Activities" />
            <Tab label="Schedule" />
          </Tabs>
          
          {/* AI Coach Tab */}
          {selectedTab === 0 && (
            <Card variant="outlined" elevation={3}>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  AI Running Recommendations
                </Typography>
                {loading.ai ? (
                  <CircularProgress />
                ) : aiData ? (
                  <>
                    <Typography variant="h6">Rules-Based Run Type & Target Pace</Typography>
                    <Typography variant="body1">
                      <strong>Run Type:</strong> {formatValue(aiData.rulesBasedRunType)}
                    </Typography>
                    <Typography variant="body1">
                      <strong>Target Pace:</strong> {formatValue(aiData.rulesBasedTargetPace)}
                    </Typography>
                    <Typography variant="h6" sx={{ marginTop: "10px" }}>AI Coach Recommendation</Typography>
                    <ReactMarkdown
                      children={aiData.aiCoachRecommendation}
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ node, ...props }) => <Typography variant="h4" component="h1" gutterBottom {...props} />,
                        h2: ({ node, ...props }) => <Typography variant="h5" component="h2" gutterBottom {...props} />,
                        h3: ({ node, ...props }) => <Typography variant="h6" component="h3" gutterBottom {...props} />,
                        p: ({ node, ...props }) => <Typography variant="body1" paragraph {...props} />,
                        li: ({ node, ...props }) => <Typography component="li" {...props} />,
                      }}
                    />
                    <Typography variant="body2" color="textSecondary" sx={{ marginTop: "10px" }}>
                      (Race Prediction: {formatValue(aiData.racePrediction)}, Overall Sleep Score: {formatValue(aiData.overallSleepScore)}, HRV: {formatValue(aiData.avgOvernightHrv)}, Body Battery Change: {formatValue(aiData.bodyBatteryChange)}, Training Readiness: {formatValue(aiData.trainingReadiness)})
                    </Typography>
                  </>
                ) : (
                  <Typography variant="body2">No recommendations available.</Typography>
                )}
              </CardContent>
            </Card>
          )}
          
          {/* ML Recommendation Tab */}
          {selectedTab === 1 && (
            <WorkoutRecommendation />
          )}
          
          {/* Training Insights Tab */}
          {selectedTab === 2 && (
            <TrainingInsights trainingData={trainingData} loading={loading.insights} />
          )}
          
          {/* Activities Tab */}
          {selectedTab === 3 && (
            <ActivityList />
          )}
          
          {/* Schedule Tab */}
          {selectedTab === 4 && (
            <Schedule trainingDistance={trainingDistance} />
          )}
        </Grid>
      </Grid>

      <Divider sx={{ my: 4 }} />
      <Feedback />

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        message={error}
      />
    </Container>
  );
}

export default Dashboard;