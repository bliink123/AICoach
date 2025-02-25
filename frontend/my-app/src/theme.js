// theme.js
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  typography: {
      fontFamily: '"Lato", "Helvetica Neue", Arial, sans-serif', // Your primary font family
      h1: {
        fontFamily: '"Bebas Neue", serif', // Custom font for h1 headings
        fontWeight: 400,
      },
      h2: {
        fontFamily: '"Lato", serif',
        fontWeight: 600,
      },
      h3: {
        fontFamily: '"Playwrite IT Moderna", serif',
        fontWeight: 600,
      },
      h4: { // Weekly Running Schedule
        fontFamily: '"Playwrite IT Moderna", serif',
        fontWeight: 600,
      },
      h5: {
        fontFamily: '"Bebas Neue", serif',
        fontWeight: 400,
      },
      body1: {
        fontFamily: '"Lato", sans-serif',
        fontWeight: 400,
        fontSize: '1rem',
      },
    // Add or override more typography variants as needed
    },
    palette: {
        mode: 'dark',
        primary: {
            main: '#40E0D0', // Teal/Aquamarine
        },
        secondary: {
            main: '#00CED1', // Slightly darker teal
        },
        background: {
            default: '#121212', // Dark background
            paper: '#1E1E1E', // Darker paper background for cards
        },
    },
    components: {
        MuiCard: {
            styleOverrides: {
                root: {
                    background: 'linear-gradient(180deg, #54A88C, #366B59)', // Teal gradient
                    color: 'white', // Dark text for contrast
                    borderRadius: '8px', // Optional: rounded corners
                    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.3)', // Optional: subtle shadow
                },
              
              defaultProps: {
                  elevation: 3, // Apply elevation globally
              },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    backgroundColor: '#B5624E',
                    color: 'white',
                    '&:hover': {
                        backgroundColor: '#00B2A9',
                    },
                },
            },
            variants: [
                {
                    props: { variant: 'contained', color: 'secondary' },
                    style: {
                        backgroundColor: '#B5624E',
                        color: 'white',
                        '&:hover': {
                            backgroundColor: '#00B2A9',
                        },
                    },
                },
                {
                    props: { variant: 'contained', color: 'primary' },
                    style: {
                        backgroundColor: '	#a85470', // Orange Colour
                        color: 'white', // button text colour
                        '&:hover': {
                            backgroundColor: 'rgba(168, 84, 112, 0.61)', // Dark Orange Colour
                        },
                    },
                },
            ],
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& label.Mui-focused': {
                        color: '#40E0D0',
                    },
                    '& .MuiInput-underline:after': {
                        borderBottomColor: '#40E0D0',
                    },
                    '& .MuiOutlinedInput-root': {
                        '& fieldset': {
                            borderColor: '#40E0D0',
                        },
                        '&:hover fieldset': {
                            borderColor: '#36C2B4',
                        },
                        '&.Mui-focused fieldset': {
                            borderColor: '#40E0D0',
                        },
                    },
                    '& .MuiSelect-select':{
                        color: '#E0E0E0'
                    }
                },
            },
        },
    },
});

export default theme;