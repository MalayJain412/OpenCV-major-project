"""
Test script for the enhanced VisionTrack Surveillance System

This script demonstrates the core surveillance functionality including:
- Person detection and tracking
- Restricted zone monitoring
- Alert system with logging and notifications
- Real-time visualization

Usage:
    python test_surveillance.py

Author: VisionTrack Project
"""

import cv2
import sys
import os
import time
from pathlib import Path

# Add project modules to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'modules'))
sys.path.append(str(project_root / 'utils'))

from modules.pose_detector import PoseDetector
from modules.surveillance_analyzer import SurveillanceAnalyzer
from utils.alert_system import AlertSystem, AlertConfig


def main():
    """Main surveillance test function."""
    print("=== VisionTrack Surveillance System Test ===")
    print("Press 'q' to quit, 'r' to reset alerts, 's' to show statistics")
    
    # Initialize components
    try:
        pose_detector = PoseDetector()
        print("[INFO] Pose detector initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize pose detector: {e}")
        return
    
    # Create custom alert system with enhanced configuration
    alert_config = AlertConfig(
        log_path="logs/surveillance_test_alerts.csv",
        enable_sound=True,
        enable_email=False,  # Set to True and configure email for testing
        alert_cooldown_seconds=3
    )
    
    alert_system = AlertSystem(alert_config=alert_config)
    surveillance_analyzer = SurveillanceAnalyzer(alert_system=alert_system)
    
    print(f"[INFO] Surveillance analyzer initialized with {len(surveillance_analyzer.restricted_zones)} zones")
    
    # Initialize camera
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("[ERROR] Could not open camera")
        return
    
    # Set camera properties for optimal performance
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    print("[INFO] Camera initialized successfully")
    print("[INFO] Starting surveillance monitoring...")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[ERROR] Failed to read from camera")
                break
            
            frame_count += 1
            
            # Process frame for pose detection
            pose_results = pose_detector.process_frame(frame)
            
            # Process frame for surveillance analysis
            surveillance_frame = surveillance_analyzer.process_frame(frame, pose_results)
            
            # Add performance info
            current_time = time.time()
            fps = frame_count / (current_time - start_time)
            cv2.putText(surveillance_frame, f"FPS: {fps:.1f}", (500, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add instruction text
            cv2.putText(surveillance_frame, "Press 'q' to quit, 'r' to reset, 's' for stats", 
                       (10, surveillance_frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Display the frame
            cv2.imshow("VisionTrack Surveillance", surveillance_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # Reset surveillance session
                surveillance_analyzer.reset_session()
                alert_system.clear_alert_history()
                print("[INFO] Surveillance session reset")
            elif key == ord('s'):
                # Show statistics
                stats = alert_system.get_alert_statistics()
                surveillance_stats = surveillance_analyzer.get_surveillance_summary()
                print("\n=== Surveillance Statistics ===")
                print(f"Alert Statistics: {stats}")
                print(f"Surveillance Stats: {surveillance_stats}")
                print("=" * 30)
    
    except KeyboardInterrupt:
        print("\n[INFO] Surveillance monitoring stopped by user")
    
    finally:
        # Cleanup
        camera.release()
        cv2.destroyAllWindows()
        
        # Show final statistics
        final_stats = alert_system.get_alert_statistics()
        print(f"\n=== Final Session Statistics ===")
        print(f"Total alerts: {final_stats['total_alerts']}")
        print(f"Session duration: {final_stats['session_duration_minutes']:.1f} minutes")
        if final_stats['total_alerts'] > 0:
            print(f"Most common alert: {final_stats['most_common_alert']}")
            print(f"Alerts per minute: {final_stats['alerts_per_minute']:.2f}")
        
        # Export alerts if any were generated
        if final_stats['total_alerts'] > 0:
            export_path = f"logs/surveillance_session_{int(time.time())}.json"
            if alert_system.export_alerts_to_json(export_path):
                print(f"Alert data exported to: {export_path}")
        
        print("[INFO] Surveillance test completed")


def test_alert_system():
    """Test the alert system independently."""
    print("\n=== Testing Alert System ===")
    
    # Create test alert system
    alert_system = AlertSystem()
    
    # Test different alert types
    test_alerts = [
        ("person_detected", (320, 240), "New person detected"),
        ("restricted_zone_entry", (150, 100), "Person entered restricted area"),
        ("rapid_movement", (400, 300), "Rapid movement detected"),
        ("fall_detected", (350, 400), "Possible fall detected"),
        ("loitering", (200, 200), "Loitering behavior detected")
    ]
    
    for alert_type, coords, description in test_alerts:
        alert_system.trigger_alert(
            alert_type=alert_type,
            person_id=1,
            coords=coords,
            confidence=0.85,
            description=description
        )
        time.sleep(1)  # Brief pause between alerts
    
    # Show results
    stats = alert_system.get_alert_statistics()
    recent_alerts = alert_system.get_recent_alerts()
    
    print(f"Generated {len(recent_alerts)} test alerts")
    print(f"Statistics: {stats}")


if __name__ == "__main__":
    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test-alerts":
        test_alert_system()
    else:
        main()