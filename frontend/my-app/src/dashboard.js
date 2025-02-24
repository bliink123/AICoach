// Dashboard.js
import React, { useEffect, useState } from 'react';
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
  MenuItem
} from '@mui/material';
import Feedback from './Feedback';
import Schedule from './Schedule';

const trainingDistances = [
  { value: "5K", label: "5K" },
  { value: "10K", label: "10K" },
  { value: "HalfMarathon", label: "Half Marathon" },
  { value: "Marathon", label: "Marathon" }
];

function Dashboard() {
  const [sleepData, setSleepData] = useState(null);
  const [activities, setActivities] = useState([]);
  const [aiData, setAiData] = useState(null);
  const [trainingDistance, setTrainingDistance] = useState("5K");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sleepRes, activitiesRes, aiRes] = await Promise.all([
        axios.get('http://127.0.0.1:8080/api/overall-sleep'),
        axios.get('http://127.0.0.1:8080/api/activities'),
        axios.get(`http://127.0.0.1:8080/api/ai-coach?distance=${trainingDistance}`)
      ]);
      setSleepData(sleepRes.data);
      setActivities(activitiesRes.data);
      setAiData(aiRes.data);
    } catch (err) {
      console.error("Error fetching data:", err);
      setError("Error fetching data from the server.");
      setSnackbarOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [trainingDistance]);

  const handleRefresh = () => {
    fetchData();
  };

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  return (
    <Container sx={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <Typography variant="h3" align="center" gutterBottom>
        AICOACH Dashboard
      </Typography>

      {/* Training Distance Selector in Dashboard only */}
      <TextField
        select
        label="Training Distance"
        value={trainingDistance}
        onChange={(e) => setTrainingDistance(e.target.value)}
        sx={{ marginBottom: "20px", width: 200 }}
      >
        {trainingDistances.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </TextField>

      <Button
        variant="contained"
        onClick={handleRefresh}
        sx={{
          backgroundColor: "#FED5D1",
          color: "#000",
          textTransform: "none",
          marginBottom: "20px"
        }}
      >
        Refresh Data
      </Button>

      {loading && (
        <Grid container justifyContent="center" sx={{ margin: "20px 0" }}>
          <CircularProgress />
        </Grid>
      )}

      {!loading && error && (
        <Typography variant="body1" color="error" align="center">
          {error}
        </Typography>
      )}

      <Grid container spacing={3}>
        {/* Row 1: Sleep Data and Recent Activities */}
        <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
          <Card variant="outlined" sx={{ width: '100%', flex: 1 }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Sleep & Recovery Data
              </Typography>
              {sleepData ? (
                <>
                  <Typography variant="body1">
                    <strong>Overall Sleep Score:</strong> {sleepData.overallSleepScore || "N/A"}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Avg Overnight HRV:</strong> {sleepData.avgOvernightHrv || "N/A"}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Body Battery Change:</strong> {sleepData.bodyBatteryChange || "N/A"}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Training Readiness:</strong> {sleepData.trainingReadiness || "N/A"}
                  </Typography>
                </>
              ) : (
                <Typography variant="body2">No sleep data available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
          <Card variant="outlined" sx={{ width: '100%', flex: 1 }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Recent Activities
              </Typography>
              {activities && activities.length > 0 ? (
                <ul style={{ listStyleType: "none", padding: 0 }}>
                  {activities.map(activity => (
                    <li key={activity.activityId}>
                      <Typography variant="body1">
                        {activity.activityName} (ID: {activity.activityId})
                      </Typography>
                    </li>
                  ))}
                </ul>
              ) : (
                <Typography variant="body2">No activities available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Row 2: Running Recommendations */}
        <Grid item xs={12}>
          <Card variant="outlined" sx={{ width: '100%' }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Running Recommendations
              </Typography>
              {aiData ? (
                <>
                  <Typography variant="h6">
                    Rules-Based Run Type & Target Pace
                  </Typography>
                  <Typography variant="body1">
                    <strong>Run Type:</strong> {aiData.rulesBasedRunType || "N/A"}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Target Pace:</strong> {aiData.rulesBasedTargetPace || "N/A"}
                  </Typography>
                  <Typography variant="h6" sx={{ marginTop: "10px" }}>
                    AI Coach Recommendation
                  </Typography>
                  <Typography variant="body1">
                    {aiData.aiCoachRecommendation}
                  </Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ marginTop: "10px" }}>
                    (Race Prediction: {aiData.racePrediction}, Overall Sleep Score: {aiData.overallSleepScore}, HRV: {aiData.avgOvernightHrv}, Body Battery Change: {aiData.bodyBatteryChange}, Training Readiness: {aiData.trainingReadiness})
                  </Typography>
                </>
              ) : (
                <Typography variant="body2">No recommendations available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Row 3: Scheduling Calendar */}
      {/* Pass trainingDistance prop to Schedule component */}
      <Schedule trainingDistance={trainingDistance} />

      {/* Feedback Section */}
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
