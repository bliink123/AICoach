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
  Grid
} from '@mui/material';

function Dashboard() {
  const [sleepData, setSleepData] = useState(null);
  const [activities, setActivities] = useState([]);
  const [aiData, setAiData] = useState(null);
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
        axios.get('http://127.0.0.1:8080/api/ai-coach')
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
  }, []);

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
                Sleep Data
              </Typography>
              {sleepData ? (
                <>
                  <Typography variant="body1">
                    <strong>Overall Sleep Score:</strong> {sleepData.overallSleepScore || "N/A"}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Average Overnight HRV:</strong> {sleepData.avgOvernightHrv || "N/A"}
                  </Typography>
                  <Typography variant="body1">
                    <strong>Body Battery Change:</strong> {sleepData.bodyBatteryChange || "N/A"}
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

        {/* Row 2: AI Coach Recommendations */}
        <Grid item xs={12}>
          <Card variant="outlined" sx={{ width: '100%' }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Workout Recommendations
              </Typography>
              {aiData ? (
                <>
                  <Typography variant="h6">
                    Rules-Based Recommendation
                  </Typography>
                  <Typography variant="body1" sx={{ marginBottom: "10px" }}>
                    {aiData.rulesBasedRecommendation}
                  </Typography>
                  <Typography variant="h6">
                    AI Coach Recommendation
                  </Typography>
                  <Typography variant="body1">
                    {aiData.aiCoachRecommendation}
                  </Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ marginTop: "10px" }}>
                    (Based on a sleep score of {aiData.overallSleepScore}, HRV of {aiData.avgOvernightHrv}, and body battery change of {aiData.bodyBatteryChange}.)
                  </Typography>
                </>
              ) : (
                <Typography variant="body2">No recommendation available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

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
