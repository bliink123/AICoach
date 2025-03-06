import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Box,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Chip,
  IconButton,
  Paper,
  InputBase,
  Grid
} from '@mui/material';
import DirectionsRunIcon from '@mui/icons-material/DirectionsRun';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import SortIcon from '@mui/icons-material/Sort';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import SpeedIcon from '@mui/icons-material/Speed';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import HeartBrokenIcon from '@mui/icons-material/HeartBroken';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8080';

const ActivityList = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc' or 'desc'

  const fetchActivities = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/recent-running-activities`);
      setActivities(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching activities:", err);
      setError("Failed to fetch activities. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, []);

  const formatDate = (dateString) => {
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const formatTime = (seconds) => {
    if (!seconds) return 'N/A';
    
    // Round seconds to 2 decimal places if it's not a whole number
    seconds = Math.round(seconds);
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${remainingSeconds}s`;
    } else {
      return `${minutes}m ${remainingSeconds}s`;
    }
  };

  const formatPace = (paceInSecondsPerMeter, distance, duration) => {
    // First check if we have a valid pace value
    if (paceInSecondsPerMeter === null || paceInSecondsPerMeter === undefined || isNaN(paceInSecondsPerMeter)) {
      console.log("Pace is null or NaN:", paceInSecondsPerMeter);
      
      // Try to calculate from distance and duration if available
      if (distance && duration && distance > 0) {
        const calculatedPace = duration / distance;
        console.log("Calculated pace:", calculatedPace);
        paceInSecondsPerMeter = calculatedPace;
      } else {
        return 'N/A';
      }
    }
    
    // Convert to min/km
    try {
      const secondsPerKm = paceInSecondsPerMeter * 1000;
      
      // Sanity check for unreasonable values
      if (secondsPerKm < 100 || secondsPerKm > 1200) {
        console.warn(`Unusual pace value: ${secondsPerKm} sec/km`);
        return 'N/A';
      }
      
      const minutes = Math.floor(secondsPerKm / 60);
      const seconds = Math.floor(secondsPerKm % 60);
      
      return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
    } catch (error) {
      console.error("Error formatting pace:", error);
      return 'N/A';
    }
  };

  const formatDistance = (meters) => {
    if (!meters) return 'N/A';
    return `${(meters / 1000).toFixed(2)} km`;
  };

  const getActivityIcon = (type) => {
    if (!type) return <DirectionsRunIcon />;
    
    const lowerType = type.toLowerCase();
    if (lowerType.includes('treadmill')) {
      return <DirectionsRunIcon style={{ transform: 'rotate(90deg)' }} />;
    } else if (lowerType.includes('trail')) {
      return <DirectionsRunIcon style={{ color: 'green' }} />;
    } else if (lowerType.includes('track')) {
      return <DirectionsRunIcon style={{ color: 'blue' }} />;
    } else if (lowerType.includes('indoor')) {
      return <DirectionsRunIcon style={{ color: 'purple' }} />;
    }
    
    return <DirectionsRunIcon />;
  };

  const getActivityColor = (type) => {
    if (!type) return 'default';
    
    const lowerType = type.toLowerCase();
    if (lowerType.includes('treadmill')) {
      return 'secondary';
    } else if (lowerType.includes('trail')) {
      return 'success';
    } else if (lowerType.includes('track')) {
      return 'info';
    } else if (lowerType.includes('indoor')) {
      return 'warning';
    }
    
    return 'primary';
  };

  // Filter and sort activities based on search term and sort order
  const filteredActivities = activities
    .filter(activity => 
      activity.type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      formatDate(activity.date).toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
    });

  const toggleSortOrder = () => {
    setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
  };

  return (
    <Card variant="outlined">
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <DirectionsRunIcon sx={{ mr: 1 }} /> Recent Running Activities
        </Typography>

        <Box sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
          <Paper
            component="form"
            sx={{ p: '2px 4px', display: 'flex', alignItems: 'center', width: 400, mr: 2 }}
            onSubmit={(e) => e.preventDefault()}
          >
            <InputBase
              sx={{ ml: 1, flex: 1 }}
              placeholder="Search activities..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <IconButton type="button" sx={{ p: '10px' }} aria-label="search">
              <SearchIcon />
            </IconButton>
          </Paper>
          
          <IconButton onClick={toggleSortOrder}>
            <SortIcon />
          </IconButton>
          <Typography variant="body2" sx={{ ml: 1 }}>
            {sortOrder === 'desc' ? 'Newest first' : 'Oldest first'}
          </Typography>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error" sx={{ p: 2 }}>
            {error}
          </Typography>
        ) : filteredActivities.length > 0 ? (
          <List sx={{ width: '100%', bgcolor: 'background.paper' }}>
            {filteredActivities.map((activity) => (
              <React.Fragment key={activity.id}>
                <ListItem 
                  alignItems="flex-start"
                  component={Link}
                  to={`/activity/${activity.id}`}
                  sx={{ 
                    textDecoration: 'none', 
                    color: 'inherit',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.04)'
                    }
                  }}
                >
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: `${getActivityColor(activity.type)}.main` }}>
                      {getActivityIcon(activity.type)}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle1">
                          {formatDate(activity.date)}
                        </Typography>
                        <Chip 
                          size="small"
                          label={activity.type || "Run"} 
                          color={getActivityColor(activity.type)}
                        />
                      </Box>
                    }
                    secondary={
                      <Grid container spacing={1} sx={{ mt: 1 }}>
                        <Grid item xs={12} sm={6} md={3}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <SpeedIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
                            <Typography variant="body2" color="text.secondary">
                              Distance: {formatDistance(activity.distance)}
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <AccessTimeIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
                            <Typography variant="body2" color="text.secondary">
                              Duration: {formatTime(activity.duration)}
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <HeartBrokenIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
                            <Typography variant="body2" color="text.secondary">
                              Avg HR: {activity.averageHR || 'N/A'}
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <LocalFireDepartmentIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
                            <Typography variant="body2" color="text.secondary">
                              Pace: {formatPace(activity.averagePace, activity.distance, activity.duration)}
                            </Typography>
                          </Box>
                        </Grid>
                      </Grid>
                    }
                  />
                </ListItem>
                <Divider variant="inset" component="li" />
              </React.Fragment>
            ))}
          </List>
        ) : (
          <Typography variant="body1" sx={{ p: 2 }}>
            No activities found. Try adjusting your search or sync your Garmin data.
          </Typography>
        )}
        
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={fetchActivities} 
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            Refresh Activities
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ActivityList;