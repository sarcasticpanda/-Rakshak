"""
Enhanced Crowd Heatmap with Confidence Weighting and Gap Detection

Provides:
1. Temporal presence tracking with decay
2. Confidence-weighted accumulation
3. Peak detection for gap filling
4. Heat-based validation
"""
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from scipy.ndimage import maximum_filter


class EnhancedCrowdHeatmap:
    """
    Multi-purpose heatmap for crowd analysis:
    - Validates detections (confirms crowd zones)
    - Fills detection gaps (predicts missing people)
    - Reduces duplicates (identifies peak centers)
    """
    
    def __init__(self, 
                 frame_shape: Tuple[int, int],
                 decay_rate: float = 0.90,
                 resolution_scale: float = 0.25,
                 gaussian_kernel: int = 31,
                 gaussian_sigma: float = 15):
        """
        Args:
            frame_shape: (height, width) of video frames
            decay_rate: Exponential decay per frame (0.90 = 10% fade)
            resolution_scale: Heatmap resolution vs frame (0.25 = 1/4 size)
            gaussian_kernel: Size of Gaussian blur kernel
            gaussian_sigma: Sigma for Gaussian blur
        """
        self.frame_h, self.frame_w = frame_shape
        self.decay_rate = decay_rate
        self.resolution_scale = resolution_scale
        
        # Heatmap resolution
        self.heatmap_h = int(self.frame_h * resolution_scale)
        self.heatmap_w = int(self.frame_w * resolution_scale)
        
        # Gaussian parameters
        self.gaussian_kernel = gaussian_kernel
        self.gaussian_sigma = gaussian_sigma
        
        # Initialize heatmaps
        self.temporal_heatmap = np.zeros((self.heatmap_h, self.heatmap_w), dtype=np.float32)
        self.confidence_heatmap = np.zeros((self.heatmap_h, self.heatmap_w), dtype=np.float32)
        
        # Statistics
        self.update_count = 0
        self.max_heat = 0.0
        
        # Visualization cache for performance
        self._vis_cache = None
        self._vis_frame_count = 0
        
        print(f"[EnhancedHeatmap] Initialized")
        print(f"   Frame: {self.frame_w}x{self.frame_h}")
        print(f"   Heatmap: {self.heatmap_w}x{self.heatmap_h}")
        print(f"   Decay: {decay_rate}, Gaussian: {gaussian_kernel}px σ={gaussian_sigma}")
    
    def update(self, detections: List[Dict]):
        """
        Update heatmap with new detections
        
        Args:
            detections: List of detection dicts with 'bbox' and 'confidence'
        """
        # Step 1: Apply temporal decay
        self.temporal_heatmap *= self.decay_rate
        self.confidence_heatmap *= self.decay_rate
        
        # Step 2: Add new detections
        for det in detections:
            bbox = det['bbox']
            confidence = det['confidence']
            
            # Calculate center in heatmap coordinates
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            
            hx = int(cx * self.resolution_scale)
            hy = int(cy * self.resolution_scale)
            
            # Bounds check
            if 0 <= hx < self.heatmap_w and 0 <= hy < self.heatmap_h:
                # Temporal heatmap: uniform weight
                self.temporal_heatmap[hy, hx] += 1.0
                
                # Confidence heatmap: weighted by conf^2
                weight = confidence ** 2
                self.confidence_heatmap[hy, hx] += weight
        
        # Step 3: Apply Gaussian blur to spread influence
        if self.gaussian_kernel > 0:
            self.temporal_heatmap = cv2.GaussianBlur(
                self.temporal_heatmap, 
                (self.gaussian_kernel, self.gaussian_kernel), 
                self.gaussian_sigma
            )
            self.confidence_heatmap = cv2.GaussianBlur(
                self.confidence_heatmap,
                (self.gaussian_kernel, self.gaussian_kernel),
                self.gaussian_sigma
            )
        
        # Step 4: Normalize to [0, 1]
        max_temporal = np.max(self.temporal_heatmap)
        max_confidence = np.max(self.confidence_heatmap)
        
        if max_temporal > 0:
            self.temporal_heatmap /= max_temporal
        if max_confidence > 0:
            self.confidence_heatmap /= max_confidence
        
        self.max_heat = max_temporal
        self.update_count += 1
    
    def get_heat_at_bbox(self, bbox: List[float], use_confidence: bool = False) -> float:
        """
        Get heat value at bounding box center
        
        Args:
            bbox: [x1, y1, x2, y2]
            use_confidence: Use confidence-weighted heatmap
            
        Returns:
            Heat value in [0, 1]
        """
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        hx = int(cx * self.resolution_scale)
        hy = int(cy * self.resolution_scale)
        
        # Bounds check
        if not (0 <= hx < self.heatmap_w and 0 <= hy < self.heatmap_h):
            return 0.0
        
        heatmap = self.confidence_heatmap if use_confidence else self.temporal_heatmap
        return float(heatmap[hy, hx])
    
    def get_heat_at_center(self, center: Tuple[float, float]) -> float:
        """Get heat value at specific center point"""
        cx, cy = center
        hx = int(cx * self.resolution_scale)
        hy = int(cy * self.resolution_scale)
        
        if not (0 <= hx < self.heatmap_w and 0 <= hy < self.heatmap_h):
            return 0.0
        
        return float(self.temporal_heatmap[hy, hx])
    
    def find_local_maxima(self, 
                         min_heat: float = 0.5,
                         min_distance: int = 60,
                         max_peaks: int = 50) -> List[Tuple[int, int]]:
        """
        Find local maxima in heatmap (potential missing people)
        
        Args:
            min_heat: Minimum heat threshold (0-1)
            min_distance: Minimum distance between peaks (pixels in original frame)
            max_peaks: Maximum number of peaks to return
            
        Returns:
            List of (x, y) coordinates in original frame space
        """
        # Apply threshold
        thresholded = self.temporal_heatmap.copy()
        thresholded[thresholded < min_heat] = 0
        
        # Find local maxima using maximum filter
        footprint_size = int(min_distance * self.resolution_scale)
        footprint_size = max(3, footprint_size)  # At least 3x3
        if footprint_size % 2 == 0:
            footprint_size += 1  # Must be odd
        
        local_max = maximum_filter(thresholded, size=footprint_size)
        peaks = (thresholded == local_max) & (thresholded > 0)
        
        # Get peak coordinates
        peak_coords = np.argwhere(peaks)
        
        if len(peak_coords) == 0:
            return []
        
        # Convert to original frame coordinates
        peak_list = []
        for py, px in peak_coords[:max_peaks]:
            # Convert from heatmap to frame coords
            fx = int(px / self.resolution_scale)
            fy = int(py / self.resolution_scale)
            peak_list.append((fx, fy))
        
        return peak_list
    
    def get_visualization(self, frame: np.ndarray = None) -> np.ndarray:
        """
        Create colored heatmap visualization (no blending - caller controls alpha)
        Uses caching to update every 2 frames for 3-5% performance boost
        
        Args:
            frame: Original BGR frame (not used - kept for compatibility)
            
        Returns:
            Colored heatmap image (JET colormap) ready for alpha blending
        """
        # Cache visualization - update every 2 updates
        if self._vis_cache is None or (self.update_count - self._vis_frame_count) >= 2:
            # Resize heatmap to frame size
            heatmap_resized = cv2.resize(
                self.temporal_heatmap,
                (self.frame_w, self.frame_h),
                interpolation=cv2.INTER_NEAREST  # Faster than LINEAR
            )
            
            # Convert to color (JET colormap)
            self._vis_cache = cv2.applyColorMap(
                (heatmap_resized * 255).astype(np.uint8),
                cv2.COLORMAP_JET
            )
            self._vis_frame_count = self.update_count
        
        return self._vis_cache
    
    def is_bootstrapped(self, min_frames: int = 30) -> bool:
        """Check if heatmap has enough data"""
        return self.update_count >= min_frames
    
    def reset(self):
        """Reset heatmap (useful for scene changes)"""
        self.temporal_heatmap.fill(0)
        self.confidence_heatmap.fill(0)
        self.update_count = 0
        self.max_heat = 0.0
