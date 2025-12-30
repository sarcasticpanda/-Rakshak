"""
ByteTrack Multi-Object Tracker - FIXED VERSION
- Properly validates box sizes before output
- No ghost/drifting boxes
- Synced with detector's size constraints
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


# Size constraints - PHASE 1: Relaxed for dense crowds
MAX_BOX_WIDTH = 450      # Was 350 - allow wider boxes for merged detections
MAX_BOX_HEIGHT = 700     # Was 600 - allow taller boxes
MAX_BOX_AREA = 150000    # Was 100000 - allow larger merged groups
MIN_BOX_AREA = 600       # Was 800 - allow smaller distant people


@dataclass
class Track:
    """Single tracked object"""
    track_id: int
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    age: int = 0
    hits: int = 1
    time_since_update: int = 0
    history: List[np.ndarray] = field(default_factory=list)
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(4))
    
    def predict(self):
        """Predict next position - but DON'T change size"""
        # Only apply velocity to center, keep size fixed
        old_w = self.bbox[2] - self.bbox[0]
        old_h = self.bbox[3] - self.bbox[1]
        old_cx = (self.bbox[0] + self.bbox[2]) / 2
        old_cy = (self.bbox[1] + self.bbox[3]) / 2
        
        # Move center by velocity (only x,y movement, not size change)
        vel_cx = (self.velocity[0] + self.velocity[2]) / 2
        vel_cy = (self.velocity[1] + self.velocity[3]) / 2
        
        new_cx = old_cx + vel_cx
        new_cy = old_cy + vel_cy
        
        # Reconstruct bbox with same size
        self.bbox = np.array([
            new_cx - old_w/2,
            new_cy - old_h/2,
            new_cx + old_w/2,
            new_cy + old_h/2
        ])
        
        self.age += 1
        self.time_since_update += 1
        return self.bbox
    
    def update(self, bbox: np.ndarray, confidence: float):
        """Update track with new detection"""
        if len(self.history) > 0:
            # Smooth velocity calculation
            self.velocity = 0.5 * self.velocity + 0.5 * (bbox - self.history[-1])
        
        self.bbox = bbox.copy()
        self.confidence = confidence
        self.hits += 1
        self.time_since_update = 0
        
        self.history.append(bbox.copy())
        if len(self.history) > 30:
            self.history.pop(0)
    
    def get_center(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)
    
    def get_trajectory(self) -> List[Tuple[float, float]]:
        return [((b[0]+b[2])/2, (b[1]+b[3])/2) for b in self.history]
    
    def is_valid_size(self, frame_w: int, frame_h: int) -> bool:
        """Check if bbox is valid size (not too big) - PHASE 1: Relaxed constraints"""
        w = self.bbox[2] - self.bbox[0]
        h = self.bbox[3] - self.bbox[1]
        area = w * h
        
        if w <= 0 or h <= 0:
            return False
        if w > MAX_BOX_WIDTH or w > frame_w * 0.35:  # Was 0.25, now 0.35
            return False
        if h > MAX_BOX_HEIGHT or h > frame_h * 0.65:  # Was 0.5, now 0.65
            return False
        if area > MAX_BOX_AREA or area < MIN_BOX_AREA:
            return False
        return True


