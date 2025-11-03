"""
Configuration Management System

Centralized configuration management for VisionTrack application
with support for different modes, camera settings, and user preferences.

Author: VisionTrack Project
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CameraConfig:
    """Camera configuration settings."""
    width: int = 640
    height: int = 480
    fps: int = 30
    device_id: int = 0
    auto_exposure: bool = True
    brightness: float = 0.5
    contrast: float = 0.5


@dataclass
class FitnessConfig:
    """Fitness mode configuration."""
    auto_exercise_detection: bool = True
    default_exercise: str = "squat"
    rep_counter_enabled: bool = True
    form_analysis_enabled: bool = True
    audio_feedback: bool = True
    calorie_tracking: bool = True
    
    # Exercise-specific thresholds
    squat_upright_threshold: float = 160.0
    squat_bottom_threshold: float = 100.0
    pushup_up_threshold: float = 160.0
    pushup_down_threshold: float = 90.0
    bicep_curl_up_threshold: float = 40.0
    bicep_curl_down_threshold: float = 160.0


@dataclass
class SurveillanceConfig:
    """Surveillance mode configuration."""
    person_tracking_enabled: bool = True
    zone_detection_enabled: bool = True
    movement_analysis_enabled: bool = True
    fall_detection_enabled: bool = True
    
    # Alert thresholds
    rapid_movement_threshold: float = 300.0  # pixels per second
    loitering_time_threshold: float = 30.0   # seconds
    fall_angle_threshold: float = 45.0       # degrees
    
    # Zone settings
    default_zones_enabled: bool = True
    alert_sound_enabled: bool = True
    alert_notifications: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""
    # General settings
    app_name: str = "VisionTrack"
    version: str = "1.0.0"
    default_mode: str = "fitness"
    
    # Performance settings
    max_fps: int = 30
    frame_skip: int = 1
    pose_model_complexity: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    
    # UI settings
    show_landmarks: bool = True
    show_fps: bool = True
    show_stats: bool = True
    overlay_opacity: float = 0.7
    
    # Data settings
    session_auto_save: bool = True
    data_retention_days: int = 30
    csv_export_enabled: bool = True
    
    # Web app settings
    web_host: str = "0.0.0.0"
    web_port: int = 5000
    web_debug: bool = False
    
    # Component configs
    camera: CameraConfig = None
    fitness: FitnessConfig = None
    surveillance: SurveillanceConfig = None
    
    def __post_init__(self):
        if self.camera is None:
            self.camera = CameraConfig()
        if self.fitness is None:
            self.fitness = FitnessConfig()
        if self.surveillance is None:
            self.surveillance = SurveillanceConfig()


class ConfigManager:
    """Configuration manager for VisionTrack application."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = AppConfig()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Update main config
                for key, value in config_data.items():
                    if key in ['camera', 'fitness', 'surveillance']:
                        # Handle nested configs
                        if key == 'camera':
                            self.config.camera = CameraConfig(**value)
                        elif key == 'fitness':
                            self.config.fitness = FitnessConfig(**value)
                        elif key == 'surveillance':
                            self.config.surveillance = SurveillanceConfig(**value)
                    else:
                        setattr(self.config, key, value)
                
                print(f"✅ Configuration loaded from {self.config_file}")
            
            except Exception as e:
                print(f"⚠️ Error loading config file: {e}")
                print("🔄 Using default configuration")
                self.save_config()  # Save default config
        else:
            print("ℹ️ Config file not found, creating default configuration")
            self.save_config()
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            config_dict = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"💾 Configuration saved to {self.config_file}")
            
        except Exception as e:
            print(f"❌ Error saving config file: {e}")
    
    def get_camera_config(self) -> CameraConfig:
        """Get camera configuration."""
        return self.config.camera
    
    def get_fitness_config(self) -> FitnessConfig:
        """Get fitness mode configuration."""
        return self.config.fitness
    
    def get_surveillance_config(self) -> SurveillanceConfig:
        """Get surveillance mode configuration."""
        return self.config.surveillance
    
    def get_app_config(self) -> AppConfig:
        """Get main app configuration."""
        return self.config
    
    def update_camera_config(self, **kwargs):
        """Update camera configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.camera, key):
                setattr(self.config.camera, key, value)
        self.save_config()
    
    def update_fitness_config(self, **kwargs):
        """Update fitness configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.fitness, key):
                setattr(self.config.fitness, key, value)
        self.save_config()
    
    def update_surveillance_config(self, **kwargs):
        """Update surveillance configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.surveillance, key):
                setattr(self.config.surveillance, key, value)
        self.save_config()
    
    def update_app_config(self, **kwargs):
        """Update main app configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key) and key not in ['camera', 'fitness', 'surveillance']:
                setattr(self.config, key, value)
        self.save_config()
    
    def get_mode_config(self, mode: str) -> Dict[str, Any]:
        """Get configuration for specific mode."""
        if mode == "fitness":
            return asdict(self.config.fitness)
        elif mode == "surveillance":
            return asdict(self.config.surveillance)
        elif mode == "camera":
            return asdict(self.config.camera)
        else:
            return {}
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = AppConfig()
        self.save_config()
        print("🔄 Configuration reset to defaults")
    
    def export_config(self, export_path: str):
        """Export configuration to specified path."""
        try:
            export_file = Path(export_path)
            config_dict = asdict(self.config)
            
            with open(export_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"📤 Configuration exported to {export_file}")
            
        except Exception as e:
            print(f"❌ Error exporting config: {e}")
    
    def import_config(self, import_path: str):
        """Import configuration from specified path."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Config file not found: {import_path}")
            
            with open(import_file, 'r') as f:
                config_data = json.load(f)
            
            # Validate and apply config
            self.config = AppConfig(**config_data)
            self.save_config()
            
            print(f"📥 Configuration imported from {import_file}")
            
        except Exception as e:
            print(f"❌ Error importing config: {e}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            'app_name': self.config.app_name,
            'version': self.config.version,
            'default_mode': self.config.default_mode,
            'camera': {
                'resolution': f"{self.config.camera.width}x{self.config.camera.height}",
                'fps': self.config.camera.fps,
                'device': self.config.camera.device_id
            },
            'fitness': {
                'auto_detection': self.config.fitness.auto_exercise_detection,
                'default_exercise': self.config.fitness.default_exercise,
                'audio_feedback': self.config.fitness.audio_feedback
            },
            'surveillance': {
                'person_tracking': self.config.surveillance.person_tracking_enabled,
                'zone_detection': self.config.surveillance.zone_detection_enabled,
                'fall_detection': self.config.surveillance.fall_detection_enabled
            },
            'web_app': {
                'host': self.config.web_host,
                'port': self.config.web_port,
                'debug': self.config.web_debug
            }
        }


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get global configuration."""
    return config_manager.get_app_config()


