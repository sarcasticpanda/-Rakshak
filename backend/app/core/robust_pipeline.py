"""
Robust Detection Pipeline
Combines YOLO + Temporal Validation + Adaptive Settings + Heatmap Intelligence
"""
import numpy as np
from typing import List, Dict, Tuple
from app.core.detector import PersonDetector
from app.core.temporal_validator import TemporalDetectionValidator
from app.core.enhanced_heatmap import EnhancedCrowdHeatmap


class RobustDetectionPipeline:
    """
    Production-ready detection pipeline with:
    1. Adaptive YOLO configuration (dense vs sparse)
    2. Temporal validation (remove flickering false positives)
    3. Motion consistency (no teleporting)
    4. Duplicate removal
    5. Heatmap intelligence (validate + gap filling)
    """
    
    def __init__(self, enable_heatmap: bool = True):
        # Base detector
        self.detector = PersonDetector()
        
        # Temporal validator
        self.temporal_validator = TemporalDetectionValidator(
            temporal_window=5,      # Look at last 5 frames
            min_appearances=3,       # Must appear in 3/5 frames
            max_jump_distance=150,   # Max 150px movement per frame
            duplicate_iou_threshold=0.4  # 40% IoU = duplicate
        )
        
        # Heatmap (initialized on first frame)
        self.enable_heatmap = enable_heatmap
        self.heatmap = None
        
        # Scene state
        self.frame_count = 0
        self.current_mode = "medium"
        
        # Detection history for density estimation
        self.recent_counts = []
        
        # Heatmap configuration
        self.heatmap_config = {
            'sparse_threshold': 0.4,   # Strict for sparse
            'medium_threshold': 0.3,   # Balanced
            'dense_threshold': 0.2,    # Lenient for dense
            'gap_fill_heat_min': 0.5,  # Strong peaks only
            'gap_fill_distance': 60,   # Peak separation
            'gap_fill_max': 50,        # Safety limit
            'bootstrap_frames': 30,    # Warmup period
        }
        
        print(f"[RobustPipeline] Initialized")
        print(f"   Heatmap: {'Enabled' if enable_heatmap else 'Disabled'}")
    
    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], Dict]:
        """
        Detect people with full pipeline
        
        Returns:
            (detections, metadata)
            - detections: Validated list of people
            - metadata: Scene info, mode, stats
        """
        self.frame_count += 1
        height, width = frame.shape[:2]
        frame_area = height * width
        
        # Initialize heatmap on first frame
        if self.heatmap is None and self.enable_heatmap:
            self.heatmap = EnhancedCrowdHeatmap(
                frame_shape=(height, width),
                decay_rate=0.90,
                resolution_scale=0.25
            )
        
        # Step 1: Determine scene mode
        mode = self._determine_mode(frame, frame_area)
        
        # Step 2: Run YOLO with adaptive settings
        raw_detections = self._adaptive_yolo_detection(frame, mode)
        
        # Step 2.5: Update heatmap every 2 frames (15-20% faster)
        # Visual smoothness doesn't require every-frame updates
        if self.enable_heatmap and self.frame_count % 2 == 0:
            self.heatmap.update(raw_detections)
        
        # Step 3: Heatmap validation (if enabled and bootstrapped)
        if self.enable_heatmap and self.heatmap.is_bootstrapped(self.heatmap_config['bootstrap_frames']):
            heatmap_validated = self._heatmap_validation(raw_detections, mode)
        else:
            heatmap_validated = raw_detections
        
        # Step 4: Temporal validation (remove noise, duplicates)
        validated_detections = self.temporal_validator.validate_detections(
            heatmap_validated, 
            self.frame_count
        )
        
        # Step 5: Gap filling (dense mode only, if heatmap enabled)
        if self.enable_heatmap and mode == "dense" and self.heatmap.is_bootstrapped():
            filled_detections = self._fill_detection_gaps(validated_detections)
        else:
            filled_detections = validated_detections
        
        # Step 7: Update history
        self.recent_counts.append(len(filled_detections))
        if len(self.recent_counts) > 10:
            self.recent_counts.pop(0)
        
        # Metadata
        metadata = {
            'mode': mode,
            'raw_count': len(raw_detections),
            'heatmap_validated_count': len(heatmap_validated),
            'temporal_validated_count': len(validated_detections),
            'final_count': len(filled_detections),
            'frame_id': self.frame_count,
            'density': len(filled_detections) / frame_area * 100000,
            'heatmap_bootstrapped': self.heatmap.is_bootstrapped() if self.heatmap else False
        }
        
        return filled_detections, metadata
    
    def _determine_mode(self, frame: np.ndarray, frame_area: float) -> str:
        """
        Determine if scene is sparse, medium, or dense
        Use recent history for stability
        """
        if self.frame_count <= 10:
            # Bootstrap: Use quick low-confidence scan
            bootstrap_dets = self.detector.model.predict(
                source=frame,
                conf=0.01,
                iou=0.3,
                classes=[0],
                max_det=1500,
                imgsz=1280,
                half=True,
                device=self.detector.device,
                verbose=False
            )
            count = len(bootstrap_dets[0].boxes) if bootstrap_dets else 0
            density = count / frame_area * 100000
        else:
            # Use smoothed recent history
            if self.recent_counts:
                avg_count = np.mean(self.recent_counts[-5:])
                density = avg_count / frame_area * 100000
            else:
                density = 0
        
        # Classify
        if density < 3.0:
            return "sparse"
        elif density > 8.0:
            return "dense"
        else:
            return "medium"
    
    def _adaptive_yolo_detection(self, frame: np.ndarray, mode: str) -> List[Dict]:
        """
        Run YOLO with mode-specific settings
        """
        if mode == "sparse":
            # Precision-first: Avoid duplicates
            results = self.detector.model.predict(
                source=frame,
                conf=0.25,      # Higher confidence
                iou=0.45,       # Aggressive NMS
                classes=[0],
                max_det=500,
                imgsz=1280,
                half=True,
                device=self.detector.device,
                verbose=False
            )
        elif mode == "dense":
            # Recall-first: Catch everyone
            results = self.detector.model.predict(
                source=frame,
                conf=0.01,      # Very low confidence
                iou=0.25,       # Relaxed NMS
                classes=[0],
                max_det=2000,
                imgsz=1920,
                half=True,
                device=self.detector.device,
                verbose=False
            )
        else:  # medium
            # Balanced
            results = self.detector.model.predict(
                source=frame,
                conf=0.15,
                iou=0.35,
                classes=[0],
                max_det=1000,
                imgsz=1600,
                half=True,
                device=self.detector.device,
                verbose=False
            )
        
        # Convert to detection dicts
        detections = []
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                box = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())
                
                detections.append({
                    'bbox': box.tolist(),
                    'confidence': conf,
                    'class_id': 0,
                    'class_name': 'person'
                })
        
        return detections
    
    def _heatmap_validation(self, detections: List[Dict], mode: str) -> List[Dict]:
        """
        Validate detections using heatmap (removes false positives in cold zones)
        
        Args:
            detections: Raw YOLO detections
            mode: Scene mode (sparse, medium, dense)
            
        Returns:
            Validated detections (FPs removed)
        """
        if not detections:
            return []
        
        validated = []
        threshold = self.heatmap_config[f'{mode}_threshold']
        
        for det in detections:
            heat_value = self.heatmap.get_heat_at_bbox(det['bbox'])
            confidence = det['confidence']
            
            # Accept if either high confidence OR in hot zone
            if confidence > 0.5 or heat_value > threshold:
                validated.append(det)
        
        return validated
    
    def _fill_detection_gaps(self, detections: List[Dict]) -> List[Dict]:
        """
        Fill gaps where heatmap shows people but no detections exist (dense mode only)
        
        Args:
            detections: Validated detections
            
        Returns:
            Detections + synthetic boxes for gaps
        """
        # Find heatmap peaks
        peaks = self.heatmap.find_local_maxima(
            min_heat=self.heatmap_config['gap_fill_heat_min'],
            min_distance=self.heatmap_config['gap_fill_distance'],
            max_peaks=self.heatmap_config['gap_fill_max']
        )
        
        if not peaks:
            return detections
        
        # Get average box size from current detections
        if detections:
            widths = [det['bbox'][2] - det['bbox'][0] for det in detections]
            heights = [det['bbox'][3] - det['bbox'][1] for det in detections]
            avg_w = np.mean(widths)
            avg_h = np.mean(heights)
        else:
            # Default size if no detections
            avg_w = 50
            avg_h = 100
        
        # Check each peak for gap
        filled = detections.copy()
        synthetic_count = 0
        search_radius = 40  # Pixels
        
        for peak_x, peak_y in peaks:
            # Check if peak has nearby detection
            has_detection = False
            for det in detections:
                cx = (det['bbox'][0] + det['bbox'][2]) / 2
                cy = (det['bbox'][1] + det['bbox'][3]) / 2
                dist = np.sqrt((cx - peak_x)**2 + (cy - peak_y)**2)
                
                if dist < search_radius:
                    has_detection = True
                    break
            
            # Gap found: Add synthetic detection
            if not has_detection and synthetic_count < self.heatmap_config['gap_fill_max']:
                synthetic_box = [
                    peak_x - avg_w/2,
                    peak_y - avg_h/2,
                    peak_x + avg_w/2,
                    peak_y + avg_h/2
                ]
                
                filled.append({
                    'bbox': synthetic_box,
                    'confidence': 0.15,  # Low confidence marker
                    'class_id': 0,
                    'class_name': 'person',
                    'synthetic': True
                })
                synthetic_count += 1
        
        return filled
