import React, { useEffect, useState } from 'react';
import { Box, TextField, Button, Typography, Card, CardContent, List, ListItem } from '@mui/material';
import axios from 'axios';

const Feedback = () => {
  const [rating, setRating] = useState('');
  const [comment, setComment] = useState('');
  const [feedbackList, setFeedbackList] = useState([]);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState('');

  // Fetch feedback from backend
  const fetchFeedback = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8080/api/feedback');
      setFeedbackList(res.data);
    } catch (err) {
      console.error("Error fetching feedback:", err);
      setError("Error fetching feedback");
    }
  };

  useEffect(() => {
    fetchFeedback();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!rating) {
      setError("Rating is required");
      return;
    }
    setError(null);
    try {
      await axios.post('http://127.0.0.1:8080/api/feedback', {
        rating: parseInt(rating, 10),
        comment
      });
      setSuccess("Feedback submitted successfully");
      setRating('');
      setComment('');
      fetchFeedback();
    } catch (err) {
      console.error("Error submitting feedback:", err);
      setError("Error submitting feedback");
    }
  };

  return (
    <Box sx={{ marginTop: 4 }}>
      <Typography variant="h5" gutterBottom>
        Submit Your Feedback
      </Typography>
      <form onSubmit={handleSubmit}>
        <TextField
          label="Rating (1-5)"
          variant="outlined"
          value={rating}
          onChange={(e) => setRating(e.target.value)}
          type="number"
          InputProps={{ inputProps: { min: 1, max: 5 } }}
          sx={{ marginRight: 2, marginBottom: 2 }}
        />
        <TextField
          label="Comment"
          variant="outlined"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          multiline
          rows={3}
          sx={{ marginRight: 2, marginBottom: 2, width: '50%' }}
        />
        <Button
          variant="contained"
          type="submit"
          sx={{ backgroundColor: "#FED5D1", color: "#000" }}
        >
          Submit Feedback
        </Button>
      </form>
      {error && <Typography color="error">{error}</Typography>}
      {success && <Typography color="primary">{success}</Typography>}
      
      <Typography variant="h6" gutterBottom sx={{ marginTop: 4 }}>
        Feedback History
      </Typography>
      {feedbackList.length > 0 ? (
        <List>
          {feedbackList.map((fb) => (
            <ListItem key={fb.id}>
              <Card sx={{ width: '100%' }}>
                <CardContent>
                  <Typography variant="body1">
                    Rating: {fb.rating}
                  </Typography>
                  <Typography variant="body2">
                    Comment: {fb.comment}
                  </Typography>
                  <Typography variant="caption">
                    {new Date(fb.timestamp).toLocaleString()}
                  </Typography>
                </CardContent>
              </Card>
            </ListItem>
          ))}
        </List>
      ) : (
        <Typography variant="body2">No feedback available yet.</Typography>
      )}
    </Box>
  );
};

export default Feedback;
