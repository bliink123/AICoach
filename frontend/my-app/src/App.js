// App.js
import React from 'react';
import Dashboard from './dashboard';
import { GlobalStyles } from '@mui/material';

function App() {
  return (
    <>
      <GlobalStyles styles={{
        body: {
          background: 'linear-gradient(135deg, #141414, #3a3a3a)',
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
