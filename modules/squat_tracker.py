"""
Squat tracking module for real-time exercise form analysis.

This module implements a state machine for detecting and counting squats,
analyzing form quality, and providing feedback on exercise execution.
"""

from collections import deque
from enum import Enum
from typing import Optional, Dict, Tuple, Any
import time

from utils.angles import calculate_knee_angle, average_angles


class SquatState(Enum):
    """Enumeration of squat exercise states."""
    UNKNOWN = "unknown"
    STANDING = "standing"
    DESCENDING = "descending"
    BOTTOM = "bottom"
    ASCENDING = "ascending"


class SquatDepthQuality(Enum):
    """Enumeration of squat depth quality assessments."""
    GOOD = "good"
    SHALLOW = "shallow"
    TOO_DEEP = "too_deep"
    UNKNOWN = "unknown"


class SquatTracker:
    """
    Individual squat tracker for a single person.
    
    Tracks squat form, counts repetitions, and provides real-time feedback
    on exercise quality using joint angle analysis and state machine logic.
    """
    
    def __init__(self, person_id: int, config: Optional[Dict[str, Any]] = None):
        """
        Initialize squat tracker for a person.
        
        Args:
            person_id (int): Unique identifier for the person
            config (dict, optional): Configuration parameters
        """
        self.person_id = person_id
        self.config = config or {}
        
        # Configuration parameters with defaults
        self.upright_threshold = self.config.get('upright_threshold', 160.0)  # degrees
        self.squat_threshold = self.config.get('squat_threshold', 100.0)      # degrees
        self.good_depth_min = self.config.get('good_depth_min', 90.0)         # degrees
        self.good_depth_max = self.config.get('good_depth_max', 110.0)        # degrees
        self.smoothing_window = self.config.get('smoothing_window', 5)        # frames
        self.min_state_duration = self.config.get('min_state_duration', 3)    # frames
        
        # State tracking
        self.current_state = SquatState.UNKNOWN
        self.previous_state = SquatState.UNKNOWN
        self.state_frame_count = 0
        self.state_history = deque(maxlen=10)
        
        # Angle tracking with smoothing
        self.knee_angles = deque(maxlen=self.smoothing_window)
        self.smoothed_angle = None
        self.min_angle_in_rep = None
        
        # Rep counting
        self.rep_count = 0
        self.last_rep_time = None
        self.rep_start_time = None
        
        # Quality assessment
        self.current_depth_quality = SquatDepthQuality.UNKNOWN
        self.form_feedback = []
        
        # Performance metrics
        self.total_session_time = 0
        self.average_rep_time = 0
        self.best_depth_angle = None
        self.rep_angles = []  # Store min angle for each rep
        
        # Callbacks for events
        self.on_rep_completed = None
        self.on_state_changed = None
    
    def update(self, left_hip: Optional[Tuple[int, int]], 
               left_knee: Optional[Tuple[int, int]], 
               left_ankle: Optional[Tuple[int, int]],
               right_hip: Optional[Tuple[int, int]], 
               right_knee: Optional[Tuple[int, int]], 
               right_ankle: Optional[Tuple[int, int]]) -> Dict[str, Any]:
        """
        Update tracker with new pose landmarks.
        
        Args:
            left_hip, left_knee, left_ankle: Left leg joint coordinates
            right_hip, right_knee, right_ankle: Right leg joint coordinates
            
        Returns:
            dict: Current tracking state and metrics
        """
        # Calculate knee angles
        left_angle = None
        right_angle = None
        
        if all(point is not None for point in [left_hip, left_knee, left_ankle]):
            left_angle = calculate_knee_angle(left_hip, left_knee, left_ankle)
        
        if all(point is not None for point in [right_hip, right_knee, right_ankle]):
            right_angle = calculate_knee_angle(right_hip, right_knee, right_ankle)
        
        # Average the angles
        current_angle = average_angles(left_angle, right_angle)
        
        if current_angle is not None:
            self.knee_angles.append(current_angle)
            self.smoothed_angle = sum(self.knee_angles) / len(self.knee_angles)
        else:
            # If we can't calculate angle, maintain previous state
            pass
        
        # Update state machine
        self._update_state_machine()
        
        # Update quality assessment
        self._assess_squat_quality()
        
        # Check for rep completion
        rep_completed = self._check_rep_completion()
        
        # Update performance metrics
        self._update_performance_metrics()
        
        return {
            'person_id': self.person_id,
            'current_state': self.current_state.value,
            'smoothed_angle': self.smoothed_angle,
            'rep_count': self.rep_count,
            'depth_quality': self.current_depth_quality.value,
            'rep_completed': rep_completed,
            'form_feedback': self.form_feedback.copy(),
            'min_angle_in_rep': self.min_angle_in_rep,
            'average_rep_time': self.average_rep_time
        }
    
    def _update_state_machine(self):
        """Update the squat state machine based on current angle."""
        if self.smoothed_angle is None:
            return
        
        new_state = self._determine_state(self.smoothed_angle)
        
        if new_state == self.current_state:
            self.state_frame_count += 1
        else:
            # State change - require minimum duration for stability
            if self.state_frame_count >= self.min_state_duration:
                self.previous_state = self.current_state
                self.current_state = new_state
                self.state_frame_count = 1
                self.state_history.append((new_state, time.time()))
                
                # Trigger callback if set
                if self.on_state_changed:
                    self.on_state_changed(self.person_id, new_state, self.previous_state)
            else:
                self.state_frame_count += 1
    
    def _determine_state(self, angle: float) -> SquatState:
        """
        Determine squat state based on knee angle.
        
        Args:
            angle (float): Current smoothed knee angle
            
        Returns:
            SquatState: Determined state
        """
        if angle > self.upright_threshold:
            return SquatState.STANDING
        elif angle < self.squat_threshold:
            return SquatState.BOTTOM
        else:
            # Intermediate angle - determine based on previous state and trend
            if self.current_state == SquatState.STANDING:
                return SquatState.DESCENDING
            elif self.current_state in [SquatState.DESCENDING, SquatState.BOTTOM]:
                # Check if we're going down or up
                if len(self.knee_angles) >= 2:
                    recent_angles = list(self.knee_angles)[-2:]
                    if recent_angles[1] < recent_angles[0]:  # Angle decreasing
                        return SquatState.DESCENDING
                    else:  # Angle increasing
                        return SquatState.ASCENDING
                return SquatState.DESCENDING
            elif self.current_state == SquatState.ASCENDING:
                return SquatState.ASCENDING
            else:
                return SquatState.DESCENDING
    
    def _assess_squat_quality(self):
        """Assess the quality of the current squat."""
        if self.current_state == SquatState.BOTTOM and self.smoothed_angle is not None:
            # Update minimum angle for this rep
            if self.min_angle_in_rep is None or self.smoothed_angle < self.min_angle_in_rep:
                self.min_angle_in_rep = self.smoothed_angle
            
            # Assess depth quality
            if self.good_depth_min <= self.smoothed_angle <= self.good_depth_max:
                self.current_depth_quality = SquatDepthQuality.GOOD
            elif self.smoothed_angle > self.good_depth_max:
                self.current_depth_quality = SquatDepthQuality.SHALLOW
            elif self.smoothed_angle < self.good_depth_min:
                self.current_depth_quality = SquatDepthQuality.TOO_DEEP
    
    def _check_rep_completion(self) -> bool:
        """
        Check if a repetition has been completed.
        
        Returns:
            bool: True if a rep was just completed
        """
        rep_completed = False
        
        # Rep completion: BOTTOM -> ASCENDING -> STANDING
        if (self.previous_state == SquatState.ASCENDING and 
            self.current_state == SquatState.STANDING and
            self.min_angle_in_rep is not None):
            
            # Valid rep completed
            self.rep_count += 1
            self.last_rep_time = time.time()
            rep_completed = True
            
            # Store rep metrics
            self.rep_angles.append(self.min_angle_in_rep)
            if self.best_depth_angle is None or self.min_angle_in_rep < self.best_depth_angle:
                self.best_depth_angle = self.min_angle_in_rep
            
            # Reset rep tracking
            self.min_angle_in_rep = None
            self.rep_start_time = None
            
            # Trigger callback if set
            if self.on_rep_completed:
                self.on_rep_completed(self.person_id, self.rep_count, self.rep_angles[-1])
        
        # Track rep start time
        elif (self.previous_state == SquatState.STANDING and 
              self.current_state == SquatState.DESCENDING and
              self.rep_start_time is None):
            self.rep_start_time = time.time()
        
        return rep_completed
    
    def _update_performance_metrics(self):
        """Update performance metrics and form feedback."""
        self.form_feedback.clear()
        
        # Calculate average rep time
        if len(self.rep_angles) > 1 and self.last_rep_time:
            # Estimate based on recent reps (simplified)
            self.average_rep_time = self.total_session_time / len(self.rep_angles)
        
        # Provide form feedback
        if self.current_state == SquatState.BOTTOM:
            if self.current_depth_quality == SquatDepthQuality.SHALLOW:
                self.form_feedback.append("Go deeper")
            elif self.current_depth_quality == SquatDepthQuality.TOO_DEEP:
                self.form_feedback.append("Not too deep")
            elif self.current_depth_quality == SquatDepthQuality.GOOD:
                self.form_feedback.append("Good depth!")
        
        # Check for form issues based on angle trends
        if len(self.knee_angles) >= self.smoothing_window:
            angles = list(self.knee_angles)
            angle_variation = max(angles) - min(angles)
            if angle_variation > 20:  # High variation might indicate instability
                self.form_feedback.append("Keep steady")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for this tracker.
        
        Returns:
            dict: Complete statistics and metrics
        """
        return {
            'person_id': self.person_id,
            'rep_count': self.rep_count,
            'current_state': self.current_state.value,
            'current_angle': self.smoothed_angle,
            'depth_quality': self.current_depth_quality.value,
            'best_depth_angle': self.best_depth_angle,
            'average_rep_time': self.average_rep_time,
            'rep_angles': self.rep_angles.copy(),
            'form_feedback': self.form_feedback.copy(),
            'last_rep_time': self.last_rep_time,
            'state_history': list(self.state_history)
        }
    
    def reset(self):
        """Reset tracker state for a new session."""
        self.current_state = SquatState.UNKNOWN
        self.previous_state = SquatState.UNKNOWN
        self.state_frame_count = 0
        self.state_history.clear()
        self.knee_angles.clear()
        self.smoothed_angle = None
        self.min_angle_in_rep = None
        self.rep_count = 0
        self.last_rep_time = None
        self.rep_start_time = None
        self.current_depth_quality = SquatDepthQuality.UNKNOWN
        self.form_feedback.clear()
        self.total_session_time = 0
        self.average_rep_time = 0
        self.best_depth_angle = None
        self.rep_angles.clear()


class MultiPersonSquatTracker:
    """
    Manager for multiple individual squat trackers.
    
    Handles tracking multiple people simultaneously and provides
    aggregate statistics and coordination between trackers.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize multi-person tracker.
        
        Args:
            config (dict, optional): Configuration parameters
        """
        self.config = config or {}
        self.trackers: Dict[int, SquatTracker] = {}
        self.session_start_time = time.time()
        
        # Global callbacks
        self.on_rep_completed = None
        self.on_new_person = None
    
    def get_or_create_tracker(self, person_id: int) -> SquatTracker:
        """
        Get existing tracker or create new one for person.
        
        Args:
            person_id (int): Person identifier
            
        Returns:
            SquatTracker: Tracker instance for the person
        """
        if person_id not in self.trackers:
            tracker = SquatTracker(person_id, self.config)
            
            # Set up callbacks
            def on_rep_callback(pid, rep_count, angle):
                if self.on_rep_completed:
                    self.on_rep_completed(pid, rep_count, angle)
            
            tracker.on_rep_completed = on_rep_callback
            self.trackers[person_id] = tracker
            
            # Trigger new person callback
            if self.on_new_person:
                self.on_new_person(person_id)
        
        return self.trackers[person_id]
    
    def update_person(self, person_id: int, pose_landmarks: Dict[str, Tuple[int, int]]) -> Dict[str, Any]:
        """
        Update tracker for a specific person.
        
        Args:
            person_id (int): Person identifier
            pose_landmarks (dict): Dictionary of landmark coordinates
            
        Returns:
            dict: Updated tracking state for the person
        """
        tracker = self.get_or_create_tracker(person_id)
        
        # Extract required landmarks
        left_hip = pose_landmarks.get('LEFT_HIP')
        left_knee = pose_landmarks.get('LEFT_KNEE')
        left_ankle = pose_landmarks.get('LEFT_ANKLE')
        right_hip = pose_landmarks.get('RIGHT_HIP')
        right_knee = pose_landmarks.get('RIGHT_KNEE')
        right_ankle = pose_landmarks.get('RIGHT_ANKLE')
        
        return tracker.update(left_hip, left_knee, left_ankle, 
                            right_hip, right_knee, right_ankle)
    
    def get_aggregate_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all trackers.
        
        Returns:
            dict: Aggregate statistics
        """
        total_reps = sum(tracker.rep_count for tracker in self.trackers.values())
        active_people = len(self.trackers)
        session_duration = time.time() - self.session_start_time
        
        # Calculate average metrics
        avg_reps_per_person = total_reps / active_people if active_people > 0 else 0
        
        # Find best performer
        best_performer = None
        best_rep_count = 0
        for person_id, tracker in self.trackers.items():
            if tracker.rep_count > best_rep_count:
                best_rep_count = tracker.rep_count
                best_performer = person_id
        
        return {
            'total_reps': total_reps,
            'active_people': active_people,
            'session_duration': session_duration,
            'avg_reps_per_person': avg_reps_per_person,
            'best_performer': best_performer,
            'best_rep_count': best_rep_count,
            'trackers': {pid: tracker.get_statistics() for pid, tracker in self.trackers.items()}
        }
    
    def reset_session(self):
        """Reset all trackers for a new session."""
        for tracker in self.trackers.values():
            tracker.reset()
        self.session_start_time = time.time()
    
    def remove_inactive_trackers(self, inactive_threshold: float = 30.0):
        """
        Remove trackers for people who haven't been seen recently.
        
        Args:
            inactive_threshold (float): Seconds of inactivity before removal
        """
        current_time = time.time()
        inactive_ids = []
        
        for person_id, tracker in self.trackers.items():
            if tracker.last_rep_time and (current_time - tracker.last_rep_time) > inactive_threshold:
                inactive_ids.append(person_id)
        
        for person_id in inactive_ids:
            del self.trackers[person_id]