# VisionTrack AI Coding Agent Instructions

## Project Overview
VisionTrack is a real-time human pose estimation platform with **fitness tracking** and **surveillance monitoring**. Uses MediaPipe for pose detection, OpenCV for video processing, Flask web interface, and SQLite persistence.

## Entry Points & Architecture
- **Primary**: `python launcher.py web` - Flask web app (port 5000)
- **Diagnostics**: `python launcher.py info` - dependency/camera validation
- **Mode switching**: `VisionTrackApp.current_mode` ("fitness"/"surveillance") triggers different analyzer initialization

## Critical Patterns

### Module Import Strategy (Required)
All modules use sys.path append for cross-imports:
```python
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
```

### State Machine Pattern
Exercise tracking uses enum-based state machines with smoothing:
```python
# squat_tracker.py pattern
class SquatState(Enum): STANDING, DESCENDING, BOTTOM, ASCENDING
# Requires min_state_duration frames for state transitions
# Smoothing via deque(maxlen=smoothing_window) for angle stability
```

### Threading & Camera Safety
Web app requires thread locks for camera access:
```python
with self.lock:  # app.py pattern
    ret, frame = self.camera.read()
```

### Real-time Data Flow
1. `camera.read()` → `pose_detector.process_frame()` → MediaPipe landmarks
2. Landmarks → exercise analyzer → state machine → rep counting
3. Stats update → database session logging → web API response
4. Frontend polls `/api/stats` every 1000ms for live updates

## Development Workflows

### Starting Development
```bash
venv\Scripts\activate    # Windows activation (venv pre-configured)
python launcher.py info  # Verify camera/dependencies
python launcher.py web   # Start dev server (localhost:5000)
```

### Common Issues
- **Port 5000 in use**: `netstat -ano | findstr :5000` 
- **Camera test**: `python -c "import cv2; print('Camera:', cv2.VideoCapture(0).isOpened())"`
- **Missing deps**: `launcher.py` validates all packages

## Key Integration Points

### MediaPipe Landmarks (33-point model)
```python
landmarks[23] = left_hip, landmarks[25] = left_knee, landmarks[27] = left_ankle
# angles.py: calculate_angle(hip, knee, ankle) for exercise analysis
```

### Database Auto-Init
```python
from utils.database import db_manager
session_id = db_manager.create_session(mode="fitness", exercise_type="squat")
# Auto-creates visiontrack.db, logs to both SQLite + CSV
```

### Web API Pattern
- `/api/mode/<mode>` POST - Switch modes, creates new session
- `/api/stats` GET - Real-time FPS, person count, reps (polled every 1s)
- `/video_feed` - MJPEG stream with pose overlays
- Frontend: vanilla JS fetch() + Tailwind CSS

### Session Logging
All sessions auto-log with timestamp format: `session_YYYYMMDD_HHMMSS.csv`
```python
from utils.csv_logger import SessionLogger
logger.log_rep(person_id, rep_count, knee_angle, depth_quality)
```

## Configuration & Extensibility Patterns

### Analyzer Initialization Pattern
Mode-specific analyzers use fallback imports:
```python
def _init_fitness_analyzer(self):
    try:
        from modules.fitness_analyzer import FitnessAnalyzer
        return FitnessAnalyzer()
    except ImportError:
        return MultiPersonSquatTracker()  # Fallback
```

### Surveillance Zone Configuration
JSON-based zone definitions with runtime loading:
```python
# utils/zone_config.json structure
{"zones": [{"zone_id": 1, "name": "Restricted Area", "points": [[x,y]...]}]}
# Auto-loaded in SurveillanceAnalyzer.__init__()
```

### Visual Overlay Architecture
Centralized drawing with mode-specific helpers:
```python
from utils.draw_utils import DrawingUtils
# Non-textual markers only (text moved to web UI)
DrawingUtils.FRAME_TEXT_ENABLED = False  # Global text control
```

### Alert System Integration
Configurable alerting with multiple output channels:
```python
from utils.alert_system import AlertSystem, create_default_alert_system
# Supports audio beeps, CSV logging, email notifications
# Built-in cooldown periods and severity classification
```