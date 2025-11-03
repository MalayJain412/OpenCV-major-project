"""
VisionTrack: Real-Time Human Pose Estimation Web Application

A comprehensive web-based system for fitness tracking, surveillance monitoring,
and interactive pose detection using computer vision.

Author: VisionTrack Project
"""

try:
    from flask import Flask, render_template, Response, request, jsonify, send_file
    import cv2
    import json
    import os
    import sqlite3
    import threading
    import time
    from datetime import datetime
    from typing import Dict, Any, Optional
    import sys
    import numpy as np
except ImportError as e:
    print(f"❌ Missing required dependency: {e}")
    print("💡 Please install required packages:")
    print("   pip install flask opencv-python mediapipe numpy")
    sys.exit(1)

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

# Import existing modules
from modules.pose_detector import PoseDetector
from modules.squat_tracker import MultiPersonSquatTracker
from modules.person_detector import SimplePersonTracker
from utils.draw_utils import DrawingUtils
from utils.csv_logger import SessionLogger
from utils.database import db_manager

app = Flask(__name__)

class VisionTrackApp:
    """Main VisionTrack web application class."""
    
    def __init__(self):
        self.current_mode = "fitness"  # Default mode
        self.camera = None
        self.is_running = False
        self.frame = None
        self.lock = threading.Lock()
        self.current_session_id = None
        
        # Initialize components
        self.pose_detector = PoseDetector()
        self.drawing_utils = DrawingUtils()
        self.session_logger = SessionLogger()
        
        # Mode-specific analyzers
        self.fitness_analyzer = self._init_fitness_analyzer()
        self.surveillance_analyzer = self._init_surveillance_analyzer()
        
        # Stats
        self.stats = {
            'fps': 0,
            'detected_persons': 0,
            'session_reps': 0,
            'alerts_count': 0,
            'uptime': datetime.now()
        }
        
    def _init_fitness_analyzer(self):
        """Initialize fitness analyzer (fallback to squat tracker for now)."""
        try:
            from modules.fitness_analyzer import FitnessAnalyzer
            return FitnessAnalyzer()
        except ImportError:
            # Use existing squat tracker as fallback
            return MultiPersonSquatTracker()
    
    def _init_surveillance_analyzer(self):
        """Initialize surveillance analyzer."""
        try:
            from modules.surveillance_analyzer import SurveillanceAnalyzer
            return SurveillanceAnalyzer()
        except ImportError:
            # Placeholder until implemented
            return None
    
    def start_camera(self):
        """Start camera capture."""
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Create new session
        if not self.current_session_id:
            self.current_session_id = db_manager.create_session(
                mode=self.current_mode,
                metadata={'camera_resolution': '640x480', 'fps_target': 30}
            )
        
        self.is_running = True
        return True
    
    def stop_camera(self):
        """Stop camera capture."""
        self.is_running = False
        
        # End current session
        if self.current_session_id:
            session_duration = (datetime.now() - self.stats['uptime']).total_seconds()
            db_manager.update_session(
                self.current_session_id,
                end_time=datetime.now(),
                total_reps=self.stats['session_reps'],
                alerts_generated=self.stats['alerts_count'],
                duration_seconds=session_duration
            )
            self.current_session_id = None
        
        if self.camera:
            self.camera.release()
            self.camera = None
    
    def set_mode(self, mode: str):
        """Set the current operating mode."""
        valid_modes = ["fitness", "surveillance", "gaming"]
        if mode in valid_modes:
            # End current session if mode changes
            if self.current_session_id and mode != self.current_mode:
                self.stop_camera()
            
            self.current_mode = mode
            
            # Create new session for new mode if camera is running
            if self.is_running and not self.current_session_id:
                self.current_session_id = db_manager.create_session(
                    mode=mode,
                    metadata={'mode_changed': True}
                )
            
            return True
        return False
    
    def generate_frames(self):
        """Generate video frames for streaming."""
        fps_counter = 0
        fps_start_time = time.time()
        
        while self.is_running:
            if self.camera is None:
                continue
                
            success, frame = self.camera.read()
            if not success:
                continue
            
            # Process frame based on current mode
            processed_frame = self.process_frame(frame)
            
            # Calculate FPS
            fps_counter += 1
            if time.time() - fps_start_time >= 1.0:
                self.stats['fps'] = fps_counter
                fps_counter = 0
                fps_start_time = time.time()
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            
            # Store frame for other uses
            with self.lock:
                self.frame = processed_frame
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    def process_frame(self, frame):
        """Process frame based on current mode."""
        # Detect pose
        results = self.pose_detector.process_frame(frame)
        
        if self.current_mode == "fitness":
            return self.process_fitness_mode(frame, results)
        elif self.current_mode == "surveillance":
            return self.process_surveillance_mode(frame, results)
        elif self.current_mode == "gaming":
            return self.process_gaming_mode(frame, results)
        else:
            return frame
    
    def process_fitness_mode(self, frame, pose_results):
        """Process frame for fitness mode."""
        processed_frame = frame.copy()
        
        if pose_results.pose_landmarks:
            # Draw pose landmarks
            self.pose_detector.draw_landmarks(processed_frame, pose_results.pose_landmarks)
            self.stats['detected_persons'] = 1
            
            # Try to use enhanced fitness analyzer
            if hasattr(self.fitness_analyzer, 'process_frame'):
                try:
                    # Pass the pose_detector to the enhanced fitness analyzer
                    processed_frame = self.fitness_analyzer.process_frame(frame, self.pose_detector)
                    
                    # Get updated stats from fitness analyzer
                    summary = self.fitness_analyzer.get_session_summary()
                    self.stats['session_reps'] = summary.get('total_reps', 0)
                    self.stats['active_people'] = summary.get('people_tracked', 0)
                    self.stats['session_duration'] = summary.get('duration_seconds', 0)
                    
                except Exception as e:
                    print(f"Fitness analyzer error: {e}")
            elif hasattr(self.fitness_analyzer, 'update'):
                # Use squat tracker fallback
                try:
                    self.fitness_analyzer.update(pose_results.pose_landmarks)
                    # Get rep count if available
                    if hasattr(self.fitness_analyzer, 'get_session_summary'):
                        summary = self.fitness_analyzer.get_session_summary()
                        self.stats['session_reps'] = summary.get('total_reps', 0)
                except Exception as e:
                    print(f"Squat tracker error: {e}")
        else:
            self.stats['detected_persons'] = 0
        
        # Draw mode indicator
        cv2.putText(processed_frame, "FITNESS MODE", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return processed_frame
    
    def process_surveillance_mode(self, frame, pose_results):
        """Process frame for surveillance mode."""
        if self.surveillance_analyzer:
            processed_frame = self.surveillance_analyzer.process_frame(frame, pose_results)
        else:
            # Basic surveillance placeholder
            processed_frame = frame.copy()
            if pose_results.pose_landmarks:
                self.pose_detector.draw_landmarks(processed_frame, pose_results.pose_landmarks)
                self.stats['detected_persons'] = 1
        
        # Draw mode indicator
        cv2.putText(processed_frame, "SURVEILLANCE MODE", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return processed_frame
    
    def process_gaming_mode(self, frame, pose_results):
        """Process frame for gaming mode (coming soon)."""
        processed_frame = frame.copy()
        
        # Draw coming soon overlay
        overlay = processed_frame.copy()
        cv2.rectangle(overlay, (50, 100), (590, 200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, processed_frame, 0.3, 0, processed_frame)
        
        cv2.putText(processed_frame, "GAMING MODE", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(processed_frame, "COMING SOON!", (150, 140), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(processed_frame, "Interactive pose-based games", (120, 180), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
        return processed_frame

# Global app instance
vision_app = VisionTrackApp()

# Flask Routes
@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    if not vision_app.is_running:
        vision_app.start_camera()
    
    return Response(vision_app.generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/mode/<mode>', methods=['POST'])
def set_mode(mode):
    """Set the current mode."""
    if vision_app.set_mode(mode):
        return jsonify({'success': True, 'mode': mode})
    else:
        return jsonify({'success': False, 'error': 'Invalid mode'}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current statistics."""
    uptime_seconds = (datetime.now() - vision_app.stats['uptime']).total_seconds()
    stats = vision_app.stats.copy()
    stats['uptime_seconds'] = uptime_seconds
    stats['current_mode'] = vision_app.current_mode
    return jsonify(stats)

@app.route('/api/control/<action>', methods=['POST'])
def control_action(action):
    """Control actions (start, stop, reset)."""
    if action == 'start':
        success = vision_app.start_camera()
        return jsonify({'success': success})
    elif action == 'stop':
        vision_app.stop_camera()
        return jsonify({'success': True})
    elif action == 'reset':
        # Reset session data
        if hasattr(vision_app.fitness_analyzer, 'reset_session'):
            vision_app.fitness_analyzer.reset_session()
        vision_app.stats['session_reps'] = 0
        vision_app.stats['alerts_count'] = 0
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400

@app.route('/api/session/save', methods=['POST'])
def save_session():
    """Save current session summary."""
    try:
        if hasattr(vision_app.fitness_analyzer, 'save_session_summary'):
            log_file = vision_app.fitness_analyzer.save_session_summary()
            return jsonify({'success': True, 'log_file': log_file})
        else:
            return jsonify({'success': False, 'error': 'Session save not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/audio/toggle', methods=['POST'])
def toggle_audio():
    """Toggle audio feedback."""
    try:
        if hasattr(vision_app.fitness_analyzer, 'toggle_audio'):
            audio_enabled = vision_app.fitness_analyzer.toggle_audio()
            return jsonify({'success': True, 'audio_enabled': audio_enabled})
        else:
            return jsonify({'success': False, 'error': 'Audio control not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/exercise/set/<exercise_type>', methods=['POST'])
def set_exercise_type(exercise_type):
    """Set the exercise type."""
    try:
        if hasattr(vision_app.fitness_analyzer, 'set_exercise_type'):
            # Import ExerciseType if fitness analyzer is available
            from modules.fitness_analyzer import ExerciseType
            
            exercise_map = {
                'squat': ExerciseType.SQUAT,
                'pushup': ExerciseType.PUSHUP,
                'bicep_curl': ExerciseType.BICEP_CURL
            }
            
            if exercise_type in exercise_map:
                vision_app.fitness_analyzer.set_exercise_type(exercise_map[exercise_type])
                return jsonify({'success': True, 'exercise_type': exercise_type})
            else:
                return jsonify({'success': False, 'error': 'Invalid exercise type'})
        else:
            return jsonify({'success': False, 'error': 'Exercise type setting not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get session logs."""
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(logs_dir):
        return jsonify([])
    
    log_files = []
    for file in os.listdir(logs_dir):
        if file.endswith('.csv'):
            file_path = os.path.join(logs_dir, file)
            stat = os.stat(file_path)
            log_files.append({
                'filename': file,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(log_files)

@app.route('/api/download/<filename>')
def download_log(filename):
    """Download a log file."""
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    file_path = os.path.join(logs_dir, filename)
    
    if os.path.exists(file_path) and filename.endswith('.csv'):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get recent sessions."""
    limit = request.args.get('limit', 20, type=int)
    mode = request.args.get('mode', None)
    
    sessions = db_manager.get_recent_sessions(limit=limit, mode=mode)
    
    session_data = []
    for session in sessions:
        session_dict = {
            'session_id': session.session_id,
            'mode': session.mode,
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'total_reps': session.total_reps,
            'calories_burned': session.calories_burned,
            'people_detected': session.people_detected,
            'alerts_generated': session.alerts_generated,
            'duration_seconds': session.duration_seconds,
            'exercise_type': session.exercise_type,
            'form_score_avg': session.form_score_avg
        }
        session_data.append(session_dict)
    
    return jsonify(session_data)

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """Get detailed session information."""
    session = db_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    alerts = db_manager.get_session_alerts(session_id)
    
    session_dict = {
        'session_id': session.session_id,
        'mode': session.mode,
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat() if session.end_time else None,
        'total_reps': session.total_reps,
        'calories_burned': session.calories_burned,
        'people_detected': session.people_detected,
        'alerts_generated': session.alerts_generated,
        'duration_seconds': session.duration_seconds,
        'exercise_type': session.exercise_type,
        'form_score_avg': session.form_score_avg,
        'metadata': session.metadata
    }
    
    alert_data = []
    for alert in alerts:
        alert_dict = {
            'alert_id': alert.alert_id,
            'alert_type': alert.alert_type,
            'timestamp': alert.timestamp.isoformat(),
            'person_id': alert.person_id,
            'location': [alert.location_x, alert.location_y],
            'confidence': alert.confidence,
            'description': alert.description,
            'resolved': alert.resolved
        }
        alert_data.append(alert_dict)
    
    return jsonify({
        'session': session_dict,
        'alerts': alert_data
    })

# Surveillance-specific API routes
@app.route('/api/surveillance/alerts', methods=['GET'])
def get_surveillance_alerts():
    """Get recent surveillance alerts."""
    if vision_app.surveillance_analyzer and hasattr(vision_app.surveillance_analyzer, 'alert_system'):
        limit = request.args.get('limit', 20, type=int)
        alert_type = request.args.get('type', None)
        
        if alert_type:
            alerts = vision_app.surveillance_analyzer.alert_system.get_alerts_by_type(alert_type, limit)
        else:
            alerts = vision_app.surveillance_analyzer.alert_system.get_recent_alerts(limit)
        
        return jsonify({
            'alerts': alerts,
            'total_alerts': len(alerts)
        })
    
    return jsonify({'alerts': [], 'total_alerts': 0})

@app.route('/api/surveillance/stats', methods=['GET'])
def get_surveillance_stats():
    """Get surveillance statistics."""
    if vision_app.surveillance_analyzer:
        surveillance_stats = vision_app.surveillance_analyzer.get_surveillance_summary()
        
        # Get alert statistics if available
        alert_stats = {}
        if hasattr(vision_app.surveillance_analyzer, 'alert_system'):
            alert_stats = vision_app.surveillance_analyzer.alert_system.get_alert_statistics()
        
        return jsonify({
            'surveillance': surveillance_stats,
            'alerts': alert_stats
        })
    
    return jsonify({'error': 'Surveillance analyzer not available'})

@app.route('/api/surveillance/zones', methods=['GET'])
def get_surveillance_zones():
    """Get configured surveillance zones."""
    if vision_app.surveillance_analyzer:
        zones = []
        for zone_id, zone in vision_app.surveillance_analyzer.restricted_zones.items():
            zones.append({
                'zone_id': zone.zone_id,
                'name': zone.name,
                'points': zone.points.tolist(),
                'alert_type': zone.alert_type.value,
                'enabled': zone.enabled
            })
        
        return jsonify({'zones': zones})
    
    return jsonify({'zones': []})

@app.route('/api/surveillance/zones', methods=['POST'])
def add_surveillance_zone():
    """Add a new surveillance zone."""
    if not vision_app.surveillance_analyzer:
        return jsonify({'error': 'Surveillance analyzer not available'}), 400
    
    data = request.json
    required_fields = ['name', 'points']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        from modules.surveillance_analyzer import AlertType
        
        zone_id = max(vision_app.surveillance_analyzer.restricted_zones.keys(), default=0) + 1
        alert_type = AlertType(data.get('alert_type', 'restricted_zone_entry'))
        
        vision_app.surveillance_analyzer.add_restricted_zone(
            zone_id=zone_id,
            name=data['name'],
            points=[(point[0], point[1]) for point in data['points']],
            alert_type=alert_type
        )
        
        return jsonify({'success': True, 'zone_id': zone_id})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/zones/<int:zone_id>', methods=['DELETE'])
def remove_surveillance_zone(zone_id):
    """Remove a surveillance zone."""
    if not vision_app.surveillance_analyzer:
        return jsonify({'error': 'Surveillance analyzer not available'}), 400
    
    vision_app.surveillance_analyzer.remove_restricted_zone(zone_id)
    return jsonify({'success': True})

@app.route('/api/surveillance/alerts/export', methods=['POST'])
def export_surveillance_alerts():
    """Export surveillance alerts to file."""
    if not vision_app.surveillance_analyzer or not hasattr(vision_app.surveillance_analyzer, 'alert_system'):
        return jsonify({'error': 'Alert system not available'}), 400
    
    filename = f"surveillance_alerts_{int(time.time())}.json"
    filepath = os.path.join('logs', filename)
    
    if vision_app.surveillance_analyzer.alert_system.export_alerts_to_json(filepath):
        return jsonify({'success': True, 'filename': filename, 'filepath': filepath})
    else:
        return jsonify({'error': 'Export failed'}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics summary."""
    days = request.args.get('days', 7, type=int)
    analytics = db_manager.get_analytics_summary(days=days)
    return jsonify(analytics)

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Mark an alert as resolved."""
    db_manager.resolve_alert(alert_id)
    return jsonify({'success': True})

@app.route('/api/preferences', methods=['GET', 'POST'])
def handle_preferences():
    """Get or set user preferences."""
    if request.method == 'GET':
        category = request.args.get('category')
        key = request.args.get('key')
        
        if category and key:
            value = db_manager.get_user_preference(category, key)
            return jsonify({'value': value})
        else:
            return jsonify({'error': 'Category and key required'}), 400
    
    elif request.method == 'POST':
        data = request.get_json()
        category = data.get('category')
        key = data.get('key')
        value = data.get('value')
        
        if category and key and value is not None:
            db_manager.set_user_preference(category, key, str(value))
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Category, key, and value required'}), 400

@app.route('/api/export/<session_id>')
def export_session(session_id):
    """Export session data as JSON."""
    export_data = db_manager.export_session_data(session_id)
    if not export_data:
        return jsonify({'error': 'Session not found'}), 404
    
    # Create temporary file for download
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(export_data, f, indent=2)
        temp_path = f.name
    
    return send_file(temp_path, as_attachment=True, 
                    download_name=f'session_{session_id}_export.json',
                    mimetype='application/json')

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Run the app
    print("Starting VisionTrack Web Application...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)