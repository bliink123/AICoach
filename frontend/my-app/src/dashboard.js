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
  Snackbar
} from '@mui/material';
import Grid from '@mui/material/Grid2'; // Grid2 component

function Dashboard() {
  const [sleepData, setSleepData] = useState(null);
  const [activities, setActivities] = useState([]);
  const [aiRecommendation, setAiRecommendation] = useState(null);
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
      setAiRecommendation(aiRes.data);
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
      <Typography variant="h3" align="center" color="#FED5D" gutterBottom>
        AICOACH Dashboard
      </Typography>

      <Button
        variant="contained"
        onClick={handleRefresh}
        sx={{
          backgroundColor: "#FED5D1",
          color: "#000",
          textTransform: "none",
          "&:hover": { backgroundColor: "#e0b9b3" },
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

      <Grid container spacing={3} sx={{justifyContent: "flex-start",alignItems: "flex-start",}}>
        <Grid xs={20} md={4}>
          <Card variant="outlined" sx={{ width: '100%' }}>
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

        <Grid xs={20} md={4}>
          <Card variant="outlined" sx={{ width: '100%' }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                AI Coach Recommendation
              </Typography>
              {aiRecommendation ? (
                <>
                  <Typography variant="body1">{aiRecommendation.recommendation}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Based on a sleep score of {aiRecommendation.overallSleepScore}, HRV of {aiRecommendation.avgOvernightHrv}, and body battery change of {aiRecommendation.bodyBatteryChange}.
                  </Typography>
                </>
              ) : (
                <Typography variant="body2">No recommendation available.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid xs={20} md={4}>
          <Card variant="outlined" sx={{ width: '100%' }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Recent Activities
              </Typography>
              {activities.length > 0 ? (
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
