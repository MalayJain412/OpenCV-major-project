"""
Audio utilities for providing audio feedback during exercises.

This module provides cross-platform audio feedback capabilities,
including beeps for rep counting and voice feedback.
"""

import platform
import time


class AudioFeedback:
    """Handles audio feedback for exercise tracking."""
    
    def __init__(self):
        self.system = platform.system()
        self.last_beep_time = 0
        self.min_beep_interval = 0.5  # Minimum seconds between beeps
        
        # Try to import audio libraries
        self.winsound_available = False
        self.pygame_available = False
        
        if self.system == "Windows":
            try:
                import winsound
                self.winsound = winsound
                self.winsound_available = True
            except ImportError:
                pass
        
        # Try pygame as fallback for all platforms
        try:
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.pygame = pygame
            self.pygame_available = True
        except ImportError:
            pass
    
    def play_beep(self, frequency=1000, duration_ms=150):
        """
        Play a beep sound.
        
        Args:
            frequency (int): Beep frequency in Hz
            duration_ms (int): Beep duration in milliseconds
        """
        current_time = time.time()
        
        # Prevent rapid repeated beeps
        if current_time - self.last_beep_time < self.min_beep_interval:
            return
        
        self.last_beep_time = current_time
        
        try:
            if self.winsound_available:
                self._beep_winsound(frequency, duration_ms)
            elif self.pygame_available:
                self._beep_pygame(frequency, duration_ms)
            else:
                self._beep_fallback()
        except Exception as e:
            print(f"Audio beep failed: {e}")
            self._beep_fallback()
    
    def _beep_winsound(self, frequency, duration_ms):
        """Beep using Windows winsound."""
        self.winsound.Beep(frequency, duration_ms)
    
    def _beep_pygame(self, frequency, duration_ms):
        """Beep using pygame mixer."""
        import numpy as np
        
        sample_rate = 22050
        duration_sec = duration_ms / 1000.0
        frames = int(duration_sec * sample_rate)
        
        # Generate sine wave
        arr = np.zeros((frames, 2), dtype=np.int16)
        arr[:, 0] = np.sin(2 * np.pi * frequency * np.linspace(0, duration_sec, frames)) * 32767 * 0.3
        arr[:, 1] = arr[:, 0]  # Stereo
        
        # Play sound
        sound = self.pygame.sndarray.make_sound(arr)
        sound.play()
        
        # Wait for sound to finish
        time.sleep(duration_sec)
    
    def _beep_fallback(self):
        """Fallback beep using terminal bell."""
        print("\a", end="", flush=True)
    
    def play_rep_count_beep(self):
        """Play a beep for rep counting."""
        self.play_beep(frequency=1000, duration_ms=120)
    
    def play_session_start_beep(self):
        """Play a beep to indicate session start."""
        self.play_beep(frequency=800, duration_ms=200)
    
    def play_session_end_beep(self):
        """Play a beep to indicate session end."""
        for _ in range(2):
            self.play_beep(frequency=600, duration_ms=150)
            time.sleep(0.1)
    
    def play_milestone_beep(self, milestone):
        """
        Play special beep for rep milestones.
        
        Args:
            milestone (int): Rep milestone (e.g., 10, 25, 50)
        """
        if milestone % 50 == 0:
            # Special beep for 50-rep milestones
            for _ in range(3):
                self.play_beep(frequency=1200, duration_ms=100)
                time.sleep(0.05)
        elif milestone % 25 == 0:
            # Special beep for 25-rep milestones
            for _ in range(2):
                self.play_beep(frequency=1100, duration_ms=120)
                time.sleep(0.1)
        elif milestone % 10 == 0:
            # Special beep for 10-rep milestones
            self.play_beep(frequency=1000, duration_ms=200)
    
    def is_audio_available(self):
        """Check if any audio system is available."""
        return self.winsound_available or self.pygame_available