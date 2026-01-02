"""
Crowd Metrics Calculator
Analyzes crowd behavior from tracks and heatmap

Key Metrics:
1. Density - people per unit area
2. Compression - nearest neighbor distance (physical pressure)
3. Velocity Variance - speed chaos indicator
4. Direction Entropy - movement coordination
5. Heatmap Compression - spatial concentration

Uses tracker's built-in velocity - no redundant calculations.
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque


class CrowdMetrics:
    """
    Calculates crowd-level behavior metrics from tracks + heatmap
    
    Design:
    - Uses Track.velocity directly (no recomputation)
    - Uses Track.history for acceleration
    - Uses heatmap for spatial analysis
    - All metrics normalized 0-1 for risk scoring
    """
    
    def __init__(self, history_size: int = 30):
        """
        Args:
            history_size: Frames to keep for temporal analysis
        """
        self.history_size = history_size
        
        # History for temporal smoothing
        self.density_history = deque(maxlen=history_size)
        self.compression_history = deque(maxlen=history_size)
        self.variance_history = deque(maxlen=history_size)
        
        # NEW: Risk history for trend prediction
        self.risk_history = deque(maxlen=history_size)
        self.flow_collision_history = deque(maxlen=history_size)
        
        # Performance cache
        self._cached_compression = 0.0
        self._cache_update_count = 0
        
        # Constants
        self.COMFORTABLE_DISTANCE = 100.0  # pixels - comfortable inter-person spacing
        self.PANIC_SPEED_THRESHOLD = 20.0   # pixels/frame
        
        # ADJUSTED RISK WEIGHTS (based on video analysis)
        # Variance matters most (chaos indicator), then compression (proximity)
        self.WEIGHT_VARIANCE = 0.30      # Chaotic movement is key
        self.WEIGHT_COMPRESSION = 0.25   # Close proximity critical
        self.WEIGHT_DENSITY = 0.10       # Count alone not enough
        self.WEIGHT_ENTROPY = 0.10       # Coordination less critical
        self.WEIGHT_HEATMAP = 0.05       # Spatial less critical
        self.WEIGHT_FLOW_COLLISION = 0.10  # NEW: Opposing flow detection
        self.WEIGHT_PANIC_WAVE = 0.10      # NEW: Panic spreading detection
        
        print("[CrowdMetrics] Initialized with ADVANCED FEATURES")
        print(f"   History size: {history_size} frames")
        print(f"   Comfortable distance: {self.COMFORTABLE_DISTANCE} px")
        print(f"   Weights: V={self.WEIGHT_VARIANCE}, C={self.WEIGHT_COMPRESSION}, D={self.WEIGHT_DENSITY}, Flow={self.WEIGHT_FLOW_COLLISION}, Panic={self.WEIGHT_PANIC_WAVE}")
    
    def calculate(self, 
                  tracks: List,  # List of Track objects from ByteTracker
                  frame_shape: Tuple[int, int],
                  heatmap = None) -> Dict:
        """
        Calculate all crowd metrics
        
        Args:
            tracks: List of Track objects with velocity, history, etc.
            frame_shape: (height, width) of frame
            heatmap: EnhancedCrowdHeatmap object (optional)
            
        Returns:
            Dict with all metrics + per-person data
        """
        if len(tracks) == 0:
            return self._empty_metrics()
        
        # Extract per-person features from tracks
        per_person = self._extract_per_person_features(tracks)
        
        # Extract arrays for calculations
        speeds = [p['speed'] for p in per_person]
        directions = [p['direction'] for p in per_person]
        centers = [p['center'] for p in per_person]
        accelerations = [p['acceleration'] for p in per_person]
        
        # Calculate crowd-level metrics
        metrics = {
            # Basic count
            'count': len(tracks),
            
            # 1. Density (people per 100k pixels)
            'density': self._calculate_density(len(tracks), frame_shape),
            'density_normalized': self._normalize_density(len(tracks), frame_shape),
            
            # 2. Compression (nearest neighbor distance) - cached every 2 frames
            'compression': self._get_cached_compression(centers),
            'compression_normalized': self._normalize_compression(centers),
            
            # 3. Velocity variance (speed chaos)
            'velocity_variance': self._calculate_velocity_variance(speeds),
            'velocity_variance_normalized': self._normalize_variance(speeds),
            
            # 4. Direction entropy (coordination)
            'direction_entropy': self._calculate_direction_entropy(directions),
            'direction_entropy_normalized': self._normalize_entropy(directions),
            
            # 5. Heatmap compression (spatial concentration)
            'heatmap_compression': self._calculate_heatmap_compression(heatmap),
            'heatmap_compression_normalized': self._normalize_heatmap_compression(heatmap),
            
            # 6. NEW: Flow collision (opposing directions)
            'flow_collision': self._calculate_flow_collision(per_person),
            'flow_collision_normalized': self._normalize_flow_collision(per_person),
            
            # 7. NEW: Panic wave (sudden speed increase spreading)
            'panic_wave': self._calculate_panic_wave(per_person, frame_shape),
            'panic_wave_normalized': self._normalize_panic_wave(per_person, frame_shape),
            
            # Additional useful metrics
            'avg_speed': np.mean(speeds) if speeds else 0.0,
            'max_speed': np.max(speeds) if speeds else 0.0,
            'avg_acceleration': np.mean(accelerations) if accelerations else 0.0,
            'max_acceleration': np.max(accelerations) if accelerations else 0.0,
            
            # Panic indicators
            'high_speed_count': sum(1 for s in speeds if s > self.PANIC_SPEED_THRESHOLD),
            'high_speed_ratio': sum(1 for s in speeds if s > self.PANIC_SPEED_THRESHOLD) / len(speeds) if speeds else 0.0,
            
            # Per-person breakdown (for debugging)
            'per_person': per_person
        }
        
        # Update histories
        self.density_history.append(metrics['density'])
        self.compression_history.append(metrics['compression'])
        self.variance_history.append(metrics['velocity_variance'])
        self.flow_collision_history.append(metrics['flow_collision'])
        
        return metrics
    
    def _extract_per_person_features(self, tracks: List) -> List[Dict]:
        """
        Extract motion features from each track
        Uses Track.velocity and Track.history directly
        """
        features = []
        
        for track in tracks:
            # Speed from tracker's velocity (already smoothed by tracker)
            vx = (track.velocity[0] + track.velocity[2]) / 2
            vy = (track.velocity[1] + track.velocity[3]) / 2
            speed = np.sqrt(vx**2 + vy**2)
            
            # Direction from velocity
            direction = np.arctan2(vy, vx)  # -π to π
            
            # Acceleration from history
            acceleration = 0.0
            if len(track.history) >= 3:
                # Compare last 2 velocity changes
                v1 = track.history[-1] - track.history[-2]
                v2 = track.history[-2] - track.history[-3]
                dv = v1 - v2
                acceleration = np.sqrt(dv[0]**2 + dv[1]**2)
            
            # Center position
            center = track.get_center()
            
            features.append({
                'track_id': track.track_id,
                'speed': float(speed),
                'direction': float(direction),
                'acceleration': float(acceleration),
                'center': center,
                'confidence': float(track.confidence),
                'age': track.age
            })
        
        return features
    
    # ========================================
    # METRIC 1: DENSITY
    # ========================================
    
    def _calculate_density(self, count: int, frame_shape: Tuple[int, int]) -> float:
        """
        People per 100k pixels
        """
        height, width = frame_shape[:2]
        frame_area = height * width
        return (count / frame_area) * 100000
    
    def _normalize_density(self, count: int, frame_shape: Tuple[int, int]) -> float:
        """
        Normalize density to 0-1
        0 = sparse (<2 people/100k)
        1 = very dense (>30 people/100k)
        """
        density = self._calculate_density(count, frame_shape)
        # Clamp between 0-30, then normalize
        return min(density / 30.0, 1.0)
    
    # ========================================
    # METRIC 2: COMPRESSION
    # ========================================
    
    def _get_cached_compression(self, centers: List[Tuple[float, float]]) -> float:
        """
        Get compression with caching - calculate every 2 frames (5-10% faster)
        """
        self._cache_update_count += 1
        if self._cache_update_count % 2 == 0:
            self._cached_compression = self._calculate_compression(centers)
        return self._cached_compression
    
    def _calculate_compression(self, centers: List[Tuple[float, float]]) -> float:
        """
        Average nearest-neighbor distance
        Low distance = high compression = high risk
        """
        if len(centers) < 2:
            return 0.0
        
        distances = []
        for i, c1 in enumerate(centers):
            min_dist = float('inf')
            for j, c2 in enumerate(centers):
                if i != j:
                    dist = np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
                    min_dist = min(min_dist, dist)
            distances.append(min_dist)
        
        return np.mean(distances)
    
    def _normalize_compression(self, centers: List[Tuple[float, float]]) -> float:
        """
        Normalize compression to 0-1
        0 = comfortable spacing (>100px)
        1 = very compressed (<30px)
        """
        if len(centers) < 2:
            return 0.0
        
        avg_distance = self._calculate_compression(centers)
        
        # Inverse relationship: smaller distance = higher compression
        if avg_distance >= self.COMFORTABLE_DISTANCE:
            return 0.0
        elif avg_distance <= 30.0:
            return 1.0
        else:
            # Linear interpolation between 30-100px
            return 1.0 - ((avg_distance - 30.0) / 70.0)
    
    # ========================================
    # METRIC 3: VELOCITY VARIANCE
    # ========================================
    
    def _calculate_velocity_variance(self, speeds: List[float]) -> float:
        """
        Variance in speeds
        High variance = chaotic movement
        """
        if len(speeds) < 2:
            return 0.0
        return float(np.var(speeds))
    
    def _normalize_variance(self, speeds: List[float]) -> float:
        """
        Normalize velocity variance to 0-1
        0 = everyone moving same speed (coordinated)
        1 = very different speeds (chaotic)
        """
        if len(speeds) < 2:
            return 0.0
        
        variance = self._calculate_velocity_variance(speeds)
        # Typical variance range: 0-100
        return min(variance / 100.0, 1.0)
    
    # ========================================
    # METRIC 4: DIRECTION ENTROPY
    # ========================================
    
    def _calculate_direction_entropy(self, directions: List[float]) -> float:
        """
        Shannon entropy of movement directions
        Low entropy = everyone moving same direction (stampede!)
        High entropy = random movement (normal)
        """
        if len(directions) < 2:
            return 0.0
        
        # Bin into 8 sectors (45° each)
        bins = np.linspace(-np.pi, np.pi, 9)
        hist, _ = np.histogram(directions, bins=bins)
        
        # Normalize to probabilities
        hist = hist / len(directions)
        
        # Calculate Shannon entropy
        entropy = 0.0
        for p in hist:
            if p > 0:
                entropy -= p * np.log2(p)
        
        return float(entropy)
    
    def _normalize_entropy(self, directions: List[float]) -> float:
        """
        Normalize direction entropy to 0-1
        For stampede detection: LOW entropy = HIGH risk
        0 = high entropy (normal, random movement)
        1 = low entropy (everyone moving same direction)
        """
        if len(directions) < 2:
            return 0.0
        
        entropy = self._calculate_direction_entropy(directions)
        # Max entropy for 8 bins = log2(8) = 3.0
        # Invert: low entropy = high risk
        normalized_entropy = entropy / 3.0
        return 1.0 - normalized_entropy  # Invert so low entropy = high score
    
    # ========================================
    # METRIC 5: HEATMAP COMPRESSION
    # ========================================
    
    def _calculate_heatmap_compression(self, heatmap) -> float:
        """
        Measure spatial concentration from heatmap
        High intensity in small area = compression
        """
        if heatmap is None or not heatmap.is_bootstrapped():
            return 0.0
        
        heat_data = heatmap.temporal_heatmap
        
        if heat_data is None or heat_data.size == 0:
            return 0.0
        
        # Total heat accumulation
        total_heat = np.sum(heat_data)
        
        if total_heat == 0:
            return 0.0
        
        # Area with significant heat (>20% of max)
        max_heat = np.max(heat_data)
        threshold = 0.2 * max_heat
        hot_pixels = np.sum(heat_data > threshold)
        
        if hot_pixels == 0:
            return 0.0
        
        # Compression = heat density
        return float(total_heat / hot_pixels)
    
    def _normalize_heatmap_compression(self, heatmap) -> float:
        """
        Normalize heatmap compression to 0-1
        """
        compression = self._calculate_heatmap_compression(heatmap)
        # Typical range: 0-5
        return min(compression / 5.0, 1.0)
    
    # ========================================
    # METRIC 6: FLOW COLLISION (NEW)
    # ========================================
    
    def _calculate_flow_collision(self, per_person: List[Dict]) -> float:
        """
        Detect opposing crowd flows - people moving toward each other.
        High collision score = people on collision course = dangerous
        
        Returns: Collision intensity 0-1
        """
        if len(per_person) < 4:
            return 0.0
        
        collision_pairs = 0
        total_pairs = 0
        
        for i, p1 in enumerate(per_person):
            for p2 in per_person[i+1:]:
                # Only check pairs within 200 pixels
                dist = np.sqrt((p1['center'][0] - p2['center'][0])**2 + 
                              (p1['center'][1] - p2['center'][1])**2)
                if dist > 200 or dist < 10:
                    continue
                
                total_pairs += 1
                
                # Check if directions are opposing (within 45° of opposite)
                dir_diff = abs(p1['direction'] - p2['direction'])
                if dir_diff > np.pi:
                    dir_diff = 2 * np.pi - dir_diff
                
                # Opposing = ~180° difference
                if abs(dir_diff - np.pi) < np.pi/4:  # Within 45° of opposite
                    # Both must be moving (speed > 2 px/f)
                    if p1['speed'] > 2.0 and p2['speed'] > 2.0:
                        collision_pairs += 1
        
        if total_pairs == 0:
            return 0.0
        
        return collision_pairs / total_pairs
    
    def _normalize_flow_collision(self, per_person: List[Dict]) -> float:
        """Normalize flow collision to 0-1"""
        collision = self._calculate_flow_collision(per_person)
        # If >30% of nearby pairs are on collision course, that's maximum danger
        return min(collision / 0.3, 1.0)
    
    # ========================================
    # METRIC 7: PANIC WAVE (NEW)
    # ========================================
    
    def _calculate_panic_wave(self, per_person: List[Dict], frame_shape: Tuple[int, int]) -> float:
        """
        Detect panic spreading through crowd - clusters of high-speed people.
        Panic wave = localized groups of fast-moving people
        
        Returns: Panic intensity 0-1
        """
        if len(per_person) < 5:
            return 0.0
        
        # Find high-speed people (running)
        runners = [p for p in per_person if p['speed'] > self.PANIC_SPEED_THRESHOLD]
        
        if len(runners) < 2:
            return 0.0
        
        # Check if runners are clustered (panic spreading locally)
        cluster_count = 0
        for i, r1 in enumerate(runners):
            for r2 in runners[i+1:]:
                dist = np.sqrt((r1['center'][0] - r2['center'][0])**2 + 
                              (r1['center'][1] - r2['center'][1])**2)
                # Runners within 150px = panic cluster
                if dist < 150:
                    cluster_count += 1
        
        # Also check high acceleration (sudden speed increase)
        high_accel_count = sum(1 for p in per_person if p['acceleration'] > 10.0)
        
        # Combine: clustered runners + sudden acceleration
        panic_score = (len(runners) / len(per_person)) * 0.5 + \
                     (cluster_count / max(len(runners), 1)) * 0.3 + \
                     (high_accel_count / len(per_person)) * 0.2
        
        return min(panic_score, 1.0)
    
    def _normalize_panic_wave(self, per_person: List[Dict], frame_shape: Tuple[int, int]) -> float:
        """Normalize panic wave to 0-1"""
        panic = self._calculate_panic_wave(per_person, frame_shape)
        return min(panic, 1.0)  # Already 0-1
    
    # ========================================
    # UTILITY
    # ========================================
    
    def _empty_metrics(self) -> Dict:
        """Return zero metrics when no tracks"""
        return {
            'count': 0,
            'density': 0.0,
            'density_normalized': 0.0,
            'compression': 0.0,
            'compression_normalized': 0.0,
            'velocity_variance': 0.0,
            'velocity_variance_normalized': 0.0,
            'direction_entropy': 0.0,
            'direction_entropy_normalized': 0.0,
            'heatmap_compression': 0.0,
            'heatmap_compression_normalized': 0.0,
            'flow_collision': 0.0,
            'flow_collision_normalized': 0.0,
            'panic_wave': 0.0,
            'panic_wave_normalized': 0.0,
            'avg_speed': 0.0,
            'max_speed': 0.0,
            'avg_acceleration': 0.0,
            'max_acceleration': 0.0,
            'high_speed_count': 0,
            'high_speed_ratio': 0.0,
            'per_person': [],
            'risk_score': 0.0
        }
    
    def calculate_risk_score(self, metrics: Dict) -> float:
        """
        Calculate weighted risk score (0-100)
        
        Uses adjusted weights based on video analysis:
        - Variance (0.30): Chaotic movement is strongest stampede indicator
        - Compression (0.25): Close proximity creates pressure
        - Flow Collision (0.10): Opposing crowd flows
        - Panic Wave (0.10): Spreading panic detection
        - Density (0.10): Raw count matters but not decisive
        - Entropy (0.10): Coordination loss
        - Heatmap (0.05): Spatial concentration
        
        Args:
            metrics: Output from calculate()
            
        Returns:
            Risk score 0-100
        """
        if metrics['count'] == 0:
            return 0.0
        
        # Get new metrics with defaults
        flow_collision = metrics.get('flow_collision_normalized', 0.0)
        panic_wave = metrics.get('panic_wave_normalized', 0.0)
        
        base_risk = (
            metrics['density_normalized'] * self.WEIGHT_DENSITY +
            metrics['compression_normalized'] * self.WEIGHT_COMPRESSION +
            metrics['velocity_variance_normalized'] * self.WEIGHT_VARIANCE +
            metrics['direction_entropy_normalized'] * self.WEIGHT_ENTROPY +
            metrics['heatmap_compression_normalized'] * self.WEIGHT_HEATMAP +
            flow_collision * self.WEIGHT_FLOW_COLLISION +
            panic_wave * self.WEIGHT_PANIC_WAVE
        ) * 100
        
        # PANIC BOOST: Add extra risk when variance is EXTREME (>150) AND crowd is large (>20)
        # This ensures stampede scenarios with chaotic movement trigger CRITICAL warnings
        if metrics['velocity_variance'] > 150 and metrics['count'] > 20:
            panic_intensity = min((metrics['velocity_variance'] - 150) / 100, 0.3)  # Up to +30 points
            panic_boost = panic_intensity * 100
            base_risk += panic_boost
        
        # FLOW COLLISION BOOST: Add risk if many people on collision course
        if flow_collision > 0.5 and metrics['count'] > 30:
            base_risk += 15  # +15 for dangerous opposing flows
        
        # Store risk in history for trend prediction
        self.risk_history.append(base_risk)
        
        return np.clip(base_risk, 0.0, 100.0)
    
    def predict_risk_trend(self) -> Dict:
        """
        Predict if stampede is imminent based on risk trend.
        Analyzes last 30 frames to detect rising risk.
        
        Returns:
            Dict with prediction info
        """
        if len(self.risk_history) < 10:
            return {'prediction': 'INSUFFICIENT_DATA', 'trend': 0.0, 'imminent': False}
        
        recent = list(self.risk_history)[-15:]  # Last 15 frames
        older = list(self.risk_history)[-30:-15] if len(self.risk_history) >= 30 else list(self.risk_history)[:15]
        
        if not older:
            return {'prediction': 'INSUFFICIENT_DATA', 'trend': 0.0, 'imminent': False}
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older)
        
        # Calculate trend (risk change per frame)
        trend = (recent_avg - older_avg) / len(recent)
        
        # Predict risk in 5 seconds (~125 frames at 25fps, but we use trend)
        predicted_risk = recent_avg + trend * 25  # 1 second ahead
        
        # Determine prediction
        if trend > 2.0 and recent_avg > 50:
            prediction = 'STAMPEDE_IMMINENT'
            imminent = True
        elif trend > 1.0 and recent_avg > 40:
            prediction = 'RISK_INCREASING'
            imminent = False
        elif trend < -1.0:
            prediction = 'RISK_DECREASING'
            imminent = False
        else:
            prediction = 'STABLE'
            imminent = False
        
        return {
            'prediction': prediction,
            'trend': float(trend),
            'recent_avg': float(recent_avg),
            'predicted_risk_1sec': float(np.clip(predicted_risk, 0, 100)),
            'imminent': imminent
        }
    
    def get_summary(self) -> Dict:
        """Get summary statistics from history"""
        if len(self.density_history) == 0:
            return {}
        
        return {
            'avg_density': np.mean(list(self.density_history)),
            'max_density': np.max(list(self.density_history)),
            'avg_compression': np.mean(list(self.compression_history)),
            'min_compression': np.min(list(self.compression_history)),
            'avg_variance': np.mean(list(self.variance_history))
        }
