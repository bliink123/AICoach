# Changelog

All notable changes to this project will be documented in this file.

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
