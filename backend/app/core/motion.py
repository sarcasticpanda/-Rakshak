"""
Motion Feature Analyzer
Calculates speed, direction, acceleration for stampede detection
"""
import numpy as np
from collections import deque
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class MotionHistory:
    """Stores motion history for a single track"""
    track_id: int
    positions: deque = field(default_factory=lambda: deque(maxlen=30))  # Last 30 frames
    speeds: deque = field(default_factory=lambda: deque(maxlen=30))
    directions: deque = field(default_factory=lambda: deque(maxlen=30))
    accelerations: deque = field(default_factory=lambda: deque(maxlen=30))
    
    def add_position(self, center: Tuple[float, float], frame_id: int):
        """Add new position and calculate motion features"""
        self.positions.append((center, frame_id))
        
        if len(self.positions) >= 2:
            # Calculate speed and direction
            prev_pos, prev_frame = self.positions[-2]
            curr_pos, curr_frame = self.positions[-1]
            
            dt = max(1, curr_frame - prev_frame)
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            
            # Speed in pixels per frame
            speed = np.sqrt(dx**2 + dy**2) / dt
            self.speeds.append(speed)
            
            # Direction in radians (-π to π)
            direction = np.arctan2(dy, dx)
            self.directions.append(direction)
            
            # Acceleration (change in speed)
            if len(self.speeds) >= 2:
                accel = (self.speeds[-1] - self.speeds[-2]) / dt
                self.accelerations.append(accel)


