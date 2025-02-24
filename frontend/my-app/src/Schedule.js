// Schedule.js
import React, { useState } from 'react';
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
  MenuItem
} from '@mui/material';

const daysOfWeek = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday"
];

const Schedule = ({ trainingDistance }) => {
  const [runDays, setRunDays] = useState('');
  const [longRunDay, setLongRunDay] = useState('');
  const [schedule, setSchedule] = useState([]);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://127.0.0.1:8080/api/schedule', {
        runDays: parseInt(runDays, 10),
        longRunDay,
        trainingDistance
      });
      setSchedule(response.data.schedule);
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to generate schedule');
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
        <Button type="submit" variant="contained" color="primary">
          Generate Schedule
        </Button>
      </form>
      {error && (
        <Typography color="error" sx={{ marginBottom: 2 }}>
          {error}
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
