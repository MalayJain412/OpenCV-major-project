"""
Database Integration Module

Handles SQLite database operations for storing session data, 
user preferences, alerts, and analytics.

Author: VisionTrack Project
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading


@dataclass
class SessionData:
    """Session data structure."""
    session_id: str
    mode: str
    start_time: datetime
    end_time: Optional[datetime]
    total_reps: int
    calories_burned: float
    people_detected: int
    alerts_generated: int
    duration_seconds: float
    exercise_type: Optional[str] = None
    form_score_avg: Optional[float] = None
    metadata: Optional[Dict] = None


@dataclass
class AlertRecord:
    """Alert record structure."""
    alert_id: int
    session_id: str
    alert_type: str
    timestamp: datetime
    person_id: int
    location_x: int
    location_y: int
    confidence: float
    description: str
    resolved: bool = False


@dataclass
class UserPreference:
    """User preference structure."""
    pref_id: int
    category: str
    key: str
    value: str
    user_id: Optional[str] = None


class DatabaseManager:
    """SQLite database manager for VisionTrack."""
    
    def __init__(self, db_path: str = "visiontrack.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Sessions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        mode TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        total_reps INTEGER DEFAULT 0,
                        calories_burned REAL DEFAULT 0.0,
                        people_detected INTEGER DEFAULT 0,
                        alerts_generated INTEGER DEFAULT 0,
                        duration_seconds REAL DEFAULT 0.0,
                        exercise_type TEXT,
                        form_score_avg REAL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Alerts table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        person_id INTEGER NOT NULL,
                        location_x INTEGER,
                        location_y INTEGER,
                        confidence REAL DEFAULT 0.0,
                        description TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                """)
                
                # User preferences table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        pref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, category, key)
                    )
                """)
                
                # Exercise stats table for detailed analytics
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS exercise_stats (
                        stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        person_id INTEGER NOT NULL,
                        exercise_type TEXT NOT NULL,
                        rep_number INTEGER NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        angle_value REAL,
                        form_score REAL,
                        phase TEXT,
                        confidence REAL DEFAULT 0.0,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                """)
                
                # Performance metrics table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        fps REAL DEFAULT 0.0,
                        processing_time_ms REAL DEFAULT 0.0,
                        memory_usage_mb REAL DEFAULT 0.0,
                        cpu_usage_percent REAL DEFAULT 0.0,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                """)
                
                # Create indexes for better performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_mode ON sessions(mode)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_session ON alerts(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_exercise_stats_session ON exercise_stats(session_id)")
                
                conn.commit()
            finally:
                conn.close()
    
    def create_session(self, mode: str, metadata: Optional[Dict] = None) -> str:
        """Create a new session and return session ID."""
        session_id = f"{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO sessions (session_id, mode, start_time, metadata)
                    VALUES (?, ?, ?, ?)
                """, (session_id, mode, datetime.now(), json.dumps(metadata) if metadata else None))
                conn.commit()
            finally:
                conn.close()
        
        return session_id
    
    def update_session(self, session_id: str, **kwargs):
        """Update session data."""
        if not kwargs:
            return
        
        # Handle datetime conversion for end_time
        if 'end_time' in kwargs and kwargs['end_time']:
            kwargs['end_time'] = kwargs['end_time']
        
        # Convert metadata to JSON if present
        if 'metadata' in kwargs and kwargs['metadata']:
            kwargs['metadata'] = json.dumps(kwargs['metadata'])
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [session_id]
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(f"UPDATE sessions SET {set_clause} WHERE session_id = ?", values)
                conn.commit()
            finally:
                conn.close()
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute("""
                    SELECT * FROM sessions WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()
                
                if row:
                    metadata = json.loads(row['metadata']) if row['metadata'] else None
                    return SessionData(
                        session_id=row['session_id'],
                        mode=row['mode'],
                        start_time=datetime.fromisoformat(row['start_time']),
                        end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                        total_reps=row['total_reps'],
                        calories_burned=row['calories_burned'],
                        people_detected=row['people_detected'],
                        alerts_generated=row['alerts_generated'],
                        duration_seconds=row['duration_seconds'],
                        exercise_type=row['exercise_type'],
                        form_score_avg=row['form_score_avg'],
                        metadata=metadata
                    )
            finally:
                conn.close()
        
        return None
    
    def get_recent_sessions(self, limit: int = 10, mode: Optional[str] = None) -> List[SessionData]:
        """Get recent sessions."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                query = "SELECT * FROM sessions"
                params = []
                
                if mode:
                    query += " WHERE mode = ?"
                    params.append(mode)
                
                query += " ORDER BY start_time DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                sessions = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else None
                    sessions.append(SessionData(
                        session_id=row['session_id'],
                        mode=row['mode'],
                        start_time=datetime.fromisoformat(row['start_time']),
                        end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                        total_reps=row['total_reps'],
                        calories_burned=row['calories_burned'],
                        people_detected=row['people_detected'],
                        alerts_generated=row['alerts_generated'],
                        duration_seconds=row['duration_seconds'],
                        exercise_type=row['exercise_type'],
                        form_score_avg=row['form_score_avg'],
                        metadata=metadata
                    ))
                
                return sessions
            finally:
                conn.close()
    
    def add_alert(self, session_id: str, alert_type: str, person_id: int,
                  location_x: int, location_y: int, confidence: float,
                  description: str) -> int:
        """Add an alert record."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    INSERT INTO alerts (session_id, alert_type, timestamp, person_id,
                                      location_x, location_y, confidence, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, alert_type, datetime.now(), person_id,
                      location_x, location_y, confidence, description))
                alert_id = cursor.lastrowid
                conn.commit()
                return alert_id
            finally:
                conn.close()
    
    def get_session_alerts(self, session_id: str) -> List[AlertRecord]:
        """Get alerts for a session."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute("""
                    SELECT * FROM alerts WHERE session_id = ? ORDER BY timestamp DESC
                """, (session_id,))
                rows = cursor.fetchall()
                
                alerts = []
                for row in rows:
                    alerts.append(AlertRecord(
                        alert_id=row['alert_id'],
                        session_id=row['session_id'],
                        alert_type=row['alert_type'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        person_id=row['person_id'],
                        location_x=row['location_x'],
                        location_y=row['location_y'],
                        confidence=row['confidence'],
                        description=row['description'],
                        resolved=bool(row['resolved'])
                    ))
                
                return alerts
            finally:
                conn.close()
    
    def resolve_alert(self, alert_id: int):
        """Mark an alert as resolved."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("UPDATE alerts SET resolved = TRUE WHERE alert_id = ?", (alert_id,))
                conn.commit()
            finally:
                conn.close()
    
    def save_exercise_stat(self, session_id: str, person_id: int, exercise_type: str,
                          rep_number: int, angle_value: float, form_score: float,
                          phase: str, confidence: float = 1.0):
        """Save detailed exercise statistics."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO exercise_stats (session_id, person_id, exercise_type,
                                              rep_number, timestamp, angle_value,
                                              form_score, phase, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, person_id, exercise_type, rep_number,
                      datetime.now(), angle_value, form_score, phase, confidence))
                conn.commit()
            finally:
                conn.close()
    
    def get_user_preference(self, category: str, key: str, user_id: Optional[str] = None,
                           default_value: Optional[str] = None) -> Optional[str]:
        """Get a user preference value."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    SELECT value FROM user_preferences 
                    WHERE category = ? AND key = ? AND (user_id = ? OR user_id IS NULL)
                    ORDER BY user_id DESC LIMIT 1
                """, (category, key, user_id))
                row = cursor.fetchone()
                return row[0] if row else default_value
            finally:
                conn.close()
    
    def set_user_preference(self, category: str, key: str, value: str,
                           user_id: Optional[str] = None):
        """Set a user preference value."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO user_preferences (user_id, category, key, value, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, category, key, value, datetime.now()))
                conn.commit()
            finally:
                conn.close()
    
    def get_analytics_summary(self, days: int = 7) -> Dict:
        """Get analytics summary for the last N days."""
        start_date = datetime.now() - timedelta(days=days)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # Session counts by mode
                cursor = conn.execute("""
                    SELECT mode, COUNT(*) as count, SUM(total_reps) as total_reps,
                           SUM(calories_burned) as total_calories, SUM(duration_seconds) as total_duration
                    FROM sessions WHERE start_time >= ? GROUP BY mode
                """, (start_date,))
                mode_stats = {row[0]: {
                    'sessions': row[1], 'reps': row[2] or 0,
                    'calories': row[3] or 0, 'duration': row[4] or 0
                } for row in cursor.fetchall()}
                
                # Alert counts by type
                cursor = conn.execute("""
                    SELECT alert_type, COUNT(*) as count FROM alerts 
                    WHERE timestamp >= ? GROUP BY alert_type
                """, (start_date,))
                alert_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Daily activity
                cursor = conn.execute("""
                    SELECT DATE(start_time) as date, COUNT(*) as sessions,
                           SUM(total_reps) as reps, SUM(alerts_generated) as alerts
                    FROM sessions WHERE start_time >= ? GROUP BY DATE(start_time)
                    ORDER BY date
                """, (start_date,))
                daily_activity = [{
                    'date': row[0], 'sessions': row[1],
                    'reps': row[2] or 0, 'alerts': row[3] or 0
                } for row in cursor.fetchall()]
                
                return {
                    'period_days': days,
                    'mode_statistics': mode_stats,
                    'alert_statistics': alert_stats,
                    'daily_activity': daily_activity,
                    'generated_at': datetime.now().isoformat()
                }
            finally:
                conn.close()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data beyond specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # Delete old sessions and their related data
                conn.execute("DELETE FROM exercise_stats WHERE session_id IN (SELECT session_id FROM sessions WHERE start_time < ?)", (cutoff_date,))
                conn.execute("DELETE FROM alerts WHERE session_id IN (SELECT session_id FROM sessions WHERE start_time < ?)", (cutoff_date,))
                conn.execute("DELETE FROM performance_metrics WHERE session_id IN (SELECT session_id FROM sessions WHERE start_time < ?)", (cutoff_date,))
                conn.execute("DELETE FROM sessions WHERE start_time < ?", (cutoff_date,))
                conn.commit()
                
                # Vacuum to reclaim space
                conn.execute("VACUUM")
            finally:
                conn.close()
    
    def export_session_data(self, session_id: str) -> Dict:
        """Export all data for a session."""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        alerts = self.get_session_alerts(session_id)
        
        return {
            'session': asdict(session),
            'alerts': [asdict(alert) for alert in alerts],
            'exported_at': datetime.now().isoformat()
        }
    
    def close(self):
        """Close database connections (cleanup)."""
        pass  # SQLite connections are closed after each operation


# Global database instance
db_manager = DatabaseManager()