class MotionAnalyzer:
    """
    Analyzes motion patterns for stampede detection
    
    Key indicators of panic/stampede:
    1. High average speed
    2. Sudden acceleration
    3. Direction changes (erratic movement)
    4. Collective motion in one direction (crowd surge)
    """
    
    def __init__(self, 
                 speed_threshold: float = 15.0,      # Pixels/frame for "fast" movement
                 accel_threshold: float = 5.0,       # Acceleration threshold
                 direction_change_threshold: float = np.pi/4):  # 45 degrees
        
        self.speed_threshold = speed_threshold
        self.accel_threshold = accel_threshold
        self.direction_change_threshold = direction_change_threshold
        
        # Track motion histories
        self.histories: Dict[int, MotionHistory] = {}
        self.frame_id = 0
        
        print(f"[MotionAnalyzer] Initialized")
        print(f"   Speed threshold: {speed_threshold} px/frame")
        print(f"   Acceleration threshold: {accel_threshold}")
        print(f"   Direction change: {np.degrees(direction_change_threshold):.0f}°")
    
    def update(self, tracks: List[Dict]) -> Dict:
        """
        Update with new tracks and return motion analysis
        
        Args:
            tracks: List of track dicts with 'track_id' and 'bbox'
            
        Returns:
            Dict with motion metrics and alerts
        """
        self.frame_id += 1
        
        active_ids = set()
        
        for track in tracks:
            track_id = track['track_id']
            bbox = track['bbox']
            active_ids.add(track_id)
            
            # Calculate center
            center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            
            # Create or update history
            if track_id not in self.histories:
                self.histories[track_id] = MotionHistory(track_id)
            
            self.histories[track_id].add_position(center, self.frame_id)
        
        # Clean up old tracks
        old_ids = [tid for tid in self.histories if tid not in active_ids]
        for tid in old_ids:
            if self.frame_id - self.histories[tid].positions[-1][1] > 30:
                del self.histories[tid]
        
        # Calculate metrics
        return self._analyze_motion(tracks)
    
    def _analyze_motion(self, tracks: List[Dict]) -> Dict:
        """Analyze current motion state"""
        
        if not tracks:
            return {
                'avg_speed': 0,
                'max_speed': 0,
                'fast_movers': 0,
                'fast_mover_ratio': 0,
                'avg_acceleration': 0,
                'sudden_accel_count': 0,
                'dominant_direction': None,
                'direction_agreement': 0,
                'panic_score': 0,
                'alerts': []
            }
        
        speeds = []
        accelerations = []
        directions = []
        fast_movers = 0
        sudden_accels = 0
        
        for track in tracks:
            tid = track['track_id']
            if tid in self.histories:
                hist = self.histories[tid]
                
                # Speed analysis
                if hist.speeds:
                    speed = hist.speeds[-1]
                    speeds.append(speed)
                    if speed > self.speed_threshold:
                        fast_movers += 1
                
                # Acceleration analysis
                if hist.accelerations:
                    accel = hist.accelerations[-1]
                    accelerations.append(accel)
                    if abs(accel) > self.accel_threshold:
                        sudden_accels += 1
                
                # Direction analysis
                if hist.directions:
                    directions.append(hist.directions[-1])
        
        # Calculate aggregates
        avg_speed = np.mean(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        avg_accel = np.mean(np.abs(accelerations)) if accelerations else 0
        
        # Direction agreement (how aligned is movement)
        direction_agreement = 0
        dominant_direction = None
        if len(directions) >= 3:
            # Circular mean for directions
            sin_sum = np.sum(np.sin(directions))
            cos_sum = np.sum(np.cos(directions))
            dominant_direction = np.arctan2(sin_sum, cos_sum)
            
            # Agreement: how many are within 45° of dominant
            agreement_count = sum(
                1 for d in directions 
                if abs(self._angle_diff(d, dominant_direction)) < self.direction_change_threshold
            )
            direction_agreement = agreement_count / len(directions)
        
        # Calculate panic score (0-100)
        panic_score = self._calculate_panic_score(
            avg_speed, max_speed, fast_movers, len(tracks),
            avg_accel, sudden_accels, direction_agreement
        )
        
        # Generate alerts
        alerts = []
        fast_ratio = fast_movers / len(tracks) if tracks else 0
        
        if fast_ratio > 0.5:
            alerts.append(f"⚠️ HIGH SPEED: {fast_ratio*100:.0f}% moving fast")
        
        if sudden_accels > 5:
            alerts.append(f"⚠️ SUDDEN MOVEMENT: {sudden_accels} people accelerating")
        
        if direction_agreement > 0.7 and avg_speed > self.speed_threshold * 0.7:
            alerts.append(f"⚠️ CROWD SURGE: {direction_agreement*100:.0f}% moving same direction")
        
        if panic_score > 70:
            alerts.append(f"🚨 PANIC DETECTED: Score {panic_score:.0f}/100")
        elif panic_score > 50:
            alerts.append(f"⚠️ ELEVATED RISK: Score {panic_score:.0f}/100")
        
        return {
            'avg_speed': avg_speed,
            'max_speed': max_speed,
            'fast_movers': fast_movers,
            'fast_mover_ratio': fast_ratio,
            'avg_acceleration': avg_accel,
            'sudden_accel_count': sudden_accels,
            'dominant_direction': dominant_direction,
            'direction_agreement': direction_agreement,
            'panic_score': panic_score,
            'alerts': alerts
        }
    
    def _calculate_panic_score(self, avg_speed, max_speed, fast_movers, total,
                               avg_accel, sudden_accels, direction_agreement) -> float:
        """
        Calculate panic score 0-100
        
        Factors:
        - Speed (40%): Higher speed = higher panic
        - Acceleration (30%): Sudden changes indicate panic
        - Crowd coherence (30%): High agreement + high speed = surge
        """
        score = 0
        
        # Speed component (0-40)
        speed_norm = min(avg_speed / (self.speed_threshold * 2), 1.0)
        fast_ratio = fast_movers / max(total, 1)
        score += (speed_norm * 20) + (fast_ratio * 20)
        
        # Acceleration component (0-30)
        accel_norm = min(avg_accel / (self.accel_threshold * 2), 1.0)
        sudden_ratio = sudden_accels / max(total, 1)
        score += (accel_norm * 15) + (sudden_ratio * 15)
        
        # Crowd coherence component (0-30)
        # High agreement with high speed = crowd surge (dangerous)
        if direction_agreement > 0.5 and avg_speed > self.speed_threshold * 0.5:
            score += direction_agreement * 30
        
        return min(score, 100)
    
    def _angle_diff(self, a: float, b: float) -> float:
        """Calculate smallest difference between two angles"""
        diff = a - b
        while diff > np.pi:
            diff -= 2 * np.pi
        while diff < -np.pi:
            diff += 2 * np.pi
        return diff
    
    def get_track_motion(self, track_id: int) -> Optional[Dict]:
        """Get motion data for a specific track"""
        if track_id not in self.histories:
            return None
        
        hist = self.histories[track_id]
        
        return {
            'track_id': track_id,
            'current_speed': hist.speeds[-1] if hist.speeds else 0,
            'avg_speed': np.mean(list(hist.speeds)) if hist.speeds else 0,
            'current_direction': hist.directions[-1] if hist.directions else 0,
            'current_acceleration': hist.accelerations[-1] if hist.accelerations else 0,
            'history_length': len(hist.positions)
        }
    
    def direction_to_arrow(self, direction: float) -> str:
        """Convert direction (radians) to arrow character"""
        if direction is None:
            return ""
        
        # Normalize to 0-2π
        d = direction % (2 * np.pi)
        
        # 8 directions
        if d < np.pi/8 or d >= 15*np.pi/8:
            return "→"
        elif d < 3*np.pi/8:
            return "↘"
        elif d < 5*np.pi/8:
            return "↓"
        elif d < 7*np.pi/8:
            return "↙"
        elif d < 9*np.pi/8:
            return "←"
        elif d < 11*np.pi/8:
            return "↖"
        elif d < 13*np.pi/8:
            return "↑"
        else:
            return "↗"
