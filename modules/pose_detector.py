"""
Pose Detection Module using MediaPipe

This module provides a wrapper around MediaPipe Pose for real-time human pose estimation.
Supports both single and multi-person pose detection with configurable parameters.
"""

import cv2
import mediapipe as mp
import numpy as np


class PoseDetector:
    """
    MediaPipe Pose detector wrapper for real-time pose estimation.
    """
    
    def __init__(self, 
                 model_complexity=1, 
                 min_detection_confidence=0.5, 
                 min_tracking_confidence=0.5,
                 static_image_mode=False):
        """
        Initialize the pose detector.
        
        Args:
            model_complexity (int): Complexity of the pose model (0, 1, or 2)
            min_detection_confidence (float): Minimum confidence for pose detection
            min_tracking_confidence (float): Minimum confidence for pose tracking
            static_image_mode (bool): Whether to treat input as static images
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
    
    def process_frame(self, frame_bgr):
        """
        Process a BGR frame and return pose landmarks.
        
        Args:
            frame_bgr (numpy.ndarray): Input frame in BGR format
            
        Returns:
            mediapipe.solutions.pose.Pose results object
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        
        # Process the frame
        results = self.pose.process(frame_rgb)
        
        return results
    
    def draw_landmarks(self, frame, landmarks, connections=None):
        """
        Draw pose landmarks on the frame.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            landmarks: MediaPipe pose landmarks
            connections: MediaPipe pose connections (optional)
        """
        if landmarks:
            self.mp_drawing.draw_landmarks(
                frame,
                landmarks,
                connections or self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
    
    def extract_keypoints(self, landmarks, frame_width, frame_height):
        """
        Extract normalized keypoints from MediaPipe landmarks.
        
        Args:
            landmarks: MediaPipe pose landmarks
            frame_width (int): Width of the frame
            frame_height (int): Height of the frame
            
        Returns:
            dict: Dictionary of landmark names to (x, y, visibility) tuples
        """
        if not landmarks:
            return {}
        
        keypoints = {}
        landmark_names = [
            'NOSE', 'LEFT_EYE_INNER', 'LEFT_EYE', 'LEFT_EYE_OUTER',
            'RIGHT_EYE_INNER', 'RIGHT_EYE', 'RIGHT_EYE_OUTER',
            'LEFT_EAR', 'RIGHT_EAR', 'MOUTH_LEFT', 'MOUTH_RIGHT',
            'LEFT_SHOULDER', 'RIGHT_SHOULDER', 'LEFT_ELBOW', 'RIGHT_ELBOW',
            'LEFT_WRIST', 'RIGHT_WRIST', 'LEFT_PINKY', 'RIGHT_PINKY',
            'LEFT_INDEX', 'RIGHT_INDEX', 'LEFT_THUMB', 'RIGHT_THUMB',
            'LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE',
            'LEFT_ANKLE', 'RIGHT_ANKLE', 'LEFT_HEEL', 'RIGHT_HEEL',
            'LEFT_FOOT_INDEX', 'RIGHT_FOOT_INDEX'
        ]
        
        for i, landmark in enumerate(landmarks.landmark):
            if i < len(landmark_names):
                keypoints[landmark_names[i]] = (
                    int(landmark.x * frame_width),
                    int(landmark.y * frame_height),
                    landmark.visibility
                )
        
        return keypoints
    
    def get_landmark_coords(self, landmarks, landmark_name, frame_width, frame_height):
        """
        Get pixel coordinates for a specific landmark.
        
        Args:
            landmarks: MediaPipe pose landmarks
            landmark_name (str): Name of the landmark
            frame_width (int): Width of the frame
            frame_height (int): Height of the frame
            
        Returns:
            tuple: (x, y) coordinates or None if landmark not found
        """
        if not landmarks:
            return None
        
        try:
            landmark_idx = getattr(self.mp_pose.PoseLandmark, landmark_name).value
            landmark = landmarks.landmark[landmark_idx]
            
            x = int(landmark.x * frame_width)
            y = int(landmark.y * frame_height)
            
            return (x, y)
        except (AttributeError, IndexError):
            return None
    
    def is_pose_visible(self, landmarks, visibility_threshold=0.5):
        """
        Check if the pose is sufficiently visible for analysis.
        
        Args:
            landmarks: MediaPipe pose landmarks
            visibility_threshold (float): Minimum visibility threshold
            
        Returns:
            bool: True if pose is visible enough for analysis
        """
        if not landmarks:
            return False
        
        # Check visibility of key landmarks for squat analysis
        key_landmarks = ['LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 
                        'LEFT_ANKLE', 'RIGHT_ANKLE']
        
        visible_count = 0
        for landmark_name in key_landmarks:
            try:
                landmark_idx = getattr(self.mp_pose.PoseLandmark, landmark_name).value
                visibility = landmarks.landmark[landmark_idx].visibility
                if visibility > visibility_threshold:
                    visible_count += 1
            except (AttributeError, IndexError):
                continue
        
        # Require at least 4 out of 6 key landmarks to be visible
        return visible_count >= 4
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'pose'):
            self.pose.close()