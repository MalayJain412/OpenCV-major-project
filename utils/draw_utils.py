"""
Drawing utilities for pose estimation visualization.

This module provides functions for drawing overlays, text, FPS counters,
and other visual elements on video frames.
"""

import cv2
import numpy as np


class DrawingUtils:
    """Utility class for drawing overlays and text on frames."""
    # Master switch to enable/disable drawing text directly on frames.
    # Set to False to keep camera preview text-free and move textual UI to the web UI.
    FRAME_TEXT_ENABLED = False
    
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
        # If frame text is globally disabled, do nothing.
        if not DrawingUtils.FRAME_TEXT_ENABLED:
            return

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
        
        # Draw person ID label (only if frame text is enabled)
        label = f"Person {person_id}"
        if DrawingUtils.FRAME_TEXT_ENABLED:
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]

            # Background for label
            cv2.rectangle(frame, (x, y - label_size[1] - 10),
                         (x + label_size[0] + 10, y), color, -1)

            # Label text using draw_text (respects FRAME_TEXT_ENABLED)
            DrawingUtils.draw_text(frame, label, (x + 5, y - 5), font_scale=0.6, color=DrawingUtils.WHITE, thickness=2)
    
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

    @staticmethod
    def draw_transparent_panel(frame, top_left, bottom_right, color=(0, 0, 0), alpha=0.6):
        """Draw a semi-transparent rectangular panel on the frame.

        Args:
            frame (numpy.ndarray): Frame to draw on
            top_left (tuple): (x, y) top-left corner
            bottom_right (tuple): (x, y) bottom-right corner
            color (tuple): BGR color for panel
            alpha (float): Opacity (0.0 - 1.0)
        """
        overlay = frame.copy()
        cv2.rectangle(overlay, top_left, bottom_right, color, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    @staticmethod
    def draw_mode_header(frame, mode_text, color=(0, 0, 0), text_color=(255, 255, 255)):
        """Draw a prominent mode header at the top of the frame.

        Args:
            frame (numpy.ndarray): Frame to draw on
            mode_text (str): Header text (e.g., "FITNESS MODE")
            color (tuple): Background color for header (BGR)
            text_color (tuple): Text color (BGR)
        """
        height, width = frame.shape[:2]
        header_h = 48
        DrawingUtils.draw_transparent_panel(frame, (0, 0), (width, header_h), color=color, alpha=0.55)
        DrawingUtils.draw_text(frame, mode_text, (12, 34), font_scale=1.0, color=text_color, thickness=2)

    @staticmethod
    def draw_fitness_ui(frame, stats: dict, person_info: dict = None):
        """Draw fitness-specific UI overlays: session panel, reps, and small info.

        Args:
            frame (numpy.ndarray): Frame to draw on
            stats (dict): Stats dictionary (fps, session_reps, etc.)
            person_info (dict, optional): Per-person info {id, reps, state, angle}
        """
        # Header
        DrawingUtils.draw_mode_header(frame, "FITNESS MODE", color=(0, 128, 0), text_color=DrawingUtils.WHITE)

        # Session panel (top-right)
        height, width = frame.shape[:2]
        panel_w = 260
        panel_h = 100
        top_left = (width - panel_w - 10, 10)
        bottom_right = (width - 10, 10 + panel_h)
        DrawingUtils.draw_transparent_panel(frame, top_left, bottom_right, color=(0, 0, 0), alpha=0.45)

        # Populate session panel
        x = top_left[0] + 10
        y = top_left[1] + 24
        DrawingUtils.draw_text(frame, f"FPS: {stats.get('fps', 0):.0f}", (x, y), font_scale=0.6, color=DrawingUtils.LIGHT_GRAY, background=False)
        DrawingUtils.draw_text(frame, f"Reps: {stats.get('session_reps', 0)}", (x, y + 22), font_scale=0.7, color=DrawingUtils.WHITE, background=False)
        DrawingUtils.draw_text(frame, f"People: {stats.get('active_people', stats.get('detected_persons', 0))}", (x, y + 44), font_scale=0.6, color=DrawingUtils.LIGHT_GRAY, background=False)

        # Per-person info (left side)
        if person_info:
            DrawingUtils.draw_transparent_panel(frame, (10, 60), (260, 160), color=(0, 0, 0), alpha=0.45)
            pid = person_info.get('id', 0)
            DrawingUtils.draw_person_info(frame, pid, person_info.get('reps', 0), person_info.get('state', 'unknown'), angle=person_info.get('angle', None), position=(20, 80))

    @staticmethod
    def draw_surveillance_ui(frame, stats: dict, alerts: list = None, zones: list = None):
        """Draw surveillance-specific UI overlays: alert panel, zone info, and counters.

        Args:
            frame (numpy.ndarray): Frame to draw on
            stats (dict): Stats dictionary
            alerts (list, optional): Recent alert dicts
            zones (list, optional): Configured zones
        """
        # Header
        DrawingUtils.draw_mode_header(frame, "SURVEILLANCE MODE", color=(0, 0, 128), text_color=DrawingUtils.WHITE)

        # Alerts panel (top-left)
        height, width = frame.shape[:2]
        panel_w = 320
        panel_h = 140
        top_left = (10, 10)
        bottom_right = (10 + panel_w, 10 + panel_h)
        DrawingUtils.draw_transparent_panel(frame, top_left, bottom_right, color=(0, 0, 0), alpha=0.5)

        # Populate alerts panel
        x = top_left[0] + 10
        y = top_left[1] + 26
        DrawingUtils.draw_text(frame, f"Active People: {stats.get('detected_persons', 0)}", (x, y), font_scale=0.6, color=DrawingUtils.WHITE, background=False)
        DrawingUtils.draw_text(frame, f"Active Alerts: {stats.get('alerts_count', 0)}", (x, y + 22), font_scale=0.7, color=DrawingUtils.ORANGE, background=False)
        DrawingUtils.draw_text(frame, f"Zones: {len(zones) if zones else 0}", (x, y + 44), font_scale=0.6, color=DrawingUtils.LIGHT_GRAY, background=False)

        # Recent alert messages (bottom)
        if alerts:
            max_show = 3
            start_y = top_left[1] + panel_h + 8
            DrawingUtils.draw_transparent_panel(frame, (10, start_y), (width - 10, start_y + 80), color=(0, 0, 0), alpha=0.35)
            for i, alert in enumerate(alerts[:max_show]):
                text = f"{alert.get('timestamp', '')} - {alert.get('alert_type', '')}: {alert.get('description','') }"
                DrawingUtils.draw_text(frame, text, (20, start_y + 20 + i * 20), font_scale=0.5, color=DrawingUtils.WHITE, background=False)

    @staticmethod
    def draw_recent_alerts_bar(frame, alerts: list):
        """Draw a wide semi-transparent bar in the middle-top to show recent alerts clearly.

        Args:
            frame (numpy.ndarray): Frame to draw on
            alerts (list): List of alert dicts with 'timestamp' and 'description' or 'alert_type'
        """
        if not alerts:
            return

        height, width = frame.shape[:2]
        bar_h = 80
        top = 60
        left = int(width * 0.05)
        right = int(width * 0.95)

        # Draw translucent background
        DrawingUtils.draw_transparent_panel(frame, (left, top), (right, top + bar_h), color=(0, 0, 0), alpha=0.45)

        # Compose a single long line (truncate if too long)
        texts = []
        for a in alerts[:4]:
            t = a.get('timestamp', '')
            at = a.get('alert_type', '')
            desc = a.get('description', '')
            texts.append(f"{t} - {at}: {desc}")

        display_text = '   |   '.join(texts)
        # Truncate to reasonable length
        max_chars = 220
        if len(display_text) > max_chars:
            display_text = display_text[:max_chars-3] + '...'

        DrawingUtils.draw_text(frame, display_text, (left + 12, top + 40), font_scale=0.6, color=DrawingUtils.WHITE, thickness=2, background=False)

    @staticmethod
    def draw_large_zone_label(frame, text, position=('bottom_right'), width_frac=0.32, height=80, bg_color=(0,0,255)):
        """Draw a large colored banner (e.g., red) at bottom-right for zone labels or large alerts.

        Args:
            frame (numpy.ndarray): Frame to draw on
            text (str): Label text
            position (str): 'bottom_right' or 'bottom_left'
            width_frac (float): Fraction of frame width for banner width
            height (int): Banner height in pixels
            bg_color (tuple): BGR color for banner
        """
        h, w = frame.shape[:2]
        banner_w = int(w * width_frac)
        banner_h = height

        if position == 'bottom_right':
            tl = (w - banner_w - 10, h - banner_h - 10)
            br = (w - 10, h - 10)
            text_pos = (tl[0] + int(banner_w*0.12), tl[1] + int(banner_h*0.62))
        else:
            tl = (10, h - banner_h - 10)
            br = (10 + banner_w, h - 10)
            text_pos = (tl[0] + int(banner_w*0.12), tl[1] + int(banner_h*0.62))

        # Solid background for high visibility
        cv2.rectangle(frame, tl, br, bg_color, -1)

        # Draw label text large and bold
        DrawingUtils.draw_text(frame, text, text_pos, font_scale=1.1, color=DrawingUtils.WHITE, thickness=3)

    @staticmethod
    def draw_small_stats_box(frame, stats: dict):
        """Draw a compact stats box (red) in the top-left showing counts with strong colors.

        Args:
            frame (numpy.ndarray): Frame to draw on
            stats (dict): Stats dictionary
        """
        height, width = frame.shape[:2]
        wbox = 220
        hbox = 90
        tl = (10, 10)
        br = (10 + wbox, 10 + hbox)

        # Red panel
        DrawingUtils.draw_transparent_panel(frame, tl, br, color=(0,0,255), alpha=0.85)

        x = tl[0] + 12
        y = tl[1] + 24
        # Yellow text for counts
        DrawingUtils.draw_text(frame, f"Active People: {stats.get('detected_persons', 0)}", (x, y), font_scale=0.6, color=DrawingUtils.YELLOW, thickness=2, background=False)
        DrawingUtils.draw_text(frame, f"Total Detected: {stats.get('detected_persons', 0)}", (x, y+22), font_scale=0.5, color=DrawingUtils.WHITE, background=False)
        DrawingUtils.draw_text(frame, f"Active Alerts: {stats.get('alerts_count', 0)}", (x, y+44), font_scale=0.6, color=DrawingUtils.ORANGE, background=False)
