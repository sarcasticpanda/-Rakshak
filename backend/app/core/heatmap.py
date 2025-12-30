"""
Heatmap Module - Crowd probability mapping for validation
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
from collections import deque


class CrowdHeatmap:
    """
    Accumulates crowd presence over time to create probability heatmap
    
    Uses:
    - Validate detections (boxes outside hotspots = likely false)
    - Remove duplicates (multiple boxes in same hotspot = duplicates)
    - Stabilize tracking (heatmap shows where people actually are)
    """
    
    def __init__(self, frame_shape: Tuple[int, int], decay: float = 0.95):
        """
        Args:
            frame_shape: (height, width)
            decay: How fast old data fades (0.95 = slow decay)
        """
        self.height, self.width = frame_shape
        self.decay = decay
        
        # Heatmap: accumulated crowd presence
        self.heatmap = np.zeros((self.height, self.width), dtype=np.float32)
        
        # Gaussian kernel for spreading heat
        self.kernel_size = 31
        self.sigma = 15
        
        print(f"[CrowdHeatmap] Initialized {self.width}x{self.height}")
        print(f"   Decay: {decay}, Kernel: {self.kernel_size}x{self.kernel_size}")
    
    def update(self, detections: List[Dict]):
        """
        Update heatmap with new detections
        
        Args:
            detections: List of detection dicts with 'bbox'
        """
        # Decay old heatmap
        self.heatmap *= self.decay
        
        # Add new detections
        for det in detections:
            bbox = det['bbox']
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            
            # Ensure within bounds
            cx = np.clip(cx, 0, self.width - 1)
            cy = np.clip(cy, 0, self.height - 1)
            
            # Add heat at center
            self.heatmap[cy, cx] += 1.0
        
        # Apply Gaussian blur to spread heat
        self.heatmap = cv2.GaussianBlur(
            self.heatmap,
            (self.kernel_size, self.kernel_size),
            self.sigma
        )
    
    def validate_detection(self, bbox: List[float], threshold: float = 0.1) -> bool:
        """
        Check if detection is in a hot region (likely valid)
        
        Args:
            bbox: [x1, y1, x2, y2]
            threshold: Minimum heatmap value to be valid
            
        Returns:
            True if detection is in hot region
        """
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        
        # Ensure within bounds
        cx = np.clip(cx, 0, self.width - 1)
        cy = np.clip(cy, 0, self.height - 1)
        
        # Check heatmap value at center
        heat_value = self.heatmap[cy, cx]
        
        # Normalize by max heat
        max_heat = np.max(self.heatmap)
        if max_heat > 0:
            normalized_heat = heat_value / max_heat
        else:
            normalized_heat = 0
        
        return normalized_heat >= threshold
    
    def filter_duplicates(self, detections: List[Dict], min_distance: int = 30) -> List[Dict]:
        """
        Remove duplicate detections using heatmap peaks
        
        If multiple boxes are very close and in same hotspot, keep only the one
        closest to the peak.
        
        Args:
            detections: List of detection dicts
            min_distance: Minimum distance between valid detections
            
        Returns:
            Filtered list of detections
        """
        if len(detections) <= 1:
            return detections
        
        # Extract centers
        centers = []
        for det in detections:
            bbox = det['bbox']
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            centers.append((cx, cy))
        
        # Mark detections to keep
        keep = [True] * len(detections)
        
        for i in range(len(detections)):
            if not keep[i]:
                continue
            
            cx1, cy1 = centers[i]
            
            for j in range(i + 1, len(detections)):
                if not keep[j]:
                    continue
                
                cx2, cy2 = centers[j]
                
                # Calculate distance
                dist = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
                
                if dist < min_distance:
                    # Too close - keep the one with higher confidence
                    # or closer to heatmap peak
                    heat1 = self.heatmap[
                        np.clip(cy1, 0, self.height-1),
                        np.clip(cx1, 0, self.width-1)
                    ]
                    heat2 = self.heatmap[
                        np.clip(cy2, 0, self.height-1),
                        np.clip(cx2, 0, self.width-1)
                    ]
                    
                    if heat2 > heat1:
                        keep[i] = False
                        break
                    else:
                        keep[j] = False
        
        return [det for i, det in enumerate(detections) if keep[i]]
    
    def get_visualization(self, alpha: float = 0.6) -> np.ndarray:
        """
        Get heatmap as colored overlay
        
        Args:
            alpha: Transparency (0=invisible, 1=opaque)
            
        Returns:
            BGR heatmap image
        """
        # Normalize heatmap to 0-255
        if np.max(self.heatmap) > 0:
            normalized = (self.heatmap / np.max(self.heatmap) * 255).astype(np.uint8)
        else:
            normalized = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # Apply colormap (hot = red, cold = blue)
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
        
        return colored
    
    def get_density_grid(self, grid_size: int = 50) -> np.ndarray:
        """
        Get grid-based density map
        
        Args:
            grid_size: Size of each grid cell in pixels
            
        Returns:
            Grid array with density values
        """
        grid_h = self.height // grid_size
        grid_w = self.width // grid_size
        
        grid = np.zeros((grid_h, grid_w), dtype=np.float32)
        
        for i in range(grid_h):
            for j in range(grid_w):
                y1 = i * grid_size
                y2 = min(y1 + grid_size, self.height)
                x1 = j * grid_size
                x2 = min(x1 + grid_size, self.width)
                
                # Average heat in this cell
                grid[i, j] = np.mean(self.heatmap[y1:y2, x1:x2])
        
        return grid
