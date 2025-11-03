"""
Angle calculation utilities for pose analysis.

This module provides functions to calculate angles between body joints
for exercise form analysis, particularly for squat detection.
"""

import numpy as np
import math


def calculate_angle(point_a, point_b, point_c):
    """
    Calculate the angle ABC formed by three points.
    
    Args:
        point_a (tuple): First point (x, y)
        point_b (tuple): Vertex point (x, y) 
        point_c (tuple): Third point (x, y)
        
    Returns:
        float: Angle in degrees, or None if calculation fails
    """
    try:
        # Convert to numpy arrays
        a = np.array(point_a, dtype=np.float32)
        b = np.array(point_b, dtype=np.float32)
        c = np.array(point_c, dtype=np.float32)
        
        # Calculate vectors
        ba = a - b  # Vector from B to A
        bc = c - b  # Vector from B to C
        
        # Calculate magnitudes
        magnitude_ba = np.linalg.norm(ba)
        magnitude_bc = np.linalg.norm(bc)
        
        # Avoid division by zero
        if magnitude_ba == 0 or magnitude_bc == 0:
            return None
        
        # Calculate cosine of angle using dot product
        cos_angle = np.dot(ba, bc) / (magnitude_ba * magnitude_bc)
        
        # Clamp to valid range for arccos
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        # Calculate angle in radians then convert to degrees
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
        
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calculate_knee_angle(hip_point, knee_point, ankle_point):
    """
    Calculate knee angle for squat analysis.
    
    Args:
        hip_point (tuple): Hip coordinates (x, y)
        knee_point (tuple): Knee coordinates (x, y)
        ankle_point (tuple): Ankle coordinates (x, y)
        
    Returns:
        float: Knee angle in degrees, or None if calculation fails
    """
    return calculate_angle(hip_point, knee_point, ankle_point)


def calculate_hip_angle(shoulder_point, hip_point, knee_point):
    """
    Calculate hip angle for posture analysis.
    
    Args:
        shoulder_point (tuple): Shoulder coordinates (x, y)
        hip_point (tuple): Hip coordinates (x, y)
        knee_point (tuple): Knee coordinates (x, y)
        
    Returns:
        float: Hip angle in degrees, or None if calculation fails
    """
    return calculate_angle(shoulder_point, hip_point, knee_point)


def calculate_body_inclination(hip_point, shoulder_point):
    """
    Calculate body inclination angle from vertical.
    
    Args:
        hip_point (tuple): Hip coordinates (x, y)
        shoulder_point (tuple): Shoulder coordinates (x, y)
        
    Returns:
        float: Inclination angle in degrees from vertical, or None if calculation fails
    """
    try:
        # Vector from hip to shoulder
        dx = shoulder_point[0] - hip_point[0]
        dy = shoulder_point[1] - hip_point[1]  # Note: y increases downward in image coordinates
        
        # Calculate angle from vertical (negative y-axis)
        angle_rad = math.atan2(abs(dx), abs(dy))
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
        
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def average_angles(left_angle, right_angle):
    """
    Calculate average of left and right joint angles.
    
    Args:
        left_angle (float or None): Left side angle
        right_angle (float or None): Right side angle
        
    Returns:
        float or None: Average angle, or single valid angle, or None if both invalid
    """
    valid_angles = [angle for angle in [left_angle, right_angle] if angle is not None]
    
    if not valid_angles:
        return None
    
    return sum(valid_angles) / len(valid_angles)


def smooth_angle_sequence(angles, window_size=5):
    """
    Apply moving average smoothing to a sequence of angles.
    
    Args:
        angles (list): List of angle values (may contain None)
        window_size (int): Size of smoothing window
        
    Returns:
        list: Smoothed angles
    """
    if not angles:
        return []
    
    smoothed = []
    
    for i in range(len(angles)):
        # Get window around current position
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(angles), i + window_size // 2 + 1)
        
        # Extract valid angles in window
        window_angles = [angles[j] for j in range(start_idx, end_idx) if angles[j] is not None]
        
        if window_angles:
            smoothed.append(sum(window_angles) / len(window_angles))
        else:
            smoothed.append(None)
    
    return smoothed