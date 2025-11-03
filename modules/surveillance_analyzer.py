"""
Surveillance Analyzer Module

Provides real-time surveillance capabilities including movement tracking,
zone detection, anomaly detection, and alert generation.

Author: VisionTrack Project
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
import time
from dataclasses import dataclass
from enum import Enum
import json

from utils.draw_utils import DrawingUtils
from utils.alert_system import AlertSystem, AlertConfig, create_default_alert_system


class AlertType(Enum):
    """Types of surveillance alerts."""
    PERSON_DETECTED = "person_detected"
    RESTRICTED_ZONE_ENTRY = "restricted_zone_entry"
    RAPID_MOVEMENT = "rapid_movement"
    FALL_DETECTED = "fall_detected"
    LOITERING = "loitering"
    OBJECT_LEFT = "object_left"
    UNUSUAL_POSTURE = "unusual_posture"


@dataclass
class Alert:
    """Surveillance alert data."""
    alert_type: AlertType
    timestamp: float
    person_id: int
    location: Tuple[int, int]
    confidence: float
    description: str
    resolved: bool = False


@dataclass
class PersonTrack:
    """Person tracking data for surveillance."""
    person_id: int
    positions: List[Tuple[int, int, float]]  # (x, y, timestamp)
    first_seen: float
    last_seen: float
    speed: float
    direction: float
    in_restricted_zones: Set[int]
    pose_history: List[Dict]
    alert_count: int


class RestrictedZone:
    """Defines a restricted zone in the surveillance area."""
    
    def __init__(self, zone_id: int, name: str, points: List[Tuple[int, int]], 
                 alert_type: AlertType = AlertType.RESTRICTED_ZONE_ENTRY):
        self.zone_id = zone_id
        self.name = name
        self.points = np.array(points, dtype=np.int32)
        self.alert_type = alert_type
        self.enabled = True
    
    def contains_point(self, point: Tuple[int, int]) -> bool:
        """Check if a point is inside the zone."""
        if not self.enabled:
            return False
        
        return cv2.pointPolygonTest(self.points, point, False) >= 0
    
    def draw(self, frame: np.ndarray, color: Tuple[int, int, int] = (0, 0, 255)):
        """Draw the zone on the frame."""
        if self.enabled:
            cv2.polylines(frame, [self.points], True, color, 2)
            cv2.fillPoly(frame, [self.points], color + (50,))  # Semi-transparent fill
            
            # Draw zone label
            center_x = int(np.mean(self.points[:, 0]))
            center_y = int(np.mean(self.points[:, 1]))
            cv2.putText(frame, self.name, (center_x - 30, center_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


class MovementAnalyzer:
    """Analyzes movement patterns for anomaly detection."""
    
    def __init__(self):
        self.speed_threshold_high = 300  # pixels per second
        self.speed_threshold_low = 10    # pixels per second for loitering
        self.loitering_time = 30         # seconds
        self.fall_angle_threshold = 45   # degrees from vertical
    
    def analyze_speed(self, person_track: PersonTrack) -> Optional[Alert]:
        """Analyze person's movement speed."""
        if len(person_track.positions) < 2:
            return None
        
        current_pos = person_track.positions[-1]
        prev_pos = person_track.positions[-2]
        
        # Calculate speed
        distance = np.sqrt((current_pos[0] - prev_pos[0])**2 + 
                          (current_pos[1] - prev_pos[1])**2)
        time_diff = current_pos[2] - prev_pos[2]
        
        if time_diff > 0:
            speed = distance / time_diff
            person_track.speed = speed
            
            if speed > self.speed_threshold_high:
                return Alert(
                    alert_type=AlertType.RAPID_MOVEMENT,
                    timestamp=current_pos[2],
                    person_id=person_track.person_id,
                    location=(current_pos[0], current_pos[1]),
                    confidence=0.8,
                    description=f"Rapid movement detected: {speed:.1f} px/s"
                )
        
        return None
    
    def analyze_loitering(self, person_track: PersonTrack) -> Optional[Alert]:
        """Detect loitering behavior."""
        if len(person_track.positions) < 10:  # Need enough history
            return None
        
        # Check if person has been in roughly the same area
        recent_positions = person_track.positions[-10:]
        center_x = np.mean([pos[0] for pos in recent_positions])
        center_y = np.mean([pos[1] for pos in recent_positions])
        
        # Calculate variance in position
        variance = np.mean([(pos[0] - center_x)**2 + (pos[1] - center_y)**2 
                           for pos in recent_positions])
        
        # Check if person has been stationary for too long
        time_in_area = recent_positions[-1][2] - recent_positions[0][2]
        
        if variance < 1000 and time_in_area > self.loitering_time:  # Low movement, long time
            return Alert(
                alert_type=AlertType.LOITERING,
                timestamp=recent_positions[-1][2],
                person_id=person_track.person_id,
                location=(int(center_x), int(center_y)),
                confidence=0.7,
                description=f"Loitering detected for {time_in_area:.1f} seconds"
            )
        
        return None
    
    def analyze_fall(self, pose_landmarks) -> Optional[Dict]:
        """Analyze pose for fall detection."""
        try:
            # Get key landmarks
            head = pose_landmarks[0]     # Nose
            shoulder = pose_landmarks[11] # Left shoulder
            hip = pose_landmarks[23]     # Left hip
            
            # Calculate body angle from vertical
            body_vector = np.array([hip.x - shoulder.x, hip.y - shoulder.y])
            vertical_vector = np.array([0, 1])
            
            # Calculate angle
            angle = np.arccos(np.dot(body_vector, vertical_vector) / 
                             (np.linalg.norm(body_vector) * np.linalg.norm(vertical_vector)))
            angle_degrees = np.degrees(angle)
            
            if angle_degrees > self.fall_angle_threshold:
                return {
                    'fall_detected': True,
                    'angle': angle_degrees,
                    'confidence': min(0.9, (angle_degrees - self.fall_angle_threshold) / 45)
                }
        
        except Exception:
            pass
        
        return None


class SurveillanceAnalyzer:
    """Main surveillance analysis system."""
    
    def __init__(self, alert_system: Optional[AlertSystem] = None):
        self.drawing_utils = DrawingUtils()
        self.movement_analyzer = MovementAnalyzer()
        
        # Initialize alert system
        self.alert_system = alert_system or create_default_alert_system()
        
        # Tracking data
        self.person_tracks: Dict[int, PersonTrack] = {}
        self.next_person_id = 1
        
        # Surveillance configuration
        self.restricted_zones: Dict[int, RestrictedZone] = {}
        self.alerts: List[Alert] = []
        self.max_alerts = 100  # Keep only recent alerts
        
        # Settings
        self.person_detection_enabled = True
        self.zone_detection_enabled = True
        self.movement_analysis_enabled = True
        self.fall_detection_enabled = True
        
        # Stats
        self.total_people_detected = 0
        self.active_alerts = 0
        
        # Initialize with zones from configuration file
        self.load_zones_from_config()
    
    def load_zones_from_config(self, config_path: str = "utils/zone_config.json"):
        """Load surveillance zones from configuration file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            for zone_data in config.get('zones', []):
                if zone_data.get('enabled', True):
                    alert_type = AlertType(zone_data.get('alert_type', 'restricted_zone_entry'))
                    self.add_restricted_zone(
                        zone_id=zone_data['zone_id'],
                        name=zone_data['name'],
                        points=[(point[0], point[1]) for point in zone_data['points']],
                        alert_type=alert_type
                    )
            
            print(f"[INFO] Loaded {len(self.restricted_zones)} surveillance zones from config")
        except Exception as e:
            print(f"[WARN] Could not load zone config: {e}")
            self.add_default_zones()
    
    def add_default_zones(self):
        """Add default restricted zones for demonstration."""
        # Example: Top-left corner as restricted zone
        zone1_points = [(50, 50), (200, 50), (200, 150), (50, 150)]
        self.add_restricted_zone(1, "Restricted Area 1", zone1_points)
    
    def add_restricted_zone(self, zone_id: int, name: str, 
                           points: List[Tuple[int, int]], 
                           alert_type: AlertType = AlertType.RESTRICTED_ZONE_ENTRY):
        """Add a restricted zone."""
        self.restricted_zones[zone_id] = RestrictedZone(zone_id, name, points, alert_type)
    
    def remove_restricted_zone(self, zone_id: int):
        """Remove a restricted zone."""
        if zone_id in self.restricted_zones:
            del self.restricted_zones[zone_id]
    
    def process_frame(self, frame: np.ndarray, pose_results) -> np.ndarray:
        """Process frame for surveillance analysis."""
        processed_frame = frame.copy()
        current_time = time.time()
        
        # Process detected people
        if pose_results.pose_landmarks:
            self.update_person_tracking(pose_results.pose_landmarks, current_time, frame.shape)
        
        # Update active person count
        active_people = len([track for track in self.person_tracks.values() 
                           if current_time - track.last_seen < 2.0])
        
        # Draw surveillance overlay
        self.draw_surveillance_overlay(processed_frame, current_time)
        
        # Update stats
        self.active_alerts = len([alert for alert in self.alerts if not alert.resolved])
        
        return processed_frame
    
    def update_person_tracking(self, pose_landmarks, current_time: float, frame_shape: tuple):
        """Update person tracking data."""
        detected_people = []
        frame_height, frame_width = frame_shape[:2]
        
        # Handle MediaPipe pose results structure
        # pose_landmarks is either None or a single NormalizedLandmarkList
        if pose_landmarks is not None:
            # Convert single pose landmarks to list format for consistency
            landmarks_list = [pose_landmarks]
        else:
            landmarks_list = []
        
        for i, landmarks in enumerate(landmarks_list):
            # Get person position (use hip midpoint)
            try:
                left_hip = landmarks.landmark[23]
                right_hip = landmarks.landmark[24]
                person_x = int((left_hip.x + right_hip.x) * frame_width / 2)
                person_y = int((left_hip.y + right_hip.y) * frame_height / 2)
                
                detected_people.append({
                    'landmarks': landmarks,
                    'position': (person_x, person_y),
                    'pose_data': self.extract_pose_features(landmarks)
                })
            except:
                continue
        
        # Update or create person tracks
        self.match_people_to_tracks(detected_people, current_time)
        
        # Analyze each person
        for person_id, track in self.person_tracks.items():
            if current_time - track.last_seen < 1.0:  # Only analyze recently seen people
                self.analyze_person(track, current_time)
    
    def match_people_to_tracks(self, detected_people: List[Dict], current_time: float):
        """Match detected people to existing tracks."""
        # Simple distance-based matching
        for person_data in detected_people:
            position = person_data['position']
            best_match_id = None
            best_distance = float('inf')
            
            # Find closest existing track
            for person_id, track in self.person_tracks.items():
                if len(track.positions) > 0:
                    last_pos = track.positions[-1]
                    distance = np.sqrt((position[0] - last_pos[0])**2 + 
                                     (position[1] - last_pos[1])**2)
                    
                    if distance < best_distance and distance < 100:  # Max matching distance
                        best_distance = distance
                        best_match_id = person_id
            
            # Update existing track or create new one
            if best_match_id:
                track = self.person_tracks[best_match_id]
                track.positions.append((position[0], position[1], current_time))
                track.last_seen = current_time
                track.pose_history.append(person_data['pose_data'])
                
                # Keep only recent history
                if len(track.positions) > 50:
                    track.positions = track.positions[-50:]
                if len(track.pose_history) > 20:
                    track.pose_history = track.pose_history[-20:]
            else:
                # Create new track
                new_id = self.next_person_id
                self.next_person_id += 1
                self.total_people_detected += 1
                
                self.person_tracks[new_id] = PersonTrack(
                    person_id=new_id,
                    positions=[(position[0], position[1], current_time)],
                    first_seen=current_time,
                    last_seen=current_time,
                    speed=0.0,
                    direction=0.0,
                    in_restricted_zones=set(),
                    pose_history=[person_data['pose_data']],
                    alert_count=0
                )
    
    def extract_pose_features(self, landmarks) -> Dict:
        """Extract relevant pose features for analysis."""
        try:
            head = landmarks.landmark[0]
            left_shoulder = landmarks.landmark[11]
            right_shoulder = landmarks.landmark[12]
            left_hip = landmarks.landmark[23]
            right_hip = landmarks.landmark[24]
            
            return {
                'head_position': (head.x, head.y),
                'shoulder_width': abs(left_shoulder.x - right_shoulder.x),
                'body_height': abs(head.y - (left_hip.y + right_hip.y) / 2),
                'posture_angle': self.calculate_posture_angle(landmarks)
            }
        except:
            return {}
    
    def calculate_posture_angle(self, landmarks) -> float:
        """Calculate body posture angle from vertical."""
        try:
            shoulder = landmarks.landmark[11]
            hip = landmarks.landmark[23]
            
            angle = np.arctan2(hip.x - shoulder.x, hip.y - shoulder.y)
            return np.degrees(angle)
        except:
            return 0.0
    
    def analyze_person(self, track: PersonTrack, current_time: float):
        """Analyze a person for various surveillance alerts."""
        
        # Movement analysis
        if self.movement_analysis_enabled:
            speed_alert = self.movement_analyzer.analyze_speed(track)
            if speed_alert:
                self.add_alert(speed_alert)
            
            loitering_alert = self.movement_analyzer.analyze_loitering(track)
            if loitering_alert:
                self.add_alert(loitering_alert)
        
        # Zone detection
        if self.zone_detection_enabled and len(track.positions) > 0:
            current_pos = track.positions[-1]
            for zone_id, zone in self.restricted_zones.items():
                is_in_zone = zone.contains_point((current_pos[0], current_pos[1]))
                
                if is_in_zone and zone_id not in track.in_restricted_zones:
                    # Person entered restricted zone
                    track.in_restricted_zones.add(zone_id)
                    alert = Alert(
                        alert_type=AlertType.RESTRICTED_ZONE_ENTRY,
                        timestamp=current_time,
                        person_id=track.person_id,
                        location=(current_pos[0], current_pos[1]),
                        confidence=0.9,
                        description=f"Person entered {zone.name}"
                    )
                    self.add_alert(alert)
                elif not is_in_zone and zone_id in track.in_restricted_zones:
                    # Person left restricted zone
                    track.in_restricted_zones.remove(zone_id)
        
        # Fall detection
        if self.fall_detection_enabled and len(track.pose_history) > 0:
            latest_pose = track.pose_history[-1]
            if 'posture_angle' in latest_pose:
                angle = abs(latest_pose['posture_angle'])
                if angle > 45:  # Significant deviation from upright
                    alert = Alert(
                        alert_type=AlertType.FALL_DETECTED,
                        timestamp=current_time,
                        person_id=track.person_id,
                        location=track.positions[-1][:2],
                        confidence=min(0.9, angle / 90),
                        description=f"Possible fall detected (angle: {angle:.1f}°)"
                    )
                    self.add_alert(alert)
    
    def add_alert(self, alert: Alert):
        """Add a new alert with comprehensive logging and notification."""
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Update person alert count
        if alert.person_id in self.person_tracks:
            self.person_tracks[alert.person_id].alert_count += 1
        
        # Trigger comprehensive alert through alert system
        self.alert_system.trigger_alert(
            alert_type=alert.alert_type.value,
            person_id=alert.person_id,
            coords=alert.location,
            confidence=alert.confidence,
            description=alert.description,
            session_id=f"surveillance_{int(time.time())}"
        )
    
    def draw_surveillance_overlay(self, frame: np.ndarray, current_time: float):
        """Draw surveillance overlay on frame."""
        
        # Draw restricted zones
        for zone in self.restricted_zones.values():
            zone.draw(frame, (0, 0, 255))
        
        # Draw person tracks
        for track in self.person_tracks.values():
            if current_time - track.last_seen < 2.0:  # Only show recent tracks
                self.draw_person_track(frame, track)
        
        # Draw recent alerts
        self.draw_alerts(frame, current_time)
        
        # Draw surveillance info panel
        self.draw_info_panel(frame, current_time)
    
    def draw_person_track(self, frame: np.ndarray, track: PersonTrack):
        """Draw person tracking visualization."""
        if len(track.positions) == 0:
            return
        
        # Draw trail
        for i in range(1, len(track.positions)):
            prev_pos = track.positions[i-1]
            curr_pos = track.positions[i]
            cv2.line(frame, (prev_pos[0], prev_pos[1]), (curr_pos[0], curr_pos[1]), 
                    (255, 255, 0), 2)
        
        # Draw current position
        current_pos = track.positions[-1]
        cv2.circle(frame, (current_pos[0], current_pos[1]), 10, (0, 255, 0), -1)
        
        # Draw person info
        info_text = f"ID:{track.person_id} Speed:{track.speed:.1f}"
        cv2.putText(frame, info_text, (current_pos[0] - 30, current_pos[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Alert indicator if person has alerts
        if track.alert_count > 0:
            cv2.circle(frame, (current_pos[0], current_pos[1]), 15, (0, 0, 255), 3)
    
    def draw_alerts(self, frame: np.ndarray, current_time: float):
        """Draw recent alerts."""
        recent_alerts = [alert for alert in self.alerts 
                        if current_time - alert.timestamp < 10.0 and not alert.resolved]
        
        y_offset = 400
        for alert in recent_alerts[-5:]:  # Show last 5 alerts
            alert_text = f"ALERT: {alert.description}"
            cv2.putText(frame, alert_text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
    
    def draw_info_panel(self, frame: np.ndarray, current_time: float):
        """Draw surveillance information panel."""
        active_people = len([track for track in self.person_tracks.values() 
                           if current_time - track.last_seen < 2.0])
        
        info_y = 60
        cv2.putText(frame, f"Active People: {active_people}", (10, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Total Detected: {self.total_people_detected}", (10, info_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Active Alerts: {self.active_alerts}", (10, info_y + 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.putText(frame, f"Zones: {len(self.restricted_zones)}", (10, info_y + 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    def get_surveillance_summary(self) -> Dict:
        """Get surveillance session summary."""
        current_time = time.time()
        active_people = len([track for track in self.person_tracks.values() 
                           if current_time - track.last_seen < 2.0])
        
        return {
            'active_people': active_people,
            'total_people_detected': self.total_people_detected,
            'active_alerts': self.active_alerts,
            'total_alerts': len(self.alerts),
            'restricted_zones': len(self.restricted_zones),
            'detection_modes': {
                'person_detection': self.person_detection_enabled,
                'zone_detection': self.zone_detection_enabled,
                'movement_analysis': self.movement_analysis_enabled,
                'fall_detection': self.fall_detection_enabled
            }
        }
    
    def reset_session(self):
        """Reset surveillance session data."""
        self.person_tracks.clear()
        self.alerts.clear()
        self.total_people_detected = 0
        self.active_alerts = 0
        self.next_person_id = 1