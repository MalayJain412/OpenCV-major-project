# VisionTrack — AI coding agent instructions

This file provides comprehensive guidance for AI agents working on VisionTrack, a real-time human pose estimation platform with fitness tracking, surveillance monitoring, and web interface capabilities.

## Project Overview & Architecture

VisionTrack is a dual-mode application:
- **Web Mode** (`python launcher.py web`): Flask server at localhost:5000 with real-time video streaming and REST API
- **Desktop Mode** (`python launcher.py desktop`): Direct OpenCV UI for standalone operation  
- **Diagnostics** (`python launcher.py info`): Validation of deps, camera, database status

### Core Architecture Layers
```
Input → MediaPipe Pose → Analyzers → Database/Logs → Web UI/Display
Camera   (33 landmarks)   (fitness/   (SQLite +     (REST API +  
                          surveillance) CSV files)   HTML/JS)
```

Key files: `app.py` (Flask), `run.py` (desktop), `launcher.py` (entry), `templates/index.html` (frontend)

## Critical Patterns (DO NOT CHANGE)

### 1. Cross-Module Imports
All modules use sys.path manipulation for imports. Preserve this pattern:
```python
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
```

### 2. State Machine Pattern
Exercise analyzers use Enum states with smoothing and min-duration requirements:
```python
# Example from squat_tracker.py
class SquatState(Enum): STANDING, DESCENDING, BOTTOM, ASCENDING
# Requires min_state_duration frames + collections.deque(maxlen=smoothing_window)
```

### 3. Thread-Safe Camera Access
All camera operations in web mode MUST use locks:
```python
with self.lock:  # In app.py VisionTrackApp
    ret, frame = self.camera.read()
```

### 4. Analyzer Fallback Pattern
Mode-specific analyzers use try/import fallback:
```python
def _init_fitness_analyzer(self):
    try:
        from modules.fitness_analyzer import FitnessAnalyzer
        return FitnessAnalyzer()
    except ImportError:
        return MultiPersonSquatTracker()  # Fallback
```

### 5. Visual Text Control
Global flag `DrawingUtils.FRAME_TEXT_ENABLED` controls on-frame text rendering (web UI handles most text):
```python
# In draw_utils.py - respects this flag before drawing text
if not DrawingUtils.FRAME_TEXT_ENABLED:
    return
```

## Core Integration Points

### MediaPipe Landmarks (33-point model)
- Hip: indices 23 (left), 24 (right)  
- Knee: indices 25 (left), 26 (right)
- Ankle: indices 27 (left), 28 (right)
- Use `utils/angles.py::calculate_angle(point1, point2, point3)` for joint angles

### Database & Logging
- `utils/database.py`: Auto-creates `visiontrack.db` with sessions, alerts, preferences tables
- `utils/csv_logger.py`: Session CSVs follow `session_YYYYMMDD_HHMMSS.csv` naming
- Both systems support concurrent access with threading locks

### Alert System
- `utils/alert_system.py`: Multi-channel alerts (CSV, audio beeps, email)
- Built-in cooldown (3-5 seconds) prevents spam
- Severity classification and real-time callbacks for web interface

### Person Detection & Tracking
- `modules/person_detector.py`: FallbackSinglePersonDetector, SimplePersonTracker
- Distance-based ID assignment with bbox expansion for pose region extraction
- Handles person entry/exit with persistent ID management

## REST API Endpoints

### Core Endpoints
- `GET /api/stats` — Real-time stats (FPS, people, reps, alerts). Frontend polls every ~1000ms
- `POST /api/mode/<mode>` — Switch between 'fitness', 'surveillance', 'gaming'  
- `GET /video_feed` — MJPEG stream with pose overlays
- `POST /api/control/<action>` — start/stop/reset operations

### Session Management
- `POST /api/session/save` — Save current session summary
- `GET /api/sessions` — Recent session history
- `GET /api/logs` — Available CSV log files
- `GET /api/download/<filename>` — Download log files

### Fitness Mode
- `POST /api/exercise/set/<type>` — Set exercise type (squat/pushup/bicep_curl)
- `POST /api/audio/toggle` — Toggle audio feedback

### Surveillance Mode  
- `GET /api/surveillance/alerts` — Recent surveillance alerts
- `GET /api/surveillance/stats` — Surveillance statistics
- `GET /api/surveillance/zones` — Configured restricted zones
- `POST /api/surveillance/zones` — Add new zone

## Development Workflows

### Setup (Windows PowerShell)
```powershell
# Clone and navigate to project
cd "d:\Major Project\OpenCV-major-project"

# Create and activate virtual environment  
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Verify installation
python launcher.py info
```

### Testing & Validation
```powershell
# Run existing tests
pytest test_surveillance.py -v
pytest verify_surveillance_fix.py -v

# Start web application
python launcher.py web
# Browse to http://localhost:5000

# Test desktop mode
python launcher.py desktop
# Controls: ESC (exit), Space (reset), S (save), M (mute)
```

### Common Debug Commands  
```powershell
# Check camera availability
python -c "import cv2; print('Camera:', cv2.VideoCapture(0).isOpened())"

# Check port usage (if 5000 busy)
netstat -ano | findstr :5000

# Kill process if needed
taskkill /PID <pid> /F
```

## Exercise Analysis System

### Supported Exercise Types
- **Squats**: Hip-knee-ankle angle analysis (90-170° range, optimal depth 90-110°)
- **Push-ups**: Shoulder-elbow-wrist angle + horizontal body position  
- **Bicep Curls**: Shoulder-elbow-wrist angle + vertical body position

### State Machine Flow
```
Unknown → Standing (>160°) → Descending → Bottom (<100°) → Ascending → Standing
```
Each transition requires `min_state_duration` frames to prevent noise.

### Form Quality Scoring
- Range: 60-100% (60% minimum to prevent negative feedback)
- Calculated based on depth quality, angle consistency, movement smoothness
- Updates stored in `utils/database.py` exercise_stats table

## Surveillance System

### Detection Capabilities
- **Person Tracking**: Multi-person with persistent IDs, movement trails
- **Zone Detection**: JSON-configured restricted areas in `utils/zone_config.json`
- **Behavior Analysis**: Fall detection, rapid movement, loitering detection
- **Alert Generation**: Real-time alerts with cooldown and severity classification

### Alert Types (AlertType enum)
- `PERSON_DETECTED`, `RESTRICTED_ZONE_ENTRY`, `RAPID_MOVEMENT`
- `FALL_DETECTED`, `LOITERING`, `UNUSUAL_POSTURE`

### Movement Thresholds
- Rapid movement: >300 pixels/second
- Loitering: <10 pixels/second for >30 seconds  
- Fall detection: >45° deviation from vertical

## Frontend Integration

### Web Interface (`templates/index.html`)
- Vanilla JavaScript with Tailwind CSS
- Real-time stats polling every 2 seconds via `fetch('/api/stats')`
- Mode switching with visual feedback
- Exercise selection panel (fitness mode only)
- Session log management with download capability

### Video Streaming
- MJPEG feed at `/video_feed` endpoint
- Pose landmarks and mode-specific overlays rendered server-side
- Minimal text overlays on video (most UI text moved to HTML panels)

## Data Storage & Session Management

### Database Schema (SQLite)
- `sessions`: session_id, mode, timestamps, stats, metadata
- `alerts`: alert records with person_id, location, confidence  
- `exercise_stats`: detailed per-rep analysis data
- `user_preferences`: configurable settings storage

### CSV Logging Format
```csv
timestamp,person_id,rep_number,knee_angle,squat_depth_quality,exercise_state,session_id
```

### File Organization
```
logs/
├── session_20241104_143022.csv          # Raw exercise data
├── session_20241104_143022_info.txt     # Session metadata  
├── session_20241104_143022_summary.txt  # Session summary
└── alerts_log.csv                       # Surveillance alerts
```

## Agent Guidelines for Code Changes

### Input/Output Contract
- **Inputs**: OpenCV BGR frames, MediaPipe NormalizedLandmarkList, JSON config
- **Outputs**: Annotated frames, session events, database records, CSV logs
- **Error Handling**: Camera disconnect, pose detection failures, missing dependencies

### Critical Bug Patterns to Avoid
- **MediaPipe Results**: Always check `if pose_results.pose_landmarks:` before accessing
- **NormalizedLandmarkList**: Previously had iteration bug — validate before using `.landmark` 
- **Threading**: Use locks for any camera or shared state access
- **Resource Cleanup**: Always release camera and close pose detector in cleanup

### Testing Requirements  
- Add unit tests for behavioral changes (happy path + edge case)
- Test both web and desktop modes if changes affect analyzers
- Validate CSV output format and database schema compatibility
- Run `python launcher.py info` before committing changes

### Performance Considerations
- Target 30+ FPS for real-time operation
- Keep CSV logging async where possible  
- Use database connection pooling for high-frequency writes
- Optimize MediaPipe model complexity based on hardware

## Configuration & Extensibility

### Adding New Exercise Types
1. Extend `ExerciseType` enum in `modules/fitness_analyzer.py`
2. Create detector class inheriting from `ExerciseDetector`
3. Add to `detectors` dict in `FitnessAnalyzer.__init__`
4. Update frontend exercise selection buttons

### Adding New Alert Types  
1. Extend `AlertType` enum in `modules/surveillance_analyzer.py`
2. Implement detection logic in analyzer methods
3. Add sound mapping in `utils/alert_system.py`
4. Update frontend alert display logic

### Zone Configuration
Edit `utils/zone_config.json`:
```json
{
  "zones": [{
    "zone_id": 1,
    "name": "Restricted Area",
    "points": [[x1,y1], [x2,y2], [x3,y3]],
    "alert_type": "restricted_zone_entry",
    "enabled": true
  }]
}
```

---

**Target**: `web` mode is primary (desktop is legacy). After changes, validate with `python launcher.py info` then `python launcher.py web`.