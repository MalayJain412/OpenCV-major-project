"""
CSV logging utilities for exercise session data.

This module provides functions to log exercise data to CSV files
for analysis and progress tracking.
"""

import csv
import os
from datetime import datetime
from typing import Optional, Dict, Any


class SessionLogger:
    """Handles CSV logging for exercise sessions."""
    
    def __init__(self, log_directory="logs"):
        """
        Initialize session logger.
        
        Args:
            log_directory (str): Directory to store log files
        """
        self.log_directory = log_directory
        self.session_start_time = datetime.now()
        self.session_id = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_directory, exist_ok=True)
        
        # Set up log file path
        self.log_file = os.path.join(
            self.log_directory, 
            f"session_{self.session_id}.csv"
        )
        
        self.is_initialized = False
        self._ensure_csv_header()
    
    def _ensure_csv_header(self):
        """Ensure CSV file has proper header."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'person_id', 
                    'rep_number',
                    'knee_angle',
                    'squat_depth_quality',
                    'exercise_state',
                    'session_id'
                ])
            self.is_initialized = True
    
    def log_rep(self, person_id: int, rep_number: int, knee_angle: Optional[float] = None,
                depth_quality: str = "unknown", exercise_state: str = "unknown"):
        """
        Log a completed repetition.
        
        Args:
            person_id (int): ID of the person performing exercise
            rep_number (int): Current rep number for this person
            knee_angle (float, optional): Knee angle at bottom of squat
            depth_quality (str): Quality assessment of squat depth
            exercise_state (str): Current exercise state
        """
        timestamp = datetime.now().isoformat()
        
        row_data = [
            timestamp,
            person_id,
            rep_number,
            f"{knee_angle:.2f}" if knee_angle is not None else "N/A",
            depth_quality,
            exercise_state,
            self.session_id
        ]
        
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
        except Exception as e:
            print(f"Error logging rep data: {e}")
    
    def log_session_start(self, config_info: Optional[Dict[str, Any]] = None):
        """
        Log session start information.
        
        Args:
            config_info (dict, optional): Configuration parameters for the session
        """
        # Create session info file
        info_file = os.path.join(
            self.log_directory,
            f"session_{self.session_id}_info.txt"
        )
        
        try:
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"Session Start: {self.session_start_time.isoformat()}\n")
                f.write(f"Session ID: {self.session_id}\n")
                f.write("="*50 + "\n")
                
                if config_info:
                    f.write("Configuration:\n")
                    for key, value in config_info.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("="*50 + "\n")
                
                f.write("Session Log:\n")
        except Exception as e:
            print(f"Error creating session info file: {e}")
    
    def log_session_end(self, total_reps: int, participants: int):
        """
        Log session end summary.
        
        Args:
            total_reps (int): Total repetitions across all participants
            participants (int): Number of participants
        """
        end_time = datetime.now()
        duration = end_time - self.session_start_time
        
        info_file = os.path.join(
            self.log_directory,
            f"session_{self.session_id}_info.txt"
        )
        
        try:
            with open(info_file, 'a', encoding='utf-8') as f:
                f.write(f"Session End: {end_time.isoformat()}\n")
                f.write(f"Duration: {duration}\n")
                f.write(f"Total Reps: {total_reps}\n")
                f.write(f"Participants: {participants}\n")
                f.write(f"Average Reps per Person: {total_reps/participants if participants > 0 else 0:.1f}\n")
        except Exception as e:
            print(f"Error updating session info: {e}")
    
    def get_session_stats(self):
        """
        Get current session statistics.
        
        Returns:
            dict: Session statistics
        """
        stats = {
            'session_id': self.session_id,
            'start_time': self.session_start_time,
            'duration': datetime.now() - self.session_start_time,
            'log_file': self.log_file
        }
        
        # Try to read current rep counts from CSV
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    if rows:
                        # Count reps per person
                        person_reps = {}
                        for row in rows:
                            person_id = int(row['person_id'])
                            rep_num = int(row['rep_number'])
                            person_reps[person_id] = max(person_reps.get(person_id, 0), rep_num)
                        
                        stats['total_reps'] = sum(person_reps.values())
                        stats['participants'] = len(person_reps)
                        stats['person_reps'] = person_reps
                    else:
                        stats['total_reps'] = 0
                        stats['participants'] = 0
                        stats['person_reps'] = {}
            else:
                stats['total_reps'] = 0
                stats['participants'] = 0
                stats['person_reps'] = {}
                
        except Exception as e:
            print(f"Error reading session stats: {e}")
            stats['total_reps'] = 0
            stats['participants'] = 0
            stats['person_reps'] = {}
        
        return stats
    
    def export_summary_report(self, output_file: Optional[str] = None):
        """
        Export a summary report of the session.
        
        Args:
            output_file (str, optional): Output file path. Defaults to auto-generated name.
        """
        if output_file is None:
            output_file = os.path.join(
                self.log_directory,
                f"session_{self.session_id}_summary.txt"
            )
        
        stats = self.get_session_stats()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("EXERCISE SESSION SUMMARY\n")
                f.write("="*50 + "\n")
                f.write(f"Session ID: {stats['session_id']}\n")
                f.write(f"Start Time: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {stats['duration']}\n")
                f.write(f"Total Participants: {stats['participants']}\n")
                f.write(f"Total Repetitions: {stats['total_reps']}\n")
                f.write("\n")
                
                if stats['person_reps']:
                    f.write("INDIVIDUAL PERFORMANCE:\n")
                    f.write("-" * 30 + "\n")
                    for person_id, reps in stats['person_reps'].items():
                        f.write(f"Person {person_id}: {reps} reps\n")
                
                f.write(f"\nDetailed log: {os.path.basename(self.log_file)}\n")
                
        except Exception as e:
            print(f"Error creating summary report: {e}")
    
    def get_log_file_path(self):
        """Get the path to the current log file."""
        return self.log_file
    
    def get_session_id(self):
        """Get the current session ID."""
        return self.session_id