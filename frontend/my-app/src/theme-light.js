// theme.js
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  typography: {
    fontFamily: '"Lato", "Helvetica Neue", Arial, sans-serif', // Your primary font family
    h1: {
      fontFamily: '"Bebas Neue", serif', // Custom font for h1 headings
      fontWeight: 400,
      letterSpacing: '0.1em', // Slight letter spacing for impact
      textTransform: 'uppercase', // Modern touch for main heading
      color: '#222222', // Dark header text
    },
    h2: {
      fontFamily: '"Lato", serif',
      fontWeight: 600,
      letterSpacing: '0.05em', // Subtle letter spacing for elegance
      color: '#222222', // Dark header text
    },
    h3: {
      fontFamily: '"Playwrite IT Moderna", serif',
      fontWeight: 600,
      color: '#222222', // Dark header text
    },
    h4: {
      // Weekly Running Schedule
      fontFamily: '"Playwrite IT Moderna", serif',
      fontWeight: 600,
      color: '#222222', // Dark header text
    },
    h5: {
      fontFamily: '"Bebas Neue", serif',
      fontWeight: 400,
      color: '#222222', // Dark header text
    },
    body1: {
      fontFamily: '"Lato", sans-serif',
      fontWeight: 400,
      fontSize: '1rem',
      lineHeight: 1.6, // Improved readability with spacing
    },
    // Add or override more typography variants as needed
  },
  palette: {
    mode: 'light', // Switch to light mode
    primary: {
      main: '#54A88C', // Keeping your main teal color
      light: '#66E8DB', // Lighter shade for accents
      dark: '#408774', // Darker teal for hover effects
      contrastText: '#fff', // White text on primary
    },
    secondary: {
      main: '#FF7D6B', // Coral accent color for contrast
      light: '#FF9E8F', // Lighter coral
      dark: '#D86A5A', // Darker coral
      contrastText: '#fff',
    },
    background: {
      default: '#F5F5F5', // Light clean background
      paper: '#FAFAFA', // Very light gray for cards
    },
    text: {
      primary: '#333333', // Dark gray for primary text
      secondary: '#666666', // Medium gray for secondary text
      disabled: '#AAAAAA'
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          color: '#333333', // Dark text for contrast
          borderRadius: '12px', // More rounded corners for modern look
          boxShadow: '0 6px 20px rgba(84, 168, 140, 0.15)', // Subtle shadow with brand color
          border: '1px solid #e0e0e0',
        },
      },
      defaultProps: {
        elevation: 0, // Remove default elevation
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none', // No uppercase for modern look
          fontWeight: 600,
          borderRadius: '8px', // Rounded buttons
          padding: '8px 20px',
          boxShadow: 'none', // Remove default shadow
        },
      },
      variants: [
        {
          props: { variant: 'contained', color: 'secondary' },
          style: {
            backgroundColor: '#FF7D6B', // Coral
            color: 'white',
            '&:hover': {
              backgroundColor: '#FF6954', // Slightly darker coral on hover
              boxShadow: '0 4px 12px rgba(255, 125, 107, 0.2)',
            },
          },
        },
        {
          props: { variant: 'contained', color: 'primary' },
          style: {
            backgroundColor: '#54A88C', // Using your main color
            color: 'white',
            '&:hover': {
              backgroundColor: '#478F78', // Slightly darker on hover
              boxShadow: '0 4px 12px rgba(84, 168, 140, 0.2)',
            },
          },
        },
        {
          props: { variant: 'outlined', color: 'primary' },
          style: {
            borderColor: '#54A88C',
            color: '#54A88C',
            '&:hover': {
              backgroundColor: 'rgba(84, 168, 140, 0.08)',
              borderColor: '#54A88C',
            },
          },
        },
      ],
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& label': {
            color: '#666666',
          },
          '& label.Mui-focused': {
            color: '#54A88C',
          },
          '& .MuiInput-underline:after': {
            borderBottomColor: '#54A88C',
          },
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: '#E0E0E0',
            },
            '&:hover fieldset': {
              borderColor: '#C8C8C8',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#54A88C',
            },
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'white',
          color: '#333333',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        switchBase: {
          color: '#CCCCCC',
          '&.Mui-checked': {
            color: '#54A88C',
          },
          '&.Mui-checked + .MuiSwitch-track': {
            backgroundColor: '#54A88C',
          },
        },
        track: {
          backgroundColor: '#E0E0E0',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(84, 168, 140, 0.1)',
          color: '#54A88C',
        },
      },
    },
        MuiTable: {
      styleOverrides: {
        root: {
          borderCollapse: 'separate',
          borderSpacing: '0px 5px', // Add spacing between rows
          '& th': {
             backgroundColor: '#F0F0F0' // Light background
          },
          '& td': {
             backgroundColor: '#FFFFFF' // White background
          },
          '& td, & th': {
            padding: '12px',
          },
          '& tr': {
             boxShadow: '0px 4px 8px rgba(0, 0, 0, 0.05)', // Subtle shadow for each row
             border: '1px solid #e0e0e0' // Add border to each row
          }
        },
      },
    },
  },
});

export default theme;
