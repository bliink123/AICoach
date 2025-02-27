// App.js
import React from 'react';
import Dashboard from './dashboard';
import { GlobalStyles } from '@mui/material';

function App() {
  return (
    <>
      <GlobalStyles styles={{
        body: {
          background: 'linear-gradient(0deg,rgb(0, 0, 0),rgba(0, 0, 0, 0.81))',
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
      <Dashboard />
    </>
  );
}

export default App;
