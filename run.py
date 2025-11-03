"""
Real-time Human Pose Estimation with Squat Tracking

A comprehensive system for real-time squat detection and counting using MediaPipe pose estimation.
Features multi-person tracking, audio feedback, CSV logging, and form analysis.

Controls:
- ESC: Exit application
- Space: Reset session
- 'S': Save session summary
- 'M': Toggle audio mute

Author: OpenCV Major Project
"""

import cv2
import time
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

# Import our modules
from modules.pose_detector import PoseDetector
from modules.squat_tracker import MultiPersonSquatTracker
from modules.person_detector import FallbackSinglePersonDetector, SimplePersonTracker
from utils.draw_utils import DrawingUtils
from utils.audio import AudioFeedback
from utils.csv_logger import SessionLogger


class SquatTrackingApp:
    """Main application class for real-time squat tracking."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the squat tracking application.
        
        Args:
            config (dict, optional): Configuration parameters
        """
        self.config = config or self._get_default_config()
        
        # Initialize components
        self.pose_detector = PoseDetector(
            model_complexity=self.config['pose_model_complexity'],
            min_detection_confidence=self.config['min_detection_confidence'],
            min_tracking_confidence=self.config['min_tracking_confidence']
        )
        
        self.squat_tracker = MultiPersonSquatTracker(self.config['squat_config'])
        self.person_detector = FallbackSinglePersonDetector()
        self.person_tracker = SimplePersonTracker()
        self.audio_feedback = AudioFeedback()
        self.session_logger = SessionLogger(self.config['log_directory'])
        
        # Video capture
        self.cap = None
        self.is_running = False
        self.flip_frame = self.config['flip_frame']
        
        # Performance tracking
        self.fps_calculator = FPSCalculator()
        self.frame_count = 0
        
        # UI state
        self.audio_muted = False
        self.show_pose_landmarks = self.config['show_pose_landmarks']
        
        # Set up callbacks
        self._setup_callbacks()
        
        print("Squat Tracking App initialized successfully!")
        print(f"Audio available: {self.audio_feedback.is_audio_available()}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration parameters."""
        return {
            'camera_index': 0,
            'flip_frame': True,
            'pose_model_complexity': 1,
            'min_detection_confidence': 0.5,
            'min_tracking_confidence': 0.5,
            'log_directory': 'logs',
            'show_pose_landmarks': True,
            'squat_config': {
                'upright_threshold': 160.0,
                'squat_threshold': 100.0,
                'good_depth_min': 90.0,
                'good_depth_max': 110.0,
                'smoothing_window': 5,
                'min_state_duration': 3
            }
        }
    
    def _setup_callbacks(self):
        """Set up event callbacks for the tracking system."""
        
        def on_rep_completed(person_id: int, rep_count: int, min_angle: float):
            """Handle rep completion event."""
            if not self.audio_muted:
                self.audio_feedback.play_rep_count_beep()
                
                # Special milestone beeps
                if rep_count % 10 == 0:
                    self.audio_feedback.play_milestone_beep(rep_count)
            
            # Log the rep
            tracker = self.squat_tracker.trackers.get(person_id)
            if tracker:
                depth_quality = tracker.current_depth_quality.value
                state = tracker.current_state.value
                self.session_logger.log_rep(person_id, rep_count, min_angle, 
                                          depth_quality, state)
            
            print(f"Person {person_id}: Rep #{rep_count} completed! Angle: {min_angle:.1f}°")
        
        def on_new_person(person_id: int):
            """Handle new person detection."""
            print(f"New person detected: ID {person_id}")
        
        self.squat_tracker.on_rep_completed = on_rep_completed
        self.squat_tracker.on_new_person = on_new_person
    
    def initialize_camera(self) -> bool:
        """
        Initialize video capture.
        
        Returns:
            bool: True if camera initialized successfully
        """
        self.cap = cv2.VideoCapture(self.config['camera_index'])
        
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.config['camera_index']}")
            return False
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("Camera initialized successfully")
        return True
    
    def process_frame(self, frame):
        """
        Process a single frame for pose detection and squat tracking.
        
        Args:
            frame (numpy.ndarray): Input frame
            
        Returns:
            numpy.ndarray: Processed frame with overlays
        """
        height, width = frame.shape[:2]
        
        # Detect people in frame (using fallback single-person detector)
        person_detections = self.person_detector.detect(frame)
        
        # Track persons and assign IDs
        person_assignments = self.person_tracker.update(person_detections)
        
        # Process each detected person
        for person_id, detection in person_assignments.items():
            # Get expanded bounding box for better pose detection
            expanded_bbox = detection.get_expanded_bbox(0.1)
            x, y, w, h = expanded_bbox
            
            # Ensure bbox is within frame bounds
            x = max(0, x)
            y = max(0, y)
            w = min(w, width - x)
            h = min(h, height - y)
            
            if w <= 0 or h <= 0:
                continue
            
            # Extract person region
            person_region = frame[y:y+h, x:x+w]
            
            if person_region.size == 0:
                continue
            
            # Run pose detection on person region
            pose_results = self.pose_detector.process_frame(person_region)
            
            if pose_results.pose_landmarks:
                # Extract keypoints and convert to frame coordinates
                keypoints = self.pose_detector.extract_keypoints(
                    pose_results.pose_landmarks, w, h
                )
                
                # Adjust keypoints to frame coordinates
                adjusted_keypoints = {}
                for name, (kx, ky, visibility) in keypoints.items():
                    adjusted_keypoints[name] = (kx + x, ky + y, visibility)
                
                # Update squat tracker
                tracking_result = self.squat_tracker.update_person(person_id, adjusted_keypoints)
                
                # Draw pose landmarks if enabled
                if self.show_pose_landmarks:
                    # Create a copy of the region for landmark drawing
                    region_copy = person_region.copy()
                    self.pose_detector.draw_landmarks(
                        region_copy, pose_results.pose_landmarks
                    )
                    # Replace the region in the main frame
                    frame[y:y+h, x:x+w] = region_copy
                
                # Draw person bounding box and info
                DrawingUtils.draw_bounding_box(frame, (x, y, w, h), person_id)
                
                # Draw tracking information
                info_y = y - 60 if y >= 60 else y + h + 10
                DrawingUtils.draw_person_info(
                    frame, person_id, 
                    tracking_result['rep_count'],
                    tracking_result['current_state'],
                    tracking_result['smoothed_angle'],
                    position=(x, info_y)
                )
                
                # Draw squat depth feedback
                if tracking_result['current_state'] == 'bottom':
                    feedback_y = info_y + 80
                    DrawingUtils.draw_squat_feedback(
                        frame, tracking_result['depth_quality'],
                        position=(x, feedback_y)
                    )
        
        return frame
    
    def draw_ui_overlays(self, frame):
        """
        Draw UI overlays on the frame.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
        """
        # Draw FPS
        fps = self.fps_calculator.get_fps()
        DrawingUtils.draw_fps(frame, fps)
        
        # Draw session info
        stats = self.squat_tracker.get_aggregate_stats()
        session_info_y = 60
        
        DrawingUtils.draw_text(
            frame, f"Total Reps: {stats['total_reps']}", 
            (10, session_info_y), color=DrawingUtils.WHITE, background=True
        )
        
        DrawingUtils.draw_text(
            frame, f"Active People: {stats['active_people']}", 
            (10, session_info_y + 25), color=DrawingUtils.WHITE, background=True
        )
        
        session_duration = int(stats['session_duration'])
        DrawingUtils.draw_text(
            frame, f"Session: {session_duration//60:02d}:{session_duration%60:02d}", 
            (10, session_info_y + 50), color=DrawingUtils.WHITE, background=True
        )
        
        # Draw controls info
        height = frame.shape[0]
        controls_y = height - 60
        
        DrawingUtils.draw_text(
            frame, "ESC: Exit | Space: Reset | S: Save | M: Mute", 
            (10, controls_y), font_scale=0.5, color=DrawingUtils.LIGHT_GRAY, background=True
        )
        
        # Audio status
        audio_status = "Audio: MUTED" if self.audio_muted else "Audio: ON"
        DrawingUtils.draw_text(
            frame, audio_status, 
            (10, controls_y + 20), font_scale=0.5, 
            color=DrawingUtils.RED if self.audio_muted else DrawingUtils.GREEN,
            background=True
        )
    
    def handle_key_input(self, key: int) -> bool:
        """
        Handle keyboard input.
        
        Args:
            key (int): Key code
            
        Returns:
            bool: True to continue running, False to exit
        """
        if key == 27:  # ESC
            return False
        elif key == ord(' '):  # Space - Reset session
            self.reset_session()
        elif key == ord('s') or key == ord('S'):  # Save summary
            self.save_session_summary()
        elif key == ord('m') or key == ord('M'):  # Toggle mute
            self.audio_muted = not self.audio_muted
            print(f"Audio {'muted' if self.audio_muted else 'unmuted'}")
        elif key == ord('l') or key == ord('L'):  # Toggle landmarks
            self.show_pose_landmarks = not self.show_pose_landmarks
            print(f"Pose landmarks {'shown' if self.show_pose_landmarks else 'hidden'}")
        
        return True
    
    def reset_session(self):
        """Reset the current session."""
        print("Resetting session...")
        
        # Save current session summary before reset
        self.save_session_summary()
        
        # Reset all trackers
        self.squat_tracker.reset_session()
        self.person_tracker.reset()
        
        # Create new session logger
        self.session_logger = SessionLogger(self.config['log_directory'])
        
        # Play reset sound
        if not self.audio_muted:
            self.audio_feedback.play_session_start_beep()
        
        print("Session reset complete")
    
    def save_session_summary(self):
        """Save session summary report."""
        try:
            stats = self.squat_tracker.get_aggregate_stats()
            self.session_logger.log_session_end(
                stats['total_reps'], stats['active_people']
            )
            self.session_logger.export_summary_report()
            print(f"Session summary saved: {self.session_logger.get_log_file_path()}")
        except Exception as e:
            print(f"Error saving session summary: {e}")
    
    def run(self):
        """Main application loop."""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        self.session_logger.log_session_start(self.config)
        
        if not self.audio_muted:
            self.audio_feedback.play_session_start_beep()
        
        print("\n" + "="*50)
        print("SQUAT TRACKING SESSION STARTED")
        print("="*50)
        print("Controls:")
        print("  ESC: Exit")
        print("  Space: Reset session")
        print("  S: Save session summary")
        print("  M: Toggle audio mute")
        print("  L: Toggle pose landmarks")
        print("="*50 + "\n")
        
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Could not read frame")
                    break
                
                # Flip frame if configured
                if self.flip_frame:
                    frame = cv2.flip(frame, 1)
                
                # Update FPS calculator
                self.fps_calculator.update()
                self.frame_count += 1
                
                # Process frame
                processed_frame = self.process_frame(frame)
                
                # Draw UI overlays
                self.draw_ui_overlays(processed_frame)
                
                # Display frame
                cv2.imshow('Real-time Squat Tracker', processed_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if not self.handle_key_input(key):
                    break
                
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"Error during execution: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        print("\nCleaning up...")
        
        # Save final session summary
        self.save_session_summary()
        
        # Play exit sound
        if not self.audio_muted:
            self.audio_feedback.play_session_end_beep()
        
        # Release resources
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        
        # Close pose detector
        self.pose_detector.close()
        
        print("Session ended. Check logs folder for session data.")


class FPSCalculator:
    """Simple FPS calculator for performance monitoring."""
    
    def __init__(self, window_size: int = 30):
        """
        Initialize FPS calculator.
        
        Args:
            window_size (int): Number of frames to average over
        """
        self.window_size = window_size
        self.frame_times = []
        self.last_time = time.time()
    
    def update(self):
        """Update with current frame time."""
        current_time = time.time()
        self.frame_times.append(current_time - self.last_time)
        
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)
        
        self.last_time = current_time
    
    def get_fps(self) -> float:
        """Get current FPS."""
        if not self.frame_times:
            return 0.0
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0


def main():
    """Main entry point."""
    print("Starting Real-time Squat Tracking System...")
    
    # Create and run application
    app = SquatTrackingApp()
    app.run()


if __name__ == "__main__":
    main()
