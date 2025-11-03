"""
Enhanced Fitness Analyzer Module

Extends the existing squat tracker to support multiple exercises including
squats, push-ups, bicep curls, and provides unified fitness analysis.

Author: VisionTrack Project
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import time
from dataclasses import dataclass
from enum import Enum
import mediapipe as mp

# Import existing modules
from modules.squat_tracker import MultiPersonSquatTracker
from modules.person_detector import FallbackSinglePersonDetector, SimplePersonTracker
from utils.angles import calculate_angle
from utils.draw_utils import DrawingUtils
from utils.audio import AudioFeedback
from utils.csv_logger import SessionLogger


class ExerciseType(Enum):
    """Supported exercise types."""
    SQUAT = "squat"
    PUSHUP = "pushup"
    BICEP_CURL = "bicep_curl"
    PLANK = "plank"


@dataclass
class ExerciseState:
    """State information for an exercise."""
    exercise_type: ExerciseType
    phase: str  # up, down, bottom, top
    rep_count: int
    last_angle: float
    confidence: float
    form_score: float


class ExerciseDetector:
    """Base class for exercise detection."""
    
    def __init__(self, exercise_type: ExerciseType):
        self.exercise_type = exercise_type
        self.state = ExerciseState(
            exercise_type=exercise_type,
            phase="unknown",
            rep_count=0,
            last_angle=0.0,
            confidence=0.0,
            form_score=100.0
        )
    
    def detect_exercise(self, landmarks) -> bool:
        """Detect if the exercise is being performed."""
        raise NotImplementedError
    
    def process_frame(self, landmarks) -> ExerciseState:
        """Process a frame and return exercise state."""
        raise NotImplementedError


class SquatDetector(ExerciseDetector):
    """Enhanced squat detector based on existing tracker."""
    
    def __init__(self):
        super().__init__(ExerciseType.SQUAT)
        self.upright_threshold = 160
        self.squat_threshold = 100
        self.good_depth_min = 90
        self.good_depth_max = 110
        
    def detect_exercise(self, landmarks) -> bool:
        """Detect if squats are being performed."""
        try:
            # Get hip, knee, ankle landmarks
            hip = landmarks[23]  # Left hip
            knee = landmarks[25]  # Left knee
            ankle = landmarks[27]  # Left ankle
            
            # Calculate knee angle
            knee_angle = calculate_angle(hip, knee, ankle)
            return 90 <= knee_angle <= 170  # Valid squat range
        except:
            return False
    
    def process_frame(self, landmarks) -> ExerciseState:
        """Process frame for squat detection."""
        try:
            # Get landmarks
            hip = landmarks[23]
            knee = landmarks[25]
            ankle = landmarks[27]
            
            # Calculate knee angle
            knee_angle = calculate_angle(hip, knee, ankle)
            
            # Determine phase and count reps
            if knee_angle > self.upright_threshold:
                if self.state.phase == "bottom":
                    self.state.rep_count += 1
                self.state.phase = "up"
            elif knee_angle < self.squat_threshold:
                self.state.phase = "bottom"
            else:
                self.state.phase = "down" if self.state.last_angle > knee_angle else "up"
            
            # Calculate form score
            if self.state.phase == "bottom":
                if self.good_depth_min <= knee_angle <= self.good_depth_max:
                    self.state.form_score = min(100.0, self.state.form_score + 1)
                else:
                    self.state.form_score = max(60.0, self.state.form_score - 2)
            
            self.state.last_angle = knee_angle
            self.state.confidence = 0.9 if knee_angle > 0 else 0.0
            
        except Exception as e:
            self.state.confidence = 0.0
        
        return self.state


class PushupDetector(ExerciseDetector):
    """Push-up detector using shoulder-elbow-wrist angle."""
    
    def __init__(self):
        super().__init__(ExerciseType.PUSHUP)
        self.up_threshold = 160
        self.down_threshold = 90
        self.good_depth_min = 80
        self.good_depth_max = 100
    
    def detect_exercise(self, landmarks) -> bool:
        """Detect if push-ups are being performed."""
        try:
            # Check if person is in horizontal position
            shoulder = landmarks[11]  # Left shoulder
            hip = landmarks[23]      # Left hip
            
            # Calculate body angle (should be close to horizontal for pushups)
            body_angle = abs(np.arctan2(hip.y - shoulder.y, hip.x - shoulder.x) * 180 / np.pi)
            return body_angle < 30  # Body is roughly horizontal
        except:
            return False
    
    def process_frame(self, landmarks) -> ExerciseState:
        """Process frame for push-up detection."""
        try:
            # Get arm landmarks
            shoulder = landmarks[11]  # Left shoulder
            elbow = landmarks[13]     # Left elbow
            wrist = landmarks[15]     # Left wrist
            
            # Calculate elbow angle
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            
            # Determine phase and count reps
            if elbow_angle > self.up_threshold:
                if self.state.phase == "bottom":
                    self.state.rep_count += 1
                self.state.phase = "up"
            elif elbow_angle < self.down_threshold:
                self.state.phase = "bottom"
            else:
                self.state.phase = "down" if self.state.last_angle > elbow_angle else "up"
            
            # Calculate form score
            if self.state.phase == "bottom":
                if self.good_depth_min <= elbow_angle <= self.good_depth_max:
                    self.state.form_score = min(100.0, self.state.form_score + 1)
                else:
                    self.state.form_score = max(60.0, self.state.form_score - 2)
            
            self.state.last_angle = elbow_angle
            self.state.confidence = 0.8 if elbow_angle > 0 else 0.0
            
        except Exception as e:
            self.state.confidence = 0.0
        
        return self.state


class BicepCurlDetector(ExerciseDetector):
    """Bicep curl detector using shoulder-elbow-wrist angle."""
    
    def __init__(self):
        super().__init__(ExerciseType.BICEP_CURL)
        self.up_threshold = 40   # Arm fully curled
        self.down_threshold = 160  # Arm extended
    
    def detect_exercise(self, landmarks) -> bool:
        """Detect if bicep curls are being performed."""
        try:
            # Check if person is standing upright
            shoulder = landmarks[11]  # Left shoulder
            hip = landmarks[23]      # Left hip
            
            # Calculate body angle (should be upright for bicep curls)
            body_angle = abs(np.arctan2(hip.y - shoulder.y, hip.x - shoulder.x) * 180 / np.pi)
            return body_angle > 70  # Body is roughly vertical
        except:
            return False
    
    def process_frame(self, landmarks) -> ExerciseState:
        """Process frame for bicep curl detection."""
        try:
            # Get arm landmarks
            shoulder = landmarks[11]  # Left shoulder
            elbow = landmarks[13]     # Left elbow
            wrist = landmarks[15]     # Left wrist
            
            # Calculate elbow angle
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            
            # Determine phase and count reps
            if elbow_angle < self.up_threshold:
                if self.state.phase == "down":
                    self.state.rep_count += 1
                self.state.phase = "up"
            elif elbow_angle > self.down_threshold:
                self.state.phase = "down"
            else:
                self.state.phase = "up" if self.state.last_angle > elbow_angle else "down"
            
            # Form score for bicep curls (smooth motion)
            angle_change = abs(elbow_angle - self.state.last_angle)
            if angle_change < 5:  # Smooth motion
                self.state.form_score = min(100.0, self.state.form_score + 0.5)
            elif angle_change > 15:  # Jerky motion
                self.state.form_score = max(60.0, self.state.form_score - 1)
            
            self.state.last_angle = elbow_angle
            self.state.confidence = 0.7 if elbow_angle > 0 else 0.0
            
        except Exception as e:
            self.state.confidence = 0.0
        
        return self.state


class FitnessAnalyzer:
    """Unified fitness analysis system supporting multiple exercises."""
    
    def __init__(self):
        self.drawing_utils = DrawingUtils()
        
        # Use robust person detection from run.py
        self.person_detector = FallbackSinglePersonDetector()
        self.person_tracker = SimplePersonTracker()
        
        # MediaPipe drawing utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        
        # Exercise detectors
        self.detectors = {
            ExerciseType.SQUAT: SquatDetector(),
            ExerciseType.PUSHUP: PushupDetector(),
            ExerciseType.BICEP_CURL: BicepCurlDetector()
        }
        
        # For squat mode, use the robust MultiPersonSquatTracker
        self.squat_tracker = MultiPersonSquatTracker()
        
        # Audio feedback
        self.audio_feedback = AudioFeedback()
        self.audio_muted = False
        
        # Current state (define before session logger)
        self.current_exercise = ExerciseType.SQUAT  # Default
        self.auto_detect = True  # Auto-detect exercise type
        self.person_states = {}  # Per-person exercise states
        
        # Session stats
        self.total_reps = 0
        self.calories_estimate = 0.0
        self.active_people = 0
        
        # Session management
        self.session_logger = SessionLogger('logs')  # Initialize by default
        self.session_start_time = time.time()
        
        # Initialize session logging
        self.session_logger.log_session_start({
            'exercise_type': self.current_exercise.value,
            'auto_detect': self.auto_detect
        })
        
        # Setup callbacks for squat tracker
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Set up event callbacks for the tracking system."""
        
        def on_rep_completed(person_id: int, rep_count: int, min_angle: float):
            """Handle rep completion event."""
            if not self.audio_muted:
                self.audio_feedback.play_rep_count_beep()
                
                # Special milestone beeps
                if rep_count % 10 == 0:
                    self.audio_feedback.play_milestone_beep(rep_count)
            
            # Log the rep if session logger exists
            if self.session_logger:
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
    
    def set_session_logger(self, log_directory: str = 'logs'):
        """Initialize session logger."""
        self.session_logger = SessionLogger(log_directory)
        
    def set_exercise_type(self, exercise_type: ExerciseType):
        """Manually set the exercise type."""
        self.current_exercise = exercise_type
        self.auto_detect = False
    
    def enable_auto_detection(self):
        """Enable automatic exercise detection."""
        self.auto_detect = True
    
    def detect_exercise_type(self, landmarks) -> ExerciseType:
        """Automatically detect the exercise type being performed."""
        exercise_scores = {}
        
        for exercise_type, detector in self.detectors.items():
            if detector.detect_exercise(landmarks):
                exercise_scores[exercise_type] = detector.state.confidence
        
        if exercise_scores:
            return max(exercise_scores, key=exercise_scores.get)
        
        return self.current_exercise  # Default to current exercise
    
    def process_frame(self, frame, pose_detector):
        """Process a frame with robust person detection and tracking."""
        if frame is None:
            return frame

        processed_frame = frame.copy()
        height, width = frame.shape[:2]
        
        # Use current exercise mode
        if self.current_exercise == ExerciseType.SQUAT:
            # Use robust squat tracking from run.py
            return self._process_squat_mode(processed_frame, pose_detector)
        else:
            # Use other exercise detection
            return self._process_other_exercises(processed_frame, pose_detector)
    
    def _process_squat_mode(self, frame, pose_detector):
        """Process frame using robust squat tracking."""
        height, width = frame.shape[:2]
        
        # Detect people in frame
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
            pose_results = pose_detector.process_frame(person_region)
            
            if pose_results.pose_landmarks:
                # Extract keypoints and convert to frame coordinates
                keypoints = pose_detector.extract_keypoints(
                    pose_results.pose_landmarks, w, h
                )
                
                # Adjust keypoints to frame coordinates
                adjusted_keypoints = {}
                for name, (kx, ky, visibility) in keypoints.items():
                    adjusted_keypoints[name] = (kx + x, ky + y, visibility)
                
                # Update squat tracker
                tracking_result = self.squat_tracker.update_person(person_id, adjusted_keypoints)
                
                # Draw pose landmarks
                region_copy = person_region.copy()
                pose_detector.draw_landmarks(region_copy, pose_results.pose_landmarks)
                frame[y:y+h, x:x+w] = region_copy
                
                # Draw person bounding box and info
                self.drawing_utils.draw_bounding_box(frame, (x, y, w, h), person_id)
                
                # Draw tracking information
                info_y = y - 60 if y >= 60 else y + h + 10
                self.drawing_utils.draw_person_info(
                    frame, person_id, 
                    tracking_result['rep_count'],
                    tracking_result['current_state'],
                    tracking_result['smoothed_angle'],
                    position=(x, info_y)
                )
                
                # Draw squat depth feedback
                if tracking_result['current_state'] == 'bottom':
                    feedback_y = info_y + 80
                    self.drawing_utils.draw_squat_feedback(
                        frame, tracking_result['depth_quality'],
                        position=(x, feedback_y)
                    )
        
        # Update session stats from squat tracker
        stats = self.squat_tracker.get_aggregate_stats()
        self.total_reps = stats['total_reps']
        self.active_people = stats['active_people']
        
        return frame
    
    def _process_other_exercises(self, frame, pose_detector):
        """Process frame for other exercises (pushups, bicep curls, etc.)."""
        # Run pose detection on full frame for other exercises
        pose_results = pose_detector.process_frame(frame)
        
        if pose_results.pose_landmarks:
            pose_landmarks_list = [pose_results.pose_landmarks]
            
            # Process each person's pose landmarks directly (simplified for other exercises)
            for person_id, landmarks in enumerate(pose_landmarks_list):
                if landmarks is None:
                    continue
                    
                # Auto-detect exercise if enabled
                if self.auto_detect:
                    detected_exercise = self.detect_exercise_type(landmarks.landmark)
                    if detected_exercise != self.current_exercise:
                        self.current_exercise = detected_exercise
                
                # Get or create person state
                if person_id not in self.person_states:
                    self.person_states[person_id] = {
                        exercise_type: ExerciseState(
                            exercise_type=exercise_type,
                            phase="unknown",
                            rep_count=0,
                            last_angle=0.0,
                            confidence=0.0,
                            form_score=100.0
                        ) for exercise_type in ExerciseType
                    }
                
                # Process current exercise
                detector = self.detectors[self.current_exercise]
                exercise_state = detector.process_frame(landmarks.landmark)
                self.person_states[person_id][self.current_exercise] = exercise_state
                
                # Draw person tracking
                self.draw_person_analysis(frame, landmarks, person_id, exercise_state)
                
                self.total_reps += exercise_state.rep_count
        
        # Update calories estimate
        self.update_calories_estimate()
        
        return frame
    
    def draw_person_analysis(self, frame, landmarks, person_id: int, exercise_state: ExerciseState):
        """Draw analysis overlay for a person."""
        # Draw pose landmarks using MediaPipe
        if landmarks:
            self.mp_drawing.draw_landmarks(
                frame,
                landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )
        
        # Get person's position for text overlay
        nose = landmarks.landmark[0]
        x = int(nose.x * frame.shape[1])
        y = int(nose.y * frame.shape[0])
        
        # Person ID and exercise info
        cv2.putText(frame, f"Person {person_id}", (x - 50, y - 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Exercise type
        cv2.putText(frame, f"{exercise_state.exercise_type.value.title()}", (x - 50, y - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        # Rep count
        cv2.putText(frame, f"Reps: {exercise_state.rep_count}", (x - 50, y - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Form score
        form_color = (0, 255, 0) if exercise_state.form_score > 80 else (0, 165, 255) if exercise_state.form_score > 60 else (0, 0, 255)
        cv2.putText(frame, f"Form: {exercise_state.form_score:.0f}%", (x - 50, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, form_color, 2)
        
        # Phase indicator
        phase_color = (0, 255, 0) if exercise_state.phase in ["up", "top"] else (255, 0, 0)
        cv2.putText(frame, f"Phase: {exercise_state.phase}", (x - 50, y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, phase_color, 2)
    
    def draw_session_info(self, frame):
        """Draw session information on the frame."""
        session_duration = time.time() - self.session_start_time
        
        # Session info panel
        info_y = 100
        cv2.putText(frame, f"Exercise: {self.current_exercise.value.title()}", (10, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Total Reps: {self.total_reps}", (10, info_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.putText(frame, f"Duration: {int(session_duration//60):02d}:{int(session_duration%60):02d}", 
                   (10, info_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        cv2.putText(frame, f"Calories: {self.calories_estimate:.1f}", (10, info_y + 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
        
        # Auto-detect indicator
        if self.auto_detect:
            cv2.putText(frame, "AUTO-DETECT ON", (10, info_y + 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    def update_calories_estimate(self):
        """Update calories burned estimate."""
        # Simple calorie estimation based on exercise type and reps
        calories_per_rep = {
            ExerciseType.SQUAT: 0.5,
            ExerciseType.PUSHUP: 0.3,
            ExerciseType.BICEP_CURL: 0.2
        }
        
        self.calories_estimate = self.total_reps * calories_per_rep.get(self.current_exercise, 0.3)
    
    def reset_session(self):
        """Reset session data with proper cleanup."""
        # Save current session summary first
        self.save_session_summary()
        
        # Reset session state
        self.session_start_time = time.time()
        self.total_reps = 0
        self.calories_estimate = 0.0
        self.person_states.clear()
        self.active_people = 0
        
        # Reset all detectors
        for detector in self.detectors.values():
            detector.state.rep_count = 0
            detector.state.form_score = 100.0
        
        # Reset squat tracker
        self.squat_tracker.reset_session()
        self.person_tracker.reset()
        
        # Create a new session logger for the new session
        self.session_logger = SessionLogger('logs')
        self.session_logger.log_session_start({
            'exercise_type': self.current_exercise.value,
            'auto_detect': self.auto_detect
        })
        
        # Play reset sound
        if not self.audio_muted:
            self.audio_feedback.play_session_start_beep()
        
        print("Session reset complete")
    
    def save_session_summary(self):
        """Save session summary report."""
        if not self.session_logger:
            print("No session logger available")
            return None
        
        try:
            if self.current_exercise == ExerciseType.SQUAT:
                # Use squat tracker stats for accurate data
                stats = self.squat_tracker.get_aggregate_stats()
                total_reps = stats['total_reps']
                active_people = stats['active_people']
            else:
                # Use fitness analyzer stats for other exercises
                total_reps = self.total_reps
                active_people = len(self.person_states)
            
            # Log session end with correct stats
            self.session_logger.log_session_end(total_reps, active_people)
            self.session_logger.export_summary_report()
            
            return self.session_logger.get_log_file_path()
        except Exception as e:
            print(f"Error saving session summary: {e}")
            return None
    
    def toggle_audio(self):
        """Toggle audio feedback."""
        self.audio_muted = not self.audio_muted
        return not self.audio_muted  # Return True if audio is now on
    
    def set_exercise_type(self, exercise_type: ExerciseType):
        """Manually set the exercise type."""
        self.current_exercise = exercise_type
        self.auto_detect = False
    
    def enable_auto_detection(self):
        """Enable automatic exercise detection."""
        self.auto_detect = True
    
    def get_session_summary(self) -> Dict:
        """Get current session summary with comprehensive stats."""
        session_duration = time.time() - self.session_start_time
        
        if self.current_exercise == ExerciseType.SQUAT:
            # Use squat tracker stats for more detailed information
            squat_stats = self.squat_tracker.get_aggregate_stats()
            return {
                'exercise_type': self.current_exercise.value,
                'total_reps': squat_stats['total_reps'],
                'duration_seconds': session_duration,
                'calories_estimate': self.calories_estimate,
                'people_tracked': squat_stats['active_people'],
                'auto_detect_enabled': self.auto_detect,
                'audio_enabled': not self.audio_muted,
                'session_start_time': self.session_start_time,
                # Additional squat-specific stats
                'average_depth': squat_stats.get('average_depth', 0),
                'form_quality': squat_stats.get('form_quality', 'Unknown')
            }
        else:
            return {
                'exercise_type': self.current_exercise.value,
                'total_reps': self.total_reps,
                'duration_seconds': session_duration,
                'calories_estimate': self.calories_estimate,
                'people_tracked': len(self.person_states),
                'auto_detect_enabled': self.auto_detect,
                'audio_enabled': not self.audio_muted,
                'session_start_time': self.session_start_time
            }