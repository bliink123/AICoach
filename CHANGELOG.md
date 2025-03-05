# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0] - 2025-03-04
### Added
**Authentication Persistence Fix:**
Added loading state to AuthContext to prevent premature redirects during authentication checks
Improved session persistence with permanent sessions via session.permanent = True
Set PERMANENT_SESSION_LIFETIME to 7 days for extended login duration
Modified SESSION_COOKIE_SAMESITE from 'Strict' to 'Lax' to improve SPA compatibility

**Changed**
Updated PrivateRoute component with loading indicator while authentication status is being verified
Restructured AuthContext to properly expose loading state to child components
Improved error handling in authentication verification process

**Fixed**
Fixed persistent login issues that were causing users to be redirected to login page after refresh
Corrected race condition in frontend authentication check that resulted in premature navigation
Resolved cookie persistence issues by properly configuring both frontend and backend authentication parameters

## [1.3.0] - 2025-03-03
### Added
**Persistent Authentication Enhancements:**
Implemented persistent login by setting login_user(user, remember=True) in the /login endpoint.
Updated the /login endpoint to store user_id in the Flask session.
Added a /logout endpoint that clears the session (removes user_id) upon logout.
Introduced a /me endpoint (protected by @login_required) to verify the current authenticated user, enabling the frontend to update its authentication state automatically.

**Session Cookie Security Updates:**
Configured secure session cookie settings:
SESSION_COOKIE_DOMAIN set to 'localhost' to ensure cookies are shared between the backend and frontend.
Enabled SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SECURE (for HTTPS), and SESSION_COOKIE_SAMESITE set to 'Strict' to enhance cookie security.

**Improved Unauthorized Handling:**
Customized the unauthorized handler to return a JSON 401 response instead of redirecting, ensuring API clients receive a proper error code.

---

## [1.2.0] - 2025-03-03
#### ✨ Enhancements

*   **Improved Rest Day Distribution:** The schedule generation logic has been updated to distribute rest days more evenly throughout the week. Previously, rest days tended to cluster at the beginning of the week. This enhancement ensures a better balanced weekly schedule, promoting better recovery and training consistency.

    *   **Technical Change:** In `api/helper_functions.py`, the `improve_run_schedule_rule_based` function was modified. The method for assigning remaining rest days now uses `available_days.pop()` instead of `available_days.pop(0)`. This change makes the algorithm select rest days from the end of the available days list, leading to a more spread-out placement of rest days across the week.

*   **Refined Workout Sequencing for Build and Peak Phases:**  Significant improvements have been made to the workout sequencing, especially within the "build" and "peak" training phases.  The generated schedules now incorporate more strategic placement of different workout types to create more logical training progressions.

    *   **Technical Change:** The `workout_rules_phase_aware` dictionary in `api/helper_functions.py` has been extensively updated.  Specifically, for the "build" and "peak" phases and for run days counts of 3, 4, 5, 6, and 7, the workout type lists have been modified. These modifications prioritize:
        *   Spacing out harder workouts (Threshold, Intervals, Long Runs) with easier runs (Easy, Recovery).
        *   Ensuring sufficient "Easy" and "Recovery" runs, especially around Long Run days and after more intense sessions.
        *   Creating more structured weekly workout patterns that align with typical training principles for build and peak phases.

*   **User Authentication Added:** Implemented basic user authentication to the API, enhancing security and enabling future user-specific features. Users can now register and log in to the application.
    *   **Technical Changes:**
        *   **Flask-Login Integration:** Added Flask-Login for user session management.
        *   **User Model:** Created a `User` model in `api/models.py` using Flask-SQLAlchemy to store user credentials (username and hashed password). Password hashing is implemented using `werkzeug.security` for security.
        *   **Registration Endpoint (`/api/register`):** Implemented a new endpoint for user registration, handling username validation, password hashing, and user creation in the database.
        *   **Login Endpoint (`/api/login`):** Implemented a login endpoint to authenticate users against stored credentials and establish user sessions using Flask-Login.
        *   **Logout Endpoint (`/api/logout`):** Added a logout endpoint to terminate user sessions.
        *   **Route Protection (`@login_required`):** Introduced the `@login_required` decorator from Flask-Login to protect specific API endpoints, demonstrating how to restrict access to logged-in users only (example: `/api/protected`).
        *   **Database Configuration:** Configured Flask-SQLAlchemy and initialized a database (example using SQLite).
        *   **Frontend Integration (React):** (Note: While primarily backend change)  Frontend UI will need to be updated to include registration and login forms, handle API authentication responses, and manage user sessions on the client-side.

#### 🧪 Testing & Development
*   Caching in the `/api/schedule` endpoint has been temporarily disabled to facilitate easier testing and iterative development of schedule generation logic. Caching will be re-enabled in a future update for production and performance optimization.

 --

## [1.1.0] - 2025-02-26
### Added
- **Advanced Periodization Integration:**
  - Implemented new helper functions to calculate training phase (base, build, peak, taper, auto), plan length, default weekly mileage, phase multipliers, and cycle-based recovery.
  - Enhanced the `/api/schedule` endpoint to dynamically distribute workout sessions (long run, threshold, easy, recovery, intervals) based on periodization principles.
  - Calculated session-specific metrics (target pace, duration, distance, and an IntensityScore) as percentages of the weekly mileage.
  - Integrated additional user inputs: `experienceLevel` and `trainingGoal` to further personalize training recommendations.
- **AI Coach Enhancements:**
  - Updated the `/api/ai-coach` endpoint to include periodization data (current week, training phase, recommended weekly mileage) in the Gemini prompt, enriching AI-driven recommendations.
- **Backend Schema Updates:**
  - Extended the SQLite `ScheduleCache` model to store `experienceLevel` and `trainingGoal` for improved caching consistency.
- **User Interface Enhancements:**
  - Updated UI components to reflect new periodization insights and additional personalized metrics in the training schedule summary.

### Changed
- Refined target pace calculations and session duration formulas across schedule and AI coach endpoints using literature-based periodization guidelines.
- Improved caching mechanism to account for additional periodization parameters, ensuring consistency for 24 hours.

---

## [1.0.0] - 2025-02-25
### Added
- Initial release of **AICOACH**.
- **Backend:**
  - Integrated with Garmin Connect to fetch:
    - Sleep and recovery metrics (overall sleep score, average overnight HRV, body battery change, training readiness).
    - Race predictions (5K, 10K, Half Marathon, Marathon).
  - Implemented `/api/overall-sleep`, `/api/race-predictions`, `/api/ai-coach`, `/api/schedule`, and `/api/feedback` endpoints.
  - Developed AI Coach functionality using Gemini API to provide:
    - Rules-based running recommendations.
    - AI-generated running recommendations.
  - Added caching system with SQLite (`app_cache.db`) to:
    - Cache generated schedules for 24 hours.
    - Store user feedback.
  - Implemented error handling and logging across all API endpoints.

- **Frontend:**
  - Built using React and Material‑UI with responsive design.
  - Developed `Dashboard` component to display:
    - Recovery metrics
    - Race predictions
    - AI and rules-based running recommendations
  - Developed `Schedule` component with:
    - Dynamic weekly schedule generation.
    - Form for inputting run days, long run day, race date, race phase, and current mileage.
    - LocalStorage integration to persist user parameters.
  - Developed `Feedback` component for submitting user feedback.

- **Advanced Periodization (Basic Implementation):**
  - Weekly mileage dynamically calculated based on:
    - Race distance
    - Race phase (base, build, peak, taper, auto)
    - Current mileage and race date.
  - Session distribution based on literature guidelines:
    - Long run: 20–30% of weekly mileage
    - Quality runs: 10–20%
    - Easy runs: remainder
    - Rest days: auto-inserted for recovery

- **User Interface Enhancements:**
  - Added race prediction times display for 5K, 10K, Half Marathon, and Marathon.
  - Consolidated training distance selector to appear only on the `Dashboard`.
  - Updated theme to include Google Fonts and improved UI consistency.
  - Added gradient background for improved visual aesthetics.

---

## [0.9.0] - 2025-02-22
### Added
- Initial Garmin Connect API integration.
- Basic AI Coach functionality with Gemini API.
- Simple rules-based run type determination.

### Changed
- Converted race predictions from seconds to human-readable format.
- Refactored code for improved readability and modularity.

---

## [0.8.0] - 2025-02-20
### Added
- Developed basic Flask backend with initial endpoints.
- Integrated Gemini API for basic AI workout recommendations.
- Created basic React frontend with Material‑UI components.

### Fixed
- Resolved CORS issues between Flask and React servers.
- Handled authentication errors with Garmin Connect token system.

---

## [0.7.0] - 2025-02-18
### Added
- Initial project setup with basic structure:
  - Flask for backend
  - React for frontend
- Established Garmin Connect authentication via tokens.
- Created initial endpoints for fetching activities and sleep data.

---

## Upcoming
### Planned Features
- Expand periodization model to include strength and cross-training sessions.
- Add user authentication and individual training history.
- Improve AI-generated recommendations with more contextual data and user feedback.
- Incorporate graphical data visualizations in the dashboard.
- Enable exporting schedules to calendar apps (Google Calendar, iCal).
- Expand caching mechanisms to include feedback analysis.

---

## Notes
- This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
- Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
