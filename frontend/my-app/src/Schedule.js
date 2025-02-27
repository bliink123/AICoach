// Schedule.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  TextField,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Paper,
  MenuItem,
  CircularProgress
} from '@mui/material';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8080';

const daysOfWeek = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday"
];

const racePhases = [
  { value: "base", label: "Base" },
  { value: "build", label: "Build" },
  { value: "peak", label: "Peak" },
  { value: "taper", label: "Taper" },
  { value: "auto", label: "Auto" }
];

const experienceLevels = [
    { value: "beginner", label: "Beginner" },
    { value: "intermediate", label: "Intermediate" },
    { value: "advanced", label: "Advanced" }
];

const trainingGoals = [
    { value: "finish", label: "Finish" },
    { value: "pr", label: "PR" },
    { value: "compete", label: "Compete" }
];

const Schedule = ({ trainingDistance }) => {
  const [runDays, setRunDays] = useState('');
  const [longRunDay, setLongRunDay] = useState('');
  const [raceDate, setRaceDate] = useState('');
  const [racePhase, setRacePhase] = useState('auto');
  const [currentMileage, setCurrentMileage] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('intermediate');
  const [trainingGoal, setTrainingGoal] = useState('pr');
  const [schedule, setSchedule] = useState([]);
  const [scheduleSummary, setScheduleSummary] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const storedParams = JSON.parse(localStorage.getItem('scheduleParams')) || {};
        const payload = {
          runDays: storedParams.runDays ? parseInt(storedParams.runDays, 10) : 4,
          longRunDay: storedParams.longRunDay || "Sunday",
          trainingDistance,
          raceDate: storedParams.raceDate || new Date().toISOString().split('T')[0],
          racePhase: storedParams.racePhase || "auto",
          currentMileage: storedParams.currentMileage ? parseFloat(storedParams.currentMileage) : 40,
          experienceLevel: storedParams.experienceLevel || "intermediate",
          trainingGoal: storedParams.trainingGoal || "pr"
        };

        const response = await axios.post(`${API_BASE_URL}/api/schedule`, payload);
        setSchedule(response.data.schedule);
        setScheduleSummary(response.data.summary);

        setRunDays(String(payload.runDays));
        setLongRunDay(payload.longRunDay);
        setRaceDate(payload.raceDate);
        setRacePhase(payload.racePhase);
        setCurrentMileage(String(payload.currentMileage));
        setExperienceLevel(payload.experienceLevel);
        setTrainingGoal(payload.trainingGoal);

        setError('');
      } catch (err) {
        console.error(err);
        setError('Failed to fetch schedule');
      } finally {
        setLoading(false);
      }
    };

    fetchSchedule();
  }, [trainingDistance]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const payload = {
      runDays: parseInt(runDays, 10),
      longRunDay,
      trainingDistance,
      raceDate,
      racePhase,
      currentMileage: currentMileage ? parseFloat(currentMileage) : undefined,
      experienceLevel,
      trainingGoal
    };

    try {
      const response = await axios.post(`${API_BASE_URL}/api/schedule`, payload);
      setSchedule(response.data.schedule);
      setScheduleSummary(response.data.summary);
      setError('');

      localStorage.setItem('scheduleParams', JSON.stringify(payload));

    } catch (err) {
      console.error(err);
      setError('Failed to generate schedule');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container sx={{ marginTop: 4 }}>
      <Typography variant="h4" gutterBottom>
        Weekly Running Schedule
      </Typography>
      <form
        onSubmit={handleSubmit}
        style={{ marginBottom: 20, display: 'flex', flexWrap: 'wrap', gap: '16px' }}
      >
        <TextField
          label="Run Days per Week"
          type="number"
          value={runDays}
          onChange={(e) => setRunDays(e.target.value)}
          required
          sx={{ width: 200 }}
        />
        <TextField
          select
          label="Long Run Day"
          value={longRunDay}
          onChange={(e) => setLongRunDay(e.target.value)}
          required
          sx={{ width: 200 }}
        >
          {daysOfWeek.map((day) => (
            <MenuItem key={day} value={day}>
              {day}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Race Date"
          type="date"
          value={raceDate}
          onChange={(e) => setRaceDate(e.target.value)}
          required
          InputLabelProps={{ shrink: true }}
          sx={{ width: 200 }}
        />
        <TextField
          select
          label="Race Phase"
          value={racePhase}
          onChange={(e) => setRacePhase(e.target.value)}
          required
          sx={{ width: 200 }}
        >
          {racePhases.map((phase) => (
            <MenuItem key={phase.value} value={phase.value}>
              {phase.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Current Weekly Mileage (km)"
          type="number"
          value={currentMileage}
          onChange={(e) => setCurrentMileage(e.target.value)}
          sx={{ width: 200 }}
        />
        <TextField
          select
          label="Experience Level"
          value={experienceLevel}
          onChange={(e) => setExperienceLevel(e.target.value)}
          required
          sx={{ width: 200 }}
        >
            {experienceLevels.map((level) => (
                <MenuItem key={level.value} value={level.value}>
                    {level.label}
                </MenuItem>
            ))}
        </TextField>
        <TextField
            select
            label="Training Goal"
            value={trainingGoal}
            onChange={(e) => setTrainingGoal(e.target.value)}
            required
            sx={{ width: 200 }}
        >
            {trainingGoals.map((goal) => (
                <MenuItem key={goal.value} value={goal.value}>
                    {goal.label}
                </MenuItem>
            ))}
        </TextField>
        <Button type="submit" variant="contained" color="primary">
          Generate Schedule
        </Button>
      </form>
      {error && (
        <Typography color="error" sx={{ marginBottom: 2 }}>
          {error}
        </Typography>
      )}
      {loading && <CircularProgress />}
      {scheduleSummary && (
          <Typography variant="body1" sx={{ marginBottom: 2 }}>
              <strong>Weekly Mileage:</strong> {scheduleSummary.weeklyMileage} km, 
              <strong>Weekly Intensity:</strong> {scheduleSummary.weeklyIntensity}, 
              <strong>Current Week:</strong> {scheduleSummary.currentWeek},
              <strong>Total Weeks:</strong> {scheduleSummary.totalWeeks},
              <strong>Race Phase:</strong> {scheduleSummary.racePhase},
              <strong>Weeks Until Race:</strong> {scheduleSummary.weeksUntilRace}
          </Typography>
      )}
      {schedule.length > 0 && (
        <Paper sx={{ overflowX: 'auto' }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell><strong>Day</strong></TableCell>
                <TableCell><strong>Workout Type</strong></TableCell>
                <TableCell><strong>Workout Details</strong></TableCell>
                <TableCell><strong>Target Pace (min/km)</strong></TableCell>
                <TableCell><strong>Duration (min)</strong></TableCell>
                <TableCell><strong>Distance (km)</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {schedule.map((item, index) => (
                <TableRow key={index}>
                  <TableCell>{item.Day}</TableCell>
                  <TableCell>{item.WorkoutType}</TableCell>
                  <TableCell>{item.WorkoutDetails}</TableCell>
                  <TableCell>{item.TargetPace}</TableCell>
                  <TableCell>{item.Duration}</TableCell>
                  <TableCell>{item.Distance}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Container>
  );
};

export default Schedule;