def get_camera_config() -> CameraConfig:
    """Get camera configuration."""
    return config_manager.get_camera_config()


def get_fitness_config() -> FitnessConfig:
    """Get fitness configuration."""
    return config_manager.get_fitness_config()


def get_surveillance_config() -> SurveillanceConfig:
    """Get surveillance configuration."""
    return config_manager.get_surveillance_config()


# Configuration validation functions
def validate_camera_config(config: CameraConfig) -> bool:
    """Validate camera configuration."""
    if config.width <= 0 or config.height <= 0:
        return False
    if config.fps <= 0 or config.fps > 120:
        return False
    if config.device_id < 0:
        return False
    return True


def validate_fitness_config(config: FitnessConfig) -> bool:
    """Validate fitness configuration."""
    if config.squat_upright_threshold <= config.squat_bottom_threshold:
        return False
    if config.pushup_up_threshold <= config.pushup_down_threshold:
        return False
    if config.bicep_curl_up_threshold >= config.bicep_curl_down_threshold:
        return False
    return True


def validate_surveillance_config(config: SurveillanceConfig) -> bool:
    """Validate surveillance configuration."""
    if config.rapid_movement_threshold <= 0:
        return False
    if config.loitering_time_threshold <= 0:
        return False
    if config.fall_angle_threshold <= 0 or config.fall_angle_threshold >= 90:
        return False
    return True