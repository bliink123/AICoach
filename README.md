# AICOACH

AICOACH is a dynamic running coaching platform that combines real-time recovery data from Garmin Connect, AI-driven recommendations via Gemini, and an advanced periodization-based scheduling engine. Our platform delivers personalized running workouts and a comprehensive weekly training schedule that adapts to your current recovery metrics, race predictions, individualized training phase, experience level, and specific goals.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Backend API Endpoints](#backend-api-endpoints)
- [Frontend](#frontend)
- [Advanced Periodization](#advanced-periodization)
- [Caching & Data Persistence](#caching--data-persistence)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Overview

AICOACH helps runners optimize their training by fusing objective recovery metrics—such as overall sleep score, average overnight HRV, body battery change, and training readiness—with race predictions across various distances (5K, 10K, Half Marathon, Marathon). Using both rules‑based logic and AI (powered by Gemini), AICOACH generates personalized running paces and a weekly schedule that dynamically adapts based on your training phase, current mileage, experience level, and training goals.

---

## Features

- **Garmin Connect Integration:**  
  Fetches sleep and recovery metrics along with race predictions.

- **AI Coach & Rules‑Based Recommendations:**  
  - Determines run type (Recovery, Easy, Threshold, Long Run) based on recovery metrics.  
  - Calculates target paces using race prediction data with multipliers:  
    - *Recovery:* ~30% slower than race pace  
    - *Easy:* ~15% slower  
    - *Threshold:* Approximately race pace (or ~4% slower)  
    - *Long Run:* ~20% slower  
  - Enriches recommendations by integrating periodization data, such as current training week, phase, and recommended weekly mileage.

- **Dynamic Weekly Schedule:**  
  Generates a full weekly running schedule (Monday–Sunday) by combining user inputs with advanced periodization principles:
  - **User Inputs:** Run days per week, long run day, training distance, race date, race phase (or auto-detected), current mileage, experience level, and training goal.
  - **Advanced Periodization:**  
    - Auto-determines training phase (base, build, peak, taper) from the race date.  
    - Adjusts default weekly mileage using phase multipliers and cycle-based recovery (e.g., every 4th week as a recovery week).  
    - Distributes session types (e.g., long run, threshold, easy, recovery, intervals) as percentages of weekly mileage.  
    - Calculates session durations, distances, and assigns an “IntensityScore” for each workout.
  - **Caching:** Schedules are cached for 24 hours in SQLite to ensure fast, consistent responses.

- **Feedback Module:**  
  Submit and view user feedback to help improve recommendations over time.

- **Responsive Frontend:**  
  Built with React and Material‑UI, the Dashboard displays recovery data, race predictions, running recommendations, and a unified training distance selector that feeds into the Schedule component.

---

## Architecture

- **Backend:**  
  - Python Flask API integrating with Garmin Connect and Gemini.  
  - Advanced periodization calculations for personalized schedule generation.  
  - SQLite (app_cache.db) for caching schedules and storing user feedback.

- **Frontend:**  
  - React application built with Material‑UI.  
  - Key components include:  
    - **Dashboard:** Displays recovery metrics, race predictions, and running recommendations.  
    - **Schedule:** Renders the weekly training plan based on user-supplied parameters.  
    - **Feedback:** Interface for submitting and reviewing user feedback.

---

## Setup & Installation

### Prerequisites

- Python 3.8+
- Node.js & npm
- SQLite

### Backend

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/aicoach.git
   cd aicoach/backend
