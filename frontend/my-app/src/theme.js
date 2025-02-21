// theme.js
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00bcd4',  // Accent color; adjust to taste
    },
    secondary: {
      main: '#ff4081',
    },
    background: {
      default: '#141414',  // Dark background similar to AngelList
      paper: '#1f1f1f',    // Slightly lighter for cards and surfaces
    },
    text: {
      primary: '#FED5D1',
      secondary: '#aaaaaa',
    },
  },
  typography: {
    fontFamily: '"Inter", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 600 },
    body1: { fontSize: '1rem' },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '8px',
          primary: "#FED5D1"
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
        },
      },
    },
  },
});

export default theme;
