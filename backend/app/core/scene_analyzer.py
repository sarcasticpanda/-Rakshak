"""
Scene Analyzer - Determines crowd density and scene characteristics
"""
import numpy as np
from typing import List, Dict, Tuple
from collections import deque


class SceneAnalyzer:
    """
    Analyzes scene characteristics to enable adaptive detection
    
    Key metrics:
    - Density: people per unit area
    - Stability: how consistent is detection count
    - Coverage: what % of frame has people
    """
    
    # Density thresholds (people per 100k pixels)
    SPARSE_THRESHOLD = 2.5   # Below this = sparse
    DENSE_THRESHOLD = 6.0    # Above this = dense
    
    def __init__(self, history_size: int = 10):
        """
        Args:
            history_size: Number of frames to track for stability
        """
        self.history_size = history_size
        self.count_history = deque(maxlen=history_size)
        self.density_history = deque(maxlen=history_size)
        
        self.current_mode = "medium"  # sparse, medium, dense
        self.stable_count = 0
        
        print(f"[SceneAnalyzer] Initialized")
        print(f"   Sparse threshold: < {self.SPARSE_THRESHOLD} people/100k px")
        print(f"   Dense threshold: > {self.DENSE_THRESHOLD} people/100k px")
    
    def analyze(self, frame_shape: Tuple[int, int], detection_count: int) -> Dict:
        """
        Analyze current frame and return scene characteristics
        
        Args:
            frame_shape: (height, width)
            detection_count: Number of people detected
            
        Returns:
            Dict with scene analysis
        """
        height, width = frame_shape
        frame_area = height * width
        
        # Calculate density (people per 100k pixels)
        density = (detection_count / frame_area) * 100000
        
        # Update history
        self.count_history.append(detection_count)
        self.density_history.append(density)
        
        # Calculate stability (coefficient of variation)
        if len(self.count_history) >= 3:
            std = np.std(list(self.count_history))
            mean = np.mean(list(self.count_history))
            stability = 1.0 - min(std / (mean + 1), 1.0)  # 0=unstable, 1=stable
        else:
            stability = 0.5
        
        # Determine scene mode using stable average
        if len(self.density_history) >= 3:
            avg_density = np.mean(list(self.density_history))
        else:
            avg_density = density
        
        # Classify scene
        if avg_density < self.SPARSE_THRESHOLD:
            scene_mode = "sparse"
        elif avg_density > self.DENSE_THRESHOLD:
            scene_mode = "dense"
        else:
            scene_mode = "medium"
        
        # Smooth mode transitions (avoid flickering)
        if scene_mode != self.current_mode:
            self.stable_count += 1
            if self.stable_count >= 3:  # Require 3 frames to switch
                self.current_mode = scene_mode
                self.stable_count = 0
        else:
            self.stable_count = 0
        
        return {
            'mode': self.current_mode,
            'density': avg_density,
            'count': detection_count,
            'stability': stability,
            'frame_area': frame_area
        }
    
    def get_yolo_config(self, scene_mode: str = None) -> Dict:
        """
        Get optimal YOLO configuration for scene mode
        
        Args:
            scene_mode: 'sparse', 'medium', or 'dense'
            
        Returns:
            Dict with YOLO parameters
        """
        if scene_mode is None:
            scene_mode = self.current_mode
        
        if scene_mode == "sparse":
            # SPARSE: Kill duplicates, high precision
            return {
                'conf': 0.35,      # High confidence only
                'iou': 0.55,       # Very aggressive NMS
                'max_det': 500,
                'imgsz': 640,
                'min_box_area': 800,      # Remove tiny boxes
                'max_box_ratio': 0.03,    # Remove huge boxes
                'min_hits': 3,            # Track must survive 3 frames
                'max_age': 5              # Kill after 5 missed frames
            }
        
        elif scene_mode == "dense":
            # DENSE: Catch everyone, allow overlaps
            return {
                'conf': 0.01,      # VERY low confidence to catch tiny people
                'iou': 0.25,       # Very relaxed NMS for overlaps
                'max_det': 2000,
                'imgsz': 1280,     # Higher resolution
                'min_box_area': 100,      # Allow very small boxes
                'max_box_ratio': 0.06,
                'min_hits': 2,            # Confirm faster
                'max_age': 15             # Keep longer in occlusions
            }
        
        else:  # medium
            # MEDIUM: Balanced
            return {
                'conf': 0.20,
                'iou': 0.40,
                'max_det': 1200,
                'imgsz': 960,
                'min_box_area': 300,
                'max_box_ratio': 0.04,
                'min_hits': 2,
                'max_age': 10
            }
