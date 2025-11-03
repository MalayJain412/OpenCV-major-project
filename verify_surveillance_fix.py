"""
Quick verification test for the fixed surveillance system
Tests the integration between pose detection and surveillance analysis
"""

import cv2
import sys
import os
from pathlib import Path

# Add project modules to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'modules'))
sys.path.append(str(project_root / 'utils'))

from modules.pose_detector import PoseDetector
from modules.surveillance_analyzer import SurveillanceAnalyzer

def test_surveillance_integration():
    """Test surveillance system with camera input."""
    print("🔍 Testing Surveillance System Integration")
    print("=" * 50)
    
    try:
        # Initialize components
        pose_detector = PoseDetector()
        surveillance_analyzer = SurveillanceAnalyzer()
        print("✅ Components initialized successfully")
        
        # Test camera
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("❌ Camera not available - testing with synthetic frame")
            
            # Test with synthetic frame
            import numpy as np
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(test_frame, "TEST FRAME", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            
            # Process synthetic frame
            pose_results = pose_detector.process_frame(test_frame)
            surveillance_frame = surveillance_analyzer.process_frame(test_frame, pose_results)
            
            print("✅ Synthetic frame processing successful")
            print(f"   Input shape: {test_frame.shape}")
            print(f"   Output shape: {surveillance_frame.shape}")
            print(f"   Pose landmarks detected: {pose_results.pose_landmarks is not None}")
            
            return True
        
        # Test with real camera for a few frames
        print("📹 Testing with real camera (5 frames)...")
        frame_count = 0
        success_count = 0
        
        while frame_count < 5:
            ret, frame = camera.read()
            if not ret:
                print(f"❌ Failed to read frame {frame_count + 1}")
                break
            
            try:
                # Process frame
                pose_results = pose_detector.process_frame(frame)
                surveillance_frame = surveillance_analyzer.process_frame(frame, pose_results)
                
                success_count += 1
                person_detected = pose_results.pose_landmarks is not None
                print(f"   Frame {frame_count + 1}: ✅ Processed | Person: {'Yes' if person_detected else 'No'}")
                
            except Exception as e:
                print(f"   Frame {frame_count + 1}: ❌ Error - {e}")
            
            frame_count += 1
        
        camera.release()
        
        print(f"\n📊 Results: {success_count}/{frame_count} frames processed successfully")
        
        # Show surveillance statistics
        stats = surveillance_analyzer.get_surveillance_summary()
        print(f"\n📈 Surveillance Stats:")
        print(f"   Active people: {stats['active_people']}")
        print(f"   Total detected: {stats['total_people_detected']}")
        print(f"   Active alerts: {stats['active_alerts']}")
        print(f"   Zones configured: {stats['restricted_zones']}")
        
        # Show alert system statistics
        if hasattr(surveillance_analyzer, 'alert_system'):
            alert_stats = surveillance_analyzer.alert_system.get_alert_statistics()
            print(f"\n🚨 Alert System Stats:")
            print(f"   Total alerts: {alert_stats['total_alerts']}")
            print(f"   Session duration: {alert_stats['session_duration_minutes']:.1f} min")
        
        return success_count == frame_count
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_surveillance_integration()
    print(f"\n{'🎉 All tests passed!' if success else '⚠️  Some tests failed'}")
    print("The surveillance system is ready for use!" if success else "Please check the error messages above.")