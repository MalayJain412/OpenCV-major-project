"""
Person detection module for multi-person pose tracking.

This module provides person detection capabilities using OpenCV DNN
or other detection backends to enable robust multi-person tracking.
"""

import cv2
import numpy as np
import math
from typing import List, Tuple, Optional, Dict, Any


class PersonDetection:
    """Represents a detected person with bounding box and confidence."""
    
    def __init__(self, bbox: Tuple[int, int, int, int], confidence: float, class_id: int = 1):
        """
        Initialize person detection.
        
        Args:
            bbox (tuple): Bounding box (x, y, width, height)
            confidence (float): Detection confidence score
            class_id (int): Class ID (typically 1 for person in COCO)
        """
        self.bbox = bbox
        self.confidence = confidence
        self.class_id = class_id
        self.center = self._calculate_center()
    
    def _calculate_center(self) -> Tuple[int, int]:
        """Calculate center point of bounding box."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)
    
    def get_expanded_bbox(self, expansion_factor: float = 0.1) -> Tuple[int, int, int, int]:
        """
        Get expanded bounding box for better pose detection.
        
        Args:
            expansion_factor (float): Factor to expand bbox by
            
        Returns:
            tuple: Expanded bounding box (x, y, width, height)
        """
        x, y, w, h = self.bbox
        expand_w = int(w * expansion_factor)
        expand_h = int(h * expansion_factor)
        
        new_x = max(0, x - expand_w)
        new_y = max(0, y - expand_h)
        new_w = w + 2 * expand_w
        new_h = h + 2 * expand_h
        
        return (new_x, new_y, new_w, new_h)


class PersonDetector:
    """
    Base class for person detection backends.
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialize person detector.
        
        Args:
            confidence_threshold (float): Minimum confidence for valid detections
        """
        self.confidence_threshold = confidence_threshold
    
    def detect(self, frame: np.ndarray) -> List[PersonDetection]:
        """
        Detect persons in frame.
        
        Args:
            frame (numpy.ndarray): Input frame in BGR format
            
        Returns:
            list: List of PersonDetection objects
        """
        raise NotImplementedError("Subclasses must implement detect method")


class OpenCVDNNPersonDetector(PersonDetector):
    """
    Person detector using OpenCV DNN backend.
    
    Supports various models like MobileNet-SSD, YOLOv3/v4/v5, etc.
    """
    
    def __init__(self, model_path: str, config_path: Optional[str] = None,
                 input_size: Tuple[int, int] = (416, 416),
                 confidence_threshold: float = 0.5,
                 nms_threshold: float = 0.4,
                 person_class_id: int = 0):
        """
        Initialize OpenCV DNN person detector.
        
        Args:
            model_path (str): Path to model weights file
            config_path (str, optional): Path to model config file
            input_size (tuple): Model input size (width, height)
            confidence_threshold (float): Minimum confidence threshold
            nms_threshold (float): Non-maximum suppression threshold
            person_class_id (int): Class ID for person (0 for YOLO, 15 for MobileNet-SSD COCO)
        """
        super().__init__(confidence_threshold)
        
        self.input_size = input_size
        self.nms_threshold = nms_threshold
        self.person_class_id = person_class_id
        
        # Load the network
        try:
            if config_path:
                self.net = cv2.dnn.readNet(model_path, config_path)
            else:
                self.net = cv2.dnn.readNet(model_path)
            
            # Set backend and target
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            # Get output layer names
            self.output_layers = self.net.getUnconnectedOutLayersNames()
            
            self.is_loaded = True
            
        except Exception as e:
            print(f"Failed to load person detection model: {e}")
            self.is_loaded = False
    
    def detect(self, frame: np.ndarray) -> List[PersonDetection]:
        """
        Detect persons using OpenCV DNN.
        
        Args:
            frame (numpy.ndarray): Input frame in BGR format
            
        Returns:
            list: List of PersonDetection objects
        """
        if not self.is_loaded:
            return []
        
        height, width = frame.shape[:2]
        
        # Create blob from image
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, self.input_size, 
                                   swapRB=True, crop=False)
        
        # Set input to network
        self.net.setInput(blob)
        
        # Run forward pass
        outputs = self.net.forward(self.output_layers)
        
        # Process outputs
        detections = self._process_outputs(outputs, width, height)
        
        return detections
    
    def _process_outputs(self, outputs: List[np.ndarray], 
                        frame_width: int, frame_height: int) -> List[PersonDetection]:
        """
        Process network outputs to extract person detections.
        
        Args:
            outputs (list): Network output arrays
            frame_width (int): Original frame width
            frame_height (int): Original frame height
            
        Returns:
            list: List of PersonDetection objects
        """
        boxes = []
        confidences = []
        class_ids = []
        
        for output in outputs:
            for detection in output:
                # Extract detection information
                if len(detection) >= 6:  # YOLO format
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if class_id == self.person_class_id and confidence > self.confidence_threshold:
                        # Extract bounding box
                        center_x = int(detection[0] * frame_width)
                        center_y = int(detection[1] * frame_height)
                        width = int(detection[2] * frame_width)
                        height = int(detection[3] * frame_height)
                        
                        # Convert to top-left corner format
                        x = int(center_x - width / 2)
                        y = int(center_y - height / 2)
                        
                        boxes.append([x, y, width, height])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
                
                elif len(detection) == 7:  # SSD format
                    confidence = detection[2]
                    class_id = int(detection[1])
                    
                    if class_id == self.person_class_id and confidence > self.confidence_threshold:
                        # Extract bounding box
                        x1 = int(detection[3] * frame_width)
                        y1 = int(detection[4] * frame_height)
                        x2 = int(detection[5] * frame_width)
                        y2 = int(detection[6] * frame_height)
                        
                        x = x1
                        y = y1
                        width = x2 - x1
                        height = y2 - y1
                        
                        boxes.append([x, y, width, height])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
        
        # Apply non-maximum suppression
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, confidences, 
                                     self.confidence_threshold, self.nms_threshold)
            
            detections = []
            if len(indices) > 0:
                for i in indices.flatten():
                    x, y, w, h = boxes[i]
                    # Ensure bounding box is within frame bounds
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, frame_width - x)
                    h = min(h, frame_height - y)
                    
                    if w > 0 and h > 0:
                        detection = PersonDetection((x, y, w, h), confidences[i], class_ids[i])
                        detections.append(detection)
            
            return detections
        
        return []


class SimplePersonTracker:
    """
    Simple person tracker using centroid tracking for ID assignment.
    """
    
    def __init__(self, max_distance: float = 100.0, max_frames_missing: int = 30):
        """
        Initialize person tracker.
        
        Args:
            max_distance (float): Maximum distance for centroid matching
            max_frames_missing (int): Maximum frames a person can be missing before removal
        """
        self.max_distance = max_distance
        self.max_frames_missing = max_frames_missing
        
        self.tracked_persons: Dict[int, Dict[str, Any]] = {}
        self.next_person_id = 0
        self.frame_count = 0
    
    def update(self, detections: List[PersonDetection]) -> Dict[int, PersonDetection]:
        """
        Update tracker with new detections and assign person IDs.
        
        Args:
            detections (list): List of PersonDetection objects
            
        Returns:
            dict: Mapping of person_id to PersonDetection
        """
        self.frame_count += 1
        current_centroids = [det.center for det in detections]
        
        # If no existing tracks, start new ones
        if not self.tracked_persons:
            person_assignments = {}
            for i, detection in enumerate(detections):
                self.tracked_persons[self.next_person_id] = {
                    'centroid': detection.center,
                    'last_seen': self.frame_count,
                    'detection': detection
                }
                person_assignments[self.next_person_id] = detection
                self.next_person_id += 1
            return person_assignments
        
        # Match current detections to existing tracks
        assignments = self._match_detections_to_tracks(detections)
        
        # Update existing tracks and create new ones
        person_assignments = {}
        used_detection_indices = set()
        
        # Update matched tracks
        for person_id, detection_idx in assignments.items():
            if detection_idx is not None:
                detection = detections[detection_idx]
                self.tracked_persons[person_id].update({
                    'centroid': detection.center,
                    'last_seen': self.frame_count,
                    'detection': detection
                })
                person_assignments[person_id] = detection
                used_detection_indices.add(detection_idx)
        
        # Create new tracks for unmatched detections
        for i, detection in enumerate(detections):
            if i not in used_detection_indices:
                self.tracked_persons[self.next_person_id] = {
                    'centroid': detection.center,
                    'last_seen': self.frame_count,
                    'detection': detection
                }
                person_assignments[self.next_person_id] = detection
                self.next_person_id += 1
        
        # Remove stale tracks
        self._remove_stale_tracks()
        
        return person_assignments
    
    def _match_detections_to_tracks(self, detections: List[PersonDetection]) -> Dict[int, Optional[int]]:
        """
        Match current detections to existing tracks using centroid distance.
        
        Args:
            detections (list): Current detections
            
        Returns:
            dict: Mapping of person_id to detection_index (or None if no match)
        """
        if not detections or not self.tracked_persons:
            return {}
        
        # Calculate distance matrix
        track_ids = list(self.tracked_persons.keys())
        detection_centers = [det.center for det in detections]
        track_centers = [self.tracked_persons[pid]['centroid'] for pid in track_ids]
        
        # Simple greedy assignment
        assignments = {pid: None for pid in track_ids}
        used_detections = set()
        
        for track_idx, track_id in enumerate(track_ids):
            track_center = track_centers[track_idx]
            best_detection_idx = None
            best_distance = float('inf')
            
            for det_idx, det_center in enumerate(detection_centers):
                if det_idx in used_detections:
                    continue
                
                distance = math.hypot(track_center[0] - det_center[0], 
                                    track_center[1] - det_center[1])
                
                if distance < best_distance and distance <= self.max_distance:
                    best_distance = distance
                    best_detection_idx = det_idx
            
            if best_detection_idx is not None:
                assignments[track_id] = best_detection_idx
                used_detections.add(best_detection_idx)
        
        return assignments
    
    def _remove_stale_tracks(self):
        """Remove tracks that haven't been seen for too long."""
        current_frame = self.frame_count
        stale_ids = []
        
        for person_id, track_info in self.tracked_persons.items():
            frames_missing = current_frame - track_info['last_seen']
            if frames_missing > self.max_frames_missing:
                stale_ids.append(person_id)
        
        for person_id in stale_ids:
            del self.tracked_persons[person_id]
    
    def get_active_person_count(self) -> int:
        """Get number of currently tracked persons."""
        return len(self.tracked_persons)
    
    def reset(self):
        """Reset tracker state."""
        self.tracked_persons.clear()
        self.next_person_id = 0
        self.frame_count = 0


class FallbackSinglePersonDetector(PersonDetector):
    """
    Fallback detector that treats the entire frame as containing one person.
    
    Used when no actual person detection model is available.
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """Initialize fallback detector."""
        super().__init__(confidence_threshold)
    
    def detect(self, frame: np.ndarray) -> List[PersonDetection]:
        """
        Return single detection covering entire frame.
        
        Args:
            frame (numpy.ndarray): Input frame
            
        Returns:
            list: Single PersonDetection covering the frame
        """
        height, width = frame.shape[:2]
        
        # Create detection for entire frame
        bbox = (0, 0, width, height)
        detection = PersonDetection(bbox, 1.0, 1)
        
        return [detection]