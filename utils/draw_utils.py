"""
Drawing utilities for pose estimation visualization.

This module provides functions for drawing overlays, text, FPS counters,
and other visual elements on video frames.
"""

import cv2
import numpy as np


class DrawingUtils:
    """Utility class for drawing overlays and text on frames."""
    
    # Color constants (BGR format)
    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    BLUE = (255, 0, 0)
    YELLOW = (0, 255, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    ORANGE = (0, 165, 255)
    PURPLE = (255, 0, 255)
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (192, 192, 192)
    
    @staticmethod
    def draw_text(frame, text, position=(10, 30), font_scale=0.7, color=(0, 255, 0), 
                  thickness=2, background=False, background_color=(0, 0, 0)):
        """
        Draw text on frame with optional background.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            text (str): Text to draw
            position (tuple): (x, y) position for text
            font_scale (float): Font scale factor
            color (tuple): Text color in BGR
            thickness (int): Text thickness
            background (bool): Whether to draw background rectangle
            background_color (tuple): Background color in BGR
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if background:
            # Get text size for background rectangle
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            
            # Draw background rectangle
            top_left = (position[0] - 5, position[1] - text_height - 5)
            bottom_right = (position[0] + text_width + 5, position[1] + baseline + 5)
            cv2.rectangle(frame, top_left, bottom_right, background_color, -1)
        
        # Draw text
        cv2.putText(frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)
    
    @staticmethod
    def draw_fps(frame, fps, position=None):
        """
        Draw FPS counter on frame.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            fps (float): Current FPS value
            position (tuple, optional): Position to draw FPS. Defaults to top-left.
        """
        if position is None:
            position = (10, 30)
        
        fps_text = f"FPS: {fps:.1f}"
        DrawingUtils.draw_text(frame, fps_text, position, color=DrawingUtils.YELLOW, 
                              background=True, background_color=(0, 0, 0))
    
    @staticmethod
    def draw_person_info(frame, person_id, reps, state, angle=None, position=(10, 60)):
        """
        Draw person information overlay.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            person_id (int): Person ID
            reps (int): Current rep count
            state (str): Current exercise state
            angle (float, optional): Current joint angle
            position (tuple): Starting position for text
        """
        x, y = position
        line_height = 25
        
        # Person ID and reps
        info_text = f"Person {person_id} | Reps: {reps}"
        DrawingUtils.draw_text(frame, info_text, (x, y), color=DrawingUtils.WHITE,
                              background=True)
        
        # Current state
        state_color = DrawingUtils.GREEN if state == "up" else DrawingUtils.ORANGE
        state_text = f"State: {state.upper()}"
        DrawingUtils.draw_text(frame, state_text, (x, y + line_height), 
                              color=state_color, background=True)
        
        # Joint angle if available
        if angle is not None:
            angle_text = f"Knee Angle: {angle:.1f}°"
            DrawingUtils.draw_text(frame, angle_text, (x, y + 2 * line_height), 
                                  color=DrawingUtils.BLUE, background=True)
    
    @staticmethod
    def draw_bounding_box(frame, bbox, person_id, color=None, thickness=2):
        """
        Draw bounding box around detected person.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            bbox (tuple): Bounding box (x, y, width, height)
            person_id (int): Person ID for labeling
            color (tuple, optional): Box color. Defaults to green.
            thickness (int): Box line thickness
        """
        if color is None:
            color = DrawingUtils.GREEN
        
        x, y, w, h = bbox
        
        # Draw rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        
        # Draw person ID label
        label = f"Person {person_id}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        
        # Background for label
        cv2.rectangle(frame, (x, y - label_size[1] - 10), 
                     (x + label_size[0] + 10, y), color, -1)
        
        # Label text
        cv2.putText(frame, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, DrawingUtils.WHITE, 2, cv2.LINE_AA)
    
    @staticmethod
    def draw_squat_feedback(frame, depth_quality, position=(10, 150)):
        """
        Draw squat depth feedback.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            depth_quality (str): Quality assessment ("good", "shallow", "deep")
            position (tuple): Position to draw feedback
        """
        feedback_colors = {
            "good": DrawingUtils.GREEN,
            "shallow": DrawingUtils.ORANGE,
            "deep": DrawingUtils.BLUE,
            "unknown": DrawingUtils.GRAY
        }
        
        color = feedback_colors.get(depth_quality, DrawingUtils.GRAY)
        feedback_text = f"Depth: {depth_quality.upper()}"
        
        DrawingUtils.draw_text(frame, feedback_text, position, color=color,
                              font_scale=0.8, background=True)
    
    @staticmethod
    def draw_angle_arc(frame, center, radius, start_angle, end_angle, color=None, thickness=2):
        """
        Draw an arc to visualize joint angles.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            center (tuple): Arc center (x, y)
            radius (int): Arc radius
            start_angle (float): Start angle in degrees
            end_angle (float): End angle in degrees
            color (tuple, optional): Arc color
            thickness (int): Arc thickness
        """
        if color is None:
            color = DrawingUtils.YELLOW
        
        # Convert to OpenCV angle format (start from positive x-axis, clockwise)
        start_cv = int(-start_angle)
        end_cv = int(-end_angle)
        
        # Draw arc
        cv2.ellipse(frame, center, (radius, radius), 0, start_cv, end_cv, color, thickness)
    
    @staticmethod
    def draw_pose_skeleton(frame, keypoints, connections=None, point_color=None, line_color=None):
        """
        Draw pose skeleton using keypoints.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            keypoints (dict): Dictionary of landmark names to (x, y, visibility) tuples
            connections (list, optional): List of connection pairs
            point_color (tuple, optional): Color for keypoints
            line_color (tuple, optional): Color for connections
        """
        if point_color is None:
            point_color = DrawingUtils.RED
        if line_color is None:
            line_color = DrawingUtils.GREEN
        
        # Default connections for basic skeleton
        if connections is None:
            connections = [
                ('LEFT_SHOULDER', 'RIGHT_SHOULDER'),
                ('LEFT_SHOULDER', 'LEFT_ELBOW'),
                ('LEFT_ELBOW', 'LEFT_WRIST'),
                ('RIGHT_SHOULDER', 'RIGHT_ELBOW'),
                ('RIGHT_ELBOW', 'RIGHT_WRIST'),
                ('LEFT_SHOULDER', 'LEFT_HIP'),
                ('RIGHT_SHOULDER', 'RIGHT_HIP'),
                ('LEFT_HIP', 'RIGHT_HIP'),
                ('LEFT_HIP', 'LEFT_KNEE'),
                ('LEFT_KNEE', 'LEFT_ANKLE'),
                ('RIGHT_HIP', 'RIGHT_KNEE'),
                ('RIGHT_KNEE', 'RIGHT_ANKLE')
            ]
        
        # Draw connections
        for connection in connections:
            point1_name, point2_name = connection
            if point1_name in keypoints and point2_name in keypoints:
                pt1 = keypoints[point1_name][:2]  # (x, y)
                pt2 = keypoints[point2_name][:2]  # (x, y)
                cv2.line(frame, pt1, pt2, line_color, 2)
        
        # Draw keypoints
        for name, (x, y, visibility) in keypoints.items():
            if visibility > 0.5:  # Only draw visible points
                cv2.circle(frame, (x, y), 4, point_color, -1)
    
    @staticmethod
    def draw_session_info(frame, session_start_time, total_reps, log_file):
        """
        Draw session information.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            session_start_time (str): Session start timestamp
            total_reps (int): Total reps across all people
            log_file (str): Log file name
        """
        height, width = frame.shape[:2]
        
        # Draw session info at bottom of frame
        y_start = height - 80
        line_height = 20
        
        session_info = [
            f"Session: {session_start_time}",
            f"Total Reps: {total_reps}",
            f"Log: {log_file}"
        ]
        
        for i, info in enumerate(session_info):
            y_pos = y_start + i * line_height
            DrawingUtils.draw_text(frame, info, (10, y_pos), font_scale=0.5,
                                  color=DrawingUtils.LIGHT_GRAY, background=True)