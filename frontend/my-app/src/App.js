// App.js
import React from 'react';
import Dashboard from './dashboard';
import { GlobalStyles } from '@mui/material';

function App() {
  return (
    <>
      <GlobalStyles styles={{
        body: {
          backgroundColor: '#141414',
          color: '#ffffff',
          margin: 0,
          padding: 0,
          fontFamily: '"Inter", sans-serif'
        }
      }} />
      <Dashboard />
    </>
  );
}

export default App;