class ByteTracker:
    """
    ByteTrack tracker - FIXED to prevent ghost/oversized boxes
    """
    
    def __init__(
        self,
        track_thresh: float = 0.05,  # PHASE 1B: Lowered to 0.05 for maximum coverage
        track_buffer: int = 15,      # Keep same
        match_thresh: float = 0.20,  # Lowered to 0.20 - very lenient matching for dense crowds
        min_hits: int = 1,           # Lowered to 1 - instant track confirmation
        max_age: int = 20            # Raised to 20 - keep tracks longer through occlusion
    ):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.min_hits = min_hits
        self.max_age = max_age
        
        self.tracks: List[Track] = []
        self.next_id = 1
        self.frame_count = 0
        self.frame_size = (1920, 1080)  # Default, updated per frame
    
    def update(self, detections: List[dict], frame_size: Tuple[int, int] = None, heatmap = None) -> List[dict]:
        """
        Update tracker with new detections
        
        Args:
            detections: List of detection dicts
            frame_size: (height, width) tuple
            heatmap: EnhancedCrowdHeatmap object for confidence boosting (PHASE 1)
        """
        self.frame_count += 1
        
        if frame_size:
            self.frame_size = frame_size
        
        # Predict existing tracks
        for track in self.tracks:
            track.predict()
        
        if len(detections) == 0:
            self._cleanup_tracks()
            return self._get_output()
        
        # PHASE 1: Boost confidence for detections in hot zones
        if heatmap is not None and heatmap.is_bootstrapped():
            for det in detections:
                heat = heatmap.get_heat_at_bbox(det['bbox'], use_confidence=True)
                if heat > 0.4:  # Hot zone threshold
                    # Boost confidence by up to +0.15 for detections in crowd areas
                    boost = min(heat * 0.15, 0.15)
                    det['confidence'] = min(det['confidence'] + boost, 1.0)
        
        det_bboxes = np.array([d['bbox'] for d in detections])
        det_scores = np.array([d['confidence'] for d in detections])
        
        # Get valid track bboxes
        # frame_size is (height, width), is_valid_size expects (frame_w, frame_h)
        frame_h, frame_w = self.frame_size
        valid_tracks = [t for t in self.tracks if t.is_valid_size(frame_w, frame_h)]
        
        if len(valid_tracks) > 0 and len(det_bboxes) > 0:
            track_bboxes = np.array([t.bbox for t in valid_tracks])
            iou_matrix = self._compute_iou(det_bboxes, track_bboxes)
            matched, unmatched_dets, unmatched_tracks = self._hungarian_match(iou_matrix)
            
            # Update matched tracks
            for det_idx, track_idx in matched:
                valid_tracks[track_idx].update(det_bboxes[det_idx], det_scores[det_idx])
            
            # Unmatched detections -> new tracks (only high confidence)
            for det_idx in unmatched_dets:
                if det_scores[det_idx] >= self.track_thresh:
                    self._create_track(det_bboxes[det_idx], det_scores[det_idx])
        else:
            # No existing tracks - create from all high-conf detections
            for i, bbox in enumerate(det_bboxes):
                if det_scores[i] >= self.track_thresh:
                    self._create_track(bbox, det_scores[i])
        
        self._cleanup_tracks()
        return self._get_output()
    
    def _create_track(self, bbox: np.ndarray, confidence: float):
        """Create new track"""
        track = Track(
            track_id=self.next_id,
            bbox=bbox.copy(),
            confidence=confidence
        )
        track.history.append(bbox.copy())
        self.tracks.append(track)
        self.next_id += 1
    
    def _compute_iou(self, boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """Compute IoU matrix"""
        n1, n2 = len(boxes1), len(boxes2)
        iou = np.zeros((n1, n2))
        
        for i in range(n1):
            for j in range(n2):
                iou[i, j] = self._iou_single(boxes1[i], boxes2[j])
        return iou
    
    def _iou_single(self, b1: np.ndarray, b2: np.ndarray) -> float:
        """Single IoU computation"""
        x1 = max(b1[0], b2[0])
        y1 = max(b1[1], b2[1])
        x2 = min(b1[2], b2[2])
        y2 = min(b1[3], b2[3])
        
        inter = max(0, x2-x1) * max(0, y2-y1)
        area1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
        area2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
        union = area1 + area2 - inter
        
        return inter / union if union > 0 else 0
    
    def _hungarian_match(self, iou_matrix: np.ndarray) -> Tuple[List, List, List]:
        """Greedy matching with threshold"""
        if iou_matrix.size == 0:
            return [], list(range(iou_matrix.shape[0])), list(range(iou_matrix.shape[1]))
        
        matched = []
        unmatched_dets = set(range(iou_matrix.shape[0]))
        unmatched_tracks = set(range(iou_matrix.shape[1]))
        
        # Greedy matching
        while unmatched_dets and unmatched_tracks:
            best_iou = 0
            best_pair = None
            
            for d in unmatched_dets:
                for t in unmatched_tracks:
                    if iou_matrix[d, t] > best_iou:
                        best_iou = iou_matrix[d, t]
                        best_pair = (d, t)
            
            if best_iou < self.match_thresh or best_pair is None:
                break
            
            matched.append(best_pair)
            unmatched_dets.remove(best_pair[0])
            unmatched_tracks.remove(best_pair[1])
        
        return matched, list(unmatched_dets), list(unmatched_tracks)
    
    def _cleanup_tracks(self):
        """Remove old/invalid tracks"""
        valid_tracks = []
        
        # frame_size is (height, width)
        frame_h, frame_w = self.frame_size
        
        for track in self.tracks:
            # Remove if too old without update
            if track.time_since_update > self.max_age:
                continue
            
            # Remove if bbox became invalid size
            # Pass (frame_w, frame_h) to match function signature
            if not track.is_valid_size(frame_w, frame_h):
                continue
            
            # Remove if bbox went out of frame
            # bbox is [x1, y1, x2, y2] - x compared to width, y compared to height
            if track.bbox[0] < -100 or track.bbox[1] < -100:
                continue
            if track.bbox[2] > frame_w + 100:  # x2 vs width
                continue
            if track.bbox[3] > frame_h + 100:  # y2 vs height
                continue
            
            valid_tracks.append(track)
        
        self.tracks = valid_tracks
    
    def _get_output(self) -> List[dict]:
        """Get output - ONLY confirmed, valid-sized tracks"""
        output = []
        
        # frame_size is (height, width), is_valid_size expects (frame_w, frame_h)
        frame_h, frame_w = self.frame_size
        
        for track in self.tracks:
            # Must have enough hits AND valid size AND recent update
            if track.hits < self.min_hits:
                continue
            if track.time_since_update > 5:  # Raised from 3 - show tracks even with brief gaps
                continue
            if not track.is_valid_size(frame_w, frame_h):
                continue
            
            output.append({
                'track_id': track.track_id,
                'bbox': track.bbox.tolist(),
                'confidence': track.confidence,
                'trajectory': track.get_trajectory(),
                'velocity': track.velocity.tolist(),
                'age': track.age
            })
        
        return output
    
    def get_track_count(self) -> int:
        return len([t for t in self.tracks if t.hits >= self.min_hits])
    
    def get_total_ids(self) -> int:
        return self.next_id - 1
    
    def reset(self):
        self.tracks = []
        self.next_id = 1
        self.frame_count = 0
