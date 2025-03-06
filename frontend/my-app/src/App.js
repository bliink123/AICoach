import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './dashboard';
import Login from './components/Login';
import Register from './components/Register';
import PrivateRoute from './PrivateRoute';
import { AuthProvider } from './AuthContext';
import { GlobalStyles } from '@mui/material';
import ActivityDetail from './ActivityDetail';
import WorkoutRecommendation from './WorkoutRecommendation';
import TrainingInsights from './TrainingInsights';

function App() {
  return (
    <AuthProvider>
      <GlobalStyles styles={{
        body: {
          background: 'linear-gradient(0deg, rgb(0, 0, 0), rgba(0, 0, 0, 0.81))',
          backgroundRepeat: 'no-repeat',
          backgroundAttachment: 'fixed',
          backgroundSize: 'cover',
          color: '#ffffff',
          margin: 0,
          padding: 0,
          fontFamily: '"Inter", sans-serif',
          minHeight: '100vh'
        }
      }} />
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<PrivateRoute />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/activity/:activityId" element={<ActivityDetail />} />
            <Route path="/recommendations" element={<WorkoutRecommendation />} />
            <Route path="/insights" element={<TrainingInsights />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;