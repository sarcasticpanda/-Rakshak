"""
Robust Detection Manager with Temporal Voting and Motion Consistency

This solves the fundamental problems:
1. Single-frame detections are noisy
2. Duplicates appear randomly across frames
3. False positives don't persist temporally
4. Real people move smoothly
"""
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class DetectionCandidate:
    """A detection that needs temporal validation"""
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    frame_id: int
    center: Tuple[float, float] = field(init=False)
    area: float = field(init=False)
    
    def __post_init__(self):
        self.center = ((self.bbox[0] + self.bbox[2]) / 2, 
                      (self.bbox[1] + self.bbox[3]) / 2)
        self.area = (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


class TemporalDetectionValidator:
    """
    Validates detections across time using:
    1. Spatial clustering (duplicate removal)
    2. Temporal voting (must appear in N/M frames)
    3. Motion consistency (no teleporting)
    """
    
    def __init__(self, 
                 temporal_window: int = 5,      # Look at last N frames
                 min_appearances: int = 3,       # Must appear in M frames
                 max_jump_distance: float = 100, # Max movement between frames
                 duplicate_iou_threshold: float = 0.5):  # IoU for duplicates
        
        self.temporal_window = temporal_window
        self.min_appearances = min_appearances
        self.max_jump_distance = max_jump_distance
        self.duplicate_iou_threshold = duplicate_iou_threshold
        
        # Detection history: frame_id -> list of DetectionCandidate
        self.detection_history = deque(maxlen=temporal_window)
        self.frame_count = 0
        
        # Track centers for motion consistency
        self.track_history = defaultdict(lambda: deque(maxlen=10))
        
        print(f"[TemporalValidator] Initialized")
        print(f"   Window: {temporal_window} frames")
        print(f"   Min appearances: {min_appearances}/{temporal_window}")
        print(f"   Max jump: {max_jump_distance} pixels")
    
    def validate_detections(self, raw_detections: List[Dict], 
                           frame_id: int) -> List[Dict]:
        """
        Apply temporal validation to raw YOLO detections
        
        Returns:
            Validated detections (duplicates removed, temporally confirmed)
        """
        self.frame_count = frame_id
        
        # Convert to candidates
        candidates = [
            DetectionCandidate(
                bbox=det['bbox'],
                confidence=det['confidence'],
                frame_id=frame_id
            )
            for det in raw_detections
        ]
        
        # Step 1: Remove spatial duplicates (current frame only)
        candidates = self._remove_spatial_duplicates(candidates)
        
        # Step 2: Add to history
        self.detection_history.append(candidates)
        
        # Step 3: Temporal voting (only if we have enough history)
        if len(self.detection_history) < self.min_appearances:
            # Not enough history yet, return filtered candidates
            return self._candidates_to_dicts(candidates)
        
        # Step 4: Find temporally consistent detections
        validated = self._temporal_voting()
        
        # Step 5: Motion consistency check
        validated = self._motion_consistency_check(validated)
        
        return validated
    
    def _remove_spatial_duplicates(self, candidates: List[DetectionCandidate]) -> List[DetectionCandidate]:
        """
        Remove duplicate boxes on the same person (current frame only)
        Keep highest confidence box from each cluster
        """
        if len(candidates) <= 1:
            return candidates
        
        # Build overlap matrix
        n = len(candidates)
        keep_mask = np.ones(n, dtype=bool)
        
        for i in range(n):
            if not keep_mask[i]:
                continue
            
            for j in range(i + 1, n):
                if not keep_mask[j]:
                    continue
                
                iou = self._calculate_iou(candidates[i].bbox, candidates[j].bbox)
                
                if iou > self.duplicate_iou_threshold:
                    # Duplicate found - keep higher confidence
                    if candidates[i].confidence >= candidates[j].confidence:
                        keep_mask[j] = False
                    else:
                        keep_mask[i] = False
                        break
        
        return [c for i, c in enumerate(candidates) if keep_mask[i]]
    
    def _temporal_voting(self) -> List[Dict]:
        """
        Find detections that appear consistently across temporal window
        
        A detection is valid if similar boxes appear in >= min_appearances frames
        """
        # Collect all candidates from history
        all_candidates = []
        for frame_candidates in self.detection_history:
            all_candidates.extend(frame_candidates)
        
        if not all_candidates:
            return []
        
        # Cluster spatially similar detections across time
        clusters = self._cluster_detections(all_candidates)
        
        # Vote: Keep clusters with enough temporal support
        validated = []
        for cluster in clusters:
            # Count unique frames in cluster
            unique_frames = len(set(c.frame_id for c in cluster))
            
            if unique_frames >= self.min_appearances:
                # This detection has temporal support - keep it
                # Use most recent detection from cluster
                most_recent = max(cluster, key=lambda c: c.frame_id)
                validated.append({
                    'bbox': most_recent.bbox,
                    'confidence': most_recent.confidence,
                    'temporal_support': unique_frames,
                    'cluster_size': len(cluster)
                })
        
        return validated
    
    def _cluster_detections(self, candidates: List[DetectionCandidate]) -> List[List[DetectionCandidate]]:
        """
        Cluster spatially similar detections (same person across frames)
        """
        if not candidates:
            return []
        
        # Simple greedy clustering based on spatial proximity
        clusters = []
        used = set()
        
        for i, cand in enumerate(candidates):
            if i in used:
                continue
            
            # Start new cluster
            cluster = [cand]
            used.add(i)
            
            # Find similar detections
            for j, other in enumerate(candidates):
                if j in used or j <= i:
                    continue
                
                # Check if spatially similar (center distance + area similarity)
                dist = np.sqrt((cand.center[0] - other.center[0])**2 + 
                             (cand.center[1] - other.center[1])**2)
                
                area_ratio = min(cand.area, other.area) / max(cand.area, other.area)
                
                # Same person if close in space and similar size
                if dist < 50 and area_ratio > 0.6:
                    cluster.append(other)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _motion_consistency_check(self, detections: List[Dict]) -> List[Dict]:
        """
        Remove detections that violate motion physics (teleporting)
        """
        if self.frame_count < 2:
            return detections
        
        # Get previous frame detections
        if len(self.detection_history) < 2:
            return detections
        
        prev_candidates = self.detection_history[-2] if len(self.detection_history) >= 2 else []
        
        validated = []
        for det in detections:
            cx = (det['bbox'][0] + det['bbox'][2]) / 2
            cy = (det['bbox'][1] + det['bbox'][3]) / 2
            
            # Find nearest previous detection
            if prev_candidates:
                min_dist = float('inf')
                for prev in prev_candidates:
                    dist = np.sqrt((cx - prev.center[0])**2 + (cy - prev.center[1])**2)
                    min_dist = min(min_dist, dist)
                
                # Reject if movement too large (teleporting)
                if min_dist > self.max_jump_distance:
                    continue
            
            validated.append(det)
        
        return validated
    
    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """Calculate IoU between two boxes"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _candidates_to_dicts(self, candidates: List[DetectionCandidate]) -> List[Dict]:
        """Convert candidates back to detection dicts"""
        return [{
            'bbox': c.bbox,
            'confidence': c.confidence,
            'class_id': 0,
            'class_name': 'person'
        } for c in candidates]
