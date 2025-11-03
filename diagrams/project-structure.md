```
human_pose_estimation/
├── run.py                     # Main application entry point
├── modules/
│   ├── __init__.py
│   ├── pose_detector.py       # MediaPipe pose detection wrapper
│   ├── squat_tracker.py       # Exercise tracking and state machine
│   └── person_detector.py     # Multi-person detection (optional)
├── utils/
│   ├── __init__.py
│   ├── angles.py              # Joint angle calculation utilities
│   ├── draw_utils.py          # Visualization and drawing functions
│   ├── audio.py               # Audio feedback system
│   └── csv_logger.py          # Data logging and session management
├── logs/                      # Auto-generated session logs
├── requirements.txt           # Python dependencies
├── README.md                  # User documentation
└── synopsis.md               # This project overview
```