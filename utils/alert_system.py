"""
Alert System Module

Provides comprehensive alert handling for VisionTrack surveillance system,
including logging, sound alerts, email notifications, and real-time notifications.

Author: VisionTrack Project
"""

import os
import csv
import json
import smtplib
import winsound
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AlertConfig:
    """Configuration for alert system."""
    log_path: str = "logs/alerts_log.csv"
    enable_sound: bool = True
    enable_email: bool = False
    enable_file_logging: bool = True
    max_alerts_in_memory: int = 100
    alert_cooldown_seconds: int = 5  # Prevent spam alerts


@dataclass
class EmailConfig:
    """Email notification configuration."""
    sender: str = ""
    password: str = ""
    receiver: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True


class AlertSystem:
    """
    Comprehensive alert system for surveillance monitoring.
    
    Features:
    - CSV logging with detailed alert information
    - Audio alerts with different sounds for different alert types
    - Email notifications (optional)
    - Real-time callback support for web interface
    - Alert cooldown to prevent spam
    - Alert history and statistics
    """
    
    def __init__(self, 
                 alert_config: Optional[AlertConfig] = None,
                 email_config: Optional[EmailConfig] = None):
        """
        Initialize the alert system.
        
        Args:
            alert_config: Alert system configuration
            email_config: Email notification configuration
        """
        self.config = alert_config or AlertConfig()
        self.email_config = email_config
        
        # Alert storage
        self.alert_history: List[Dict] = []
        self.last_alert_times: Dict[str, float] = {}
        
        # Callback for real-time notifications (e.g., websocket)
        self.real_time_callback: Optional[Callable] = None
        
        # Alert statistics
        self.stats = {
            'total_alerts': 0,
            'alerts_by_type': {},
            'session_start': time.time()
        }
        
        # Sound mappings for different alert types
        self.sound_mappings = {
            'person_detected': {'freq': 800, 'duration': 200},
            'restricted_zone_entry': {'freq': 1000, 'duration': 500},
            'rapid_movement': {'freq': 1200, 'duration': 300},
            'fall_detected': {'freq': 1500, 'duration': 1000},
            'loitering': {'freq': 600, 'duration': 300},
            'default': {'freq': 1000, 'duration': 300}
        }
        
        # Initialize logging
        self._initialize_logging()
    
    def _initialize_logging(self):
        """Initialize CSV logging file."""
        if not self.config.enable_file_logging:
            return
        
        # Create logs directory if it doesn't exist
        log_dir = Path(self.config.log_path).parent
        log_dir.mkdir(exist_ok=True)
        
        # Create log file with headers if it doesn't exist
        if not os.path.exists(self.config.log_path):
            with open(self.config.log_path, "w", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Alert Type", "Person ID", "Coordinates", 
                    "Confidence", "Description", "Session ID", "Resolved"
                ])
    
    def trigger_alert(self, 
                     alert_type: str, 
                     person_id: Optional[int] = None,
                     coords: Optional[tuple] = None, 
                     confidence: float = 0.8,
                     description: str = "",
                     session_id: str = "default") -> bool:
        """
        Trigger a surveillance alert with full logging and notification.
        
        Args:
            alert_type: Type of alert (e.g., 'zone_intrusion', 'fall_detected')
            person_id: ID of the person involved (if applicable)
            coords: Coordinates where alert occurred (x, y)
            confidence: Confidence level of the detection (0.0-1.0)
            description: Human-readable description of the alert
            session_id: Session identifier for grouping alerts
            
        Returns:
            bool: True if alert was processed, False if cooled down
        """
        # Check cooldown to prevent spam
        if self._is_alert_cooled_down(alert_type, person_id):
            return False
        
        timestamp = datetime.now()
        coords_str = f"{coords[0]},{coords[1]}" if coords else "N/A"
        
        # Create alert data
        alert_data = {
            'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'alert_type': alert_type,
            'person_id': person_id or 'N/A',
            'coordinates': coords_str,
            'confidence': confidence,
            'description': description or f"{alert_type.replace('_', ' ').title()} detected",
            'session_id': session_id,
            'resolved': False
        }
        
        # Add to memory
        self.alert_history.append(alert_data)
        if len(self.alert_history) > self.config.max_alerts_in_memory:
            self.alert_history = self.alert_history[-self.config.max_alerts_in_memory:]
        
        # Update statistics
        self.stats['total_alerts'] += 1
        if alert_type not in self.stats['alerts_by_type']:
            self.stats['alerts_by_type'][alert_type] = 0
        self.stats['alerts_by_type'][alert_type] += 1
        
        # Log to CSV
        if self.config.enable_file_logging:
            self._log_to_csv(alert_data)
        
        # Play sound alert
        if self.config.enable_sound:
            self._play_sound_alert(alert_type)
        
        # Send email notification
        if self.config.enable_email and self.email_config:
            self._send_email_alert(alert_data)
        
        # Real-time callback (for web interface)
        if self.real_time_callback:
            try:
                self.real_time_callback(alert_data)
            except Exception as e:
                print(f"[WARN] Real-time callback failed: {e}")
        
        # Console output
        print(f"[ALERT] {timestamp.strftime('%H:%M:%S')} - {alert_data['description']} "
              f"@ {coords_str} (Confidence: {confidence:.2f})")
        
        # Update cooldown
        cooldown_key = f"{alert_type}_{person_id}" if person_id else alert_type
        self.last_alert_times[cooldown_key] = time.time()
        
        return True
    
    def _is_alert_cooled_down(self, alert_type: str, person_id: Optional[int]) -> bool:
        """Check if alert is in cooldown period."""
        cooldown_key = f"{alert_type}_{person_id}" if person_id else alert_type
        last_time = self.last_alert_times.get(cooldown_key, 0)
        return (time.time() - last_time) < self.config.alert_cooldown_seconds
    
    def _log_to_csv(self, alert_data: Dict):
        """Log alert to CSV file."""
        try:
            with open(self.config.log_path, "a", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    alert_data['timestamp'],
                    alert_data['alert_type'],
                    alert_data['person_id'],
                    alert_data['coordinates'],
                    alert_data['confidence'],
                    alert_data['description'],
                    alert_data['session_id'],
                    alert_data['resolved']
                ])
        except Exception as e:
            print(f"[ERROR] CSV logging failed: {e}")
    
    def _play_sound_alert(self, alert_type: str):
        """Play audio alert based on alert type."""
        try:
            sound_config = self.sound_mappings.get(alert_type, self.sound_mappings['default'])
            winsound.Beep(sound_config['freq'], sound_config['duration'])
        except Exception as e:
            print(f"[WARN] Sound alert failed: {e}")
    
    def _send_email_alert(self, alert_data: Dict):
        """Send email notification for alert."""
        if not self.email_config or not self.email_config.sender:
            return
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.email_config.sender
            msg['To'] = self.email_config.receiver
            msg['Subject'] = f"VisionTrack Alert: {alert_data['alert_type'].replace('_', ' ').title()}"
            
            # Email body
            body = f"""
VisionTrack Surveillance Alert

Alert Type: {alert_data['alert_type'].replace('_', ' ').title()}
Time: {alert_data['timestamp']}
Person ID: {alert_data['person_id']}
Location: {alert_data['coordinates']}
Confidence: {alert_data['confidence']:.2f}
Description: {alert_data['description']}
Session: {alert_data['session_id']}

This is an automated alert from your VisionTrack surveillance system.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect and send
            if self.email_config.use_tls:
                server = smtplib.SMTP(self.email_config.smtp_server, self.email_config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.email_config.smtp_server, self.email_config.smtp_port)
            
            server.login(self.email_config.sender, self.email_config.password)
            server.send_message(msg)
            server.quit()
            
            print("[INFO] Alert email sent successfully.")
        except Exception as e:
            print(f"[ERROR] Email alert failed: {e}")
    
    def set_real_time_callback(self, callback: Callable):
        """Set callback function for real-time alert notifications."""
        self.real_time_callback = callback
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts from memory."""
        return self.alert_history[-limit:] if self.alert_history else []
    
    def get_alerts_by_type(self, alert_type: str, limit: int = 10) -> List[Dict]:
        """Get alerts filtered by type."""
        filtered = [alert for alert in self.alert_history 
                   if alert['alert_type'] == alert_type]
        return filtered[-limit:] if filtered else []
    
    def get_unresolved_alerts(self) -> List[Dict]:
        """Get all unresolved alerts."""
        return [alert for alert in self.alert_history if not alert['resolved']]
    
    def resolve_alert(self, alert_index: int) -> bool:
        """Mark an alert as resolved."""
        if 0 <= alert_index < len(self.alert_history):
            self.alert_history[alert_index]['resolved'] = True
            return True
        return False
    
    def get_alert_statistics(self) -> Dict:
        """Get comprehensive alert statistics."""
        session_duration = time.time() - self.stats['session_start']
        unresolved_count = len(self.get_unresolved_alerts())
        
        return {
            'total_alerts': self.stats['total_alerts'],
            'unresolved_alerts': unresolved_count,
            'alerts_by_type': self.stats['alerts_by_type'].copy(),
            'session_duration_minutes': session_duration / 60,
            'alerts_per_minute': self.stats['total_alerts'] / (session_duration / 60) if session_duration > 0 else 0,
            'most_common_alert': max(self.stats['alerts_by_type'].items(), 
                                   key=lambda x: x[1], default=('none', 0))[0]
        }
    
    def clear_alert_history(self):
        """Clear alert history and reset statistics."""
        self.alert_history.clear()
        self.last_alert_times.clear()
        self.stats = {
            'total_alerts': 0,
            'alerts_by_type': {},
            'session_start': time.time()
        }
    
    def export_alerts_to_json(self, filepath: str) -> bool:
        """Export alert history to JSON file."""
        try:
            export_data = {
                'alerts': self.alert_history,
                'statistics': self.get_alert_statistics(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"[INFO] Alerts exported to {filepath}")
            return True
        except Exception as e:
            print(f"[ERROR] Export failed: {e}")
            return False


# Example usage and configuration helpers
def create_default_alert_system() -> AlertSystem:
    """Create alert system with default configuration."""
    config = AlertConfig(
        log_path="logs/surveillance_alerts.csv",
        enable_sound=True,
        enable_email=False,
        alert_cooldown_seconds=3
    )
    
    return AlertSystem(alert_config=config)


def create_email_enabled_alert_system(sender_email: str, sender_password: str, 
                                     receiver_email: str) -> AlertSystem:
    """Create alert system with email notifications enabled."""
    alert_config = AlertConfig(
        log_path="logs/surveillance_alerts.csv",
        enable_sound=True,
        enable_email=True,
        alert_cooldown_seconds=3
    )
    
    email_config = EmailConfig(
        sender=sender_email,
        password=sender_password,
        receiver=receiver_email
    )
    
    return AlertSystem(alert_config=alert_config, email_config=email_config)


if __name__ == "__main__":
    # Test the alert system
    alert_system = create_default_alert_system()
    
    # Test different alert types
    alert_system.trigger_alert("person_detected", person_id=1, coords=(320, 240), 
                              description="New person detected in surveillance area")
    
    alert_system.trigger_alert("restricted_zone_entry", person_id=1, coords=(150, 100), 
                              confidence=0.95, description="Person entered restricted zone")
    
    alert_system.trigger_alert("fall_detected", person_id=1, coords=(300, 350), 
                              confidence=0.87, description="Possible fall detected")
    
    # Show statistics
    stats = alert_system.get_alert_statistics()
    print(f"\nAlert Statistics: {stats}")
    
    # Show recent alerts
    recent = alert_system.get_recent_alerts(5)
    print(f"\nRecent Alerts: {len(recent)}")
    for alert in recent:
        print(f"  - {alert['timestamp']}: {alert['description']}")