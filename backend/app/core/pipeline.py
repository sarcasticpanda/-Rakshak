"""
Stampede Detection Pipeline - Complete integrated system
Combines: Adaptive Detection + Tracking + Heatmap Validation + Motion Analysis
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
from ultralytics import YOLO

from app.core.scene_analyzer import SceneAnalyzer
from app.core.heatmap import CrowdHeatmap
from app.core.tracker import ByteTracker
from app.core.motion import MotionAnalyzer
from app.utils.config import YOLO_MODEL, YOLO_DEVICE


class StampedePipeline:
    """
    Complete stampede detection pipeline with adaptive intelligence
    
    Pipeline stages:
    1. Scene Analysis → Determine sparse/medium/dense
    2. Adaptive YOLO → Adjust config for scene
    3. Post-YOLO Filtering → Remove noise
    4. Heatmap Validation → Remove false positives
    5. ByteTrack → Temporal consistency
    6. Motion Analysis → Speed, direction, panic
    7. Final Cleanup → Remove unstable tracks
    """
    
    def __init__(
        self,
        model_name: str = YOLO_MODEL,
        device: str = YOLO_DEVICE,
        use_heatmap: bool = True,
        verbose: bool = True
    ):
        """
        Initialize complete pipeline
        
        Args:
            model_name: YOLO model to use
            device: 'cuda' or 'cpu'
            use_heatmap: Enable heatmap validation
            verbose: Print initialization info
        """
        self.device = device
        self.use_heatmap = use_heatmap
        self.verbose = verbose
        
        if verbose:
            print(f"[StampedePipeline] Initializing...")
            print(f"   Model: {model_name}")
            print(f"   Device: {device}")
            print(f"   Heatmap: {'Enabled' if use_heatmap else 'Disabled'}")
        
        # Load YOLO model
        self.model = YOLO(model_name)
        if device == 'cuda':
            self.model.to(device)
        
        # Initialize components
        self.scene_analyzer = SceneAnalyzer(history_size=10)
        self.heatmap = None  # Created on first frame
        self.tracker = None  # Created with adaptive config
        self.motion_analyzer = MotionAnalyzer()
        
        # State
        self.frame_count = 0
        self.current_config = None
        
        if verbose:
            print(f"[StampedePipeline] Ready!")
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Process single frame through complete pipeline
        
        Args:
            frame: BGR input frame
            
        Returns:
            Dict with all results and metrics
        """
        self.frame_count += 1
        frame_h, frame_w = frame.shape[:2]
        
        # Initialize heatmap on first frame
        if self.heatmap is None:
            self.heatmap = CrowdHeatmap((frame_h, frame_w), decay=0.95)
        
        # STAGE 1: Initial detection for scene analysis
        # Use VERY LOW confidence to catch everyone for density estimation
        initial_results = self.model.predict(
            source=frame,
            conf=0.05,  # Very low confidence to see true density
            iou=0.30,
            classes=[0],
            max_det=2000,
            imgsz=1280,
            half=True,
            device=self.device,
            verbose=False
        )
        
        initial_count = len(initial_results[0].boxes) if initial_results else 0
        
        # STAGE 2: Scene analysis
        scene_info = self.scene_analyzer.analyze((frame_h, frame_w), initial_count)
        
        # Get adaptive config
        config = self.scene_analyzer.get_yolo_config(scene_info['mode'])
        
        # Update tracker if config changed
        if self.current_config is None or config['max_age'] != self.current_config['max_age']:
            self.tracker = ByteTracker(
                track_thresh=0.3,
                track_buffer=config['max_age'],
                match_thresh=0.4,
                min_hits=config['min_hits'],
                max_age=config['max_age']
            )
            self.current_config = config
        
        # STAGE 3: Adaptive YOLO detection
        results = self.model.predict(
            source=frame,
            conf=config['conf'],
            iou=config['iou'],
            classes=[0],
            max_det=config['max_det'],
            imgsz=config['imgsz'],
            half=True,
            device=self.device,
            verbose=False
        )
        
        # STAGE 4: Post-YOLO filtering
        detections = self._parse_and_filter(
            results,
            frame.shape,
            config
        )
        
        # Update heatmap FIRST (before validation)
        if self.use_heatmap:
            self.heatmap.update(detections)
        
        # STAGE 5: Heatmap validation (only after warmup period)
        if self.use_heatmap and self.frame_count > 20:  # Wait for heatmap to build up
            detections = self._heatmap_validation(detections, scene_info['mode'])
        
        # STAGE 6: Tracking
        tracks = self.tracker.update(detections, frame_size=(frame_w, frame_h))
        
        # STAGE 7: Motion analysis
        motion_data = self.motion_analyzer.update(tracks)
        
        # Return complete analysis
        return {
            'frame': frame,
            'detections': detections,
            'tracks': tracks,
            'motion': motion_data,
            'scene': scene_info,
            'config': config,
            'heatmap': self.heatmap.get_visualization() if self.use_heatmap else None
        }
    
    def _parse_and_filter(
        self,
        results,
        frame_shape: Tuple[int, int, int],
        config: Dict
    ) -> List[Dict]:
        """
        Parse YOLO results and apply post-detection filters
        
        Args:
            results: YOLO results
            frame_shape: (H, W, C)
            config: Scene config with thresholds
            
        Returns:
            Filtered detections
        """
        detections = []
        frame_h, frame_w = frame_shape[:2]
        frame_area = frame_h * frame_w
        
        for result in results:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                box = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())
                cls = int(boxes.cls[i].cpu().numpy())
                
                if cls != 0:  # Person class only
                    continue
                
                x1, y1, x2, y2 = box
                width = x2 - x1
                height = y2 - y1
                area = width * height
                
                # Filter 1: Minimum box area
                if area < config['min_box_area']:
                    continue
                
                # Filter 2: Maximum box ratio
                if area > frame_area * config['max_box_ratio']:
                    continue
                
                # Filter 3: Aspect ratio (person-shaped)
                if width <= 0 or height <= 0:
                    continue
                
                aspect_ratio = height / width
                
                # Adaptive aspect ratio
                if config['conf'] < 0.25:  # Dense mode - relaxed
                    if aspect_ratio < 0.6 or aspect_ratio > 4.0:
                        continue
                else:  # Sparse/medium - strict
                    if aspect_ratio < 0.8 or aspect_ratio > 3.5:
                        continue
                
                # Filter 4: Maximum absolute dimensions
                if height > 600 or width > 350:
                    continue
                
                detections.append({
                    'bbox': box.tolist(),
                    'confidence': conf,
                    'class_id': cls,
                    'class_name': 'person'
                })
        
        return detections
    
    def _heatmap_validation(
        self,
        detections: List[Dict],
        scene_mode: str
    ) -> List[Dict]:
        """
        Use heatmap to validate and clean detections
        
        Args:
            detections: Raw detections
            scene_mode: 'sparse', 'medium', 'dense'
            
        Returns:
            Validated detections
        """
        if not detections:
            return detections
        
        # Step 1: Remove detections outside hotspots
        # Use VERY lenient thresholds - heatmap is for removing outliers only
        if scene_mode == "sparse":
            # In sparse scenes, validate against heatmap
            threshold = 0.03  # Very lenient
        else:
            # In dense scenes, barely filter (allow new people)
            threshold = 0.01  # Extremely lenient
        
        validated = []
        for det in detections:
            # Allow detection if it's in ANY warm area
            if self.heatmap.validate_detection(det['bbox'], threshold=threshold):
                validated.append(det)
            elif scene_mode != "sparse":
                # In dense/medium, keep detection anyway (might be new person)
                validated.append(det)
        
        # Step 2: Remove duplicates using heatmap peaks
        # ONLY in sparse mode - dense crowds have legitimate overlaps
        if scene_mode == "sparse":
            # Remove duplicates in sparse
            validated = self.heatmap.filter_duplicates(validated, min_distance=50)
        
        return validated
    
    def visualize(self, result: Dict, show_heatmap: bool = True) -> np.ndarray:
        """
        Create visualization of pipeline results
        
        Args:
            result: Result dict from process_frame()
            show_heatmap: Show heatmap overlay
            
        Returns:
            Annotated frame
        """
        frame = result['frame'].copy()
        tracks = result['tracks']
        scene = result['scene']
        motion = result['motion']
        
        # Draw tracks with motion colors
        for track in tracks:
            tid = track['track_id']
            bbox = track['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Get motion info
            motion_info = self.motion_analyzer.get_track_motion(tid)
            
            if motion_info:
                speed = motion_info['current_speed']
                # Color based on speed
                if speed < 5:
                    color = (0, 255, 0)  # Green
                elif speed < 15:
                    color = (0, 255, 255)  # Yellow
                else:
                    color = (0, 0, 255)  # Red
            else:
                color = (128, 128, 128)  # Gray
            
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw ID
            cv2.putText(frame, f"#{tid}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw dashboard
        self._draw_dashboard(frame, scene, motion, len(tracks))
        
        # Overlay heatmap
        if show_heatmap and result['heatmap'] is not None:
            heatmap_vis = result['heatmap']
            frame = cv2.addWeighted(frame, 0.7, heatmap_vis, 0.3, 0)
        
        return frame
    
    def _draw_dashboard(self, frame, scene, motion, track_count):
        """Draw info dashboard"""
        h, w = frame.shape[:2]
        
        # Background
        cv2.rectangle(frame, (10, 10), (400, 180), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (400, 180), (255, 255, 255), 2)
        
        # Title
        cv2.putText(frame, "STAMPEDE DETECTION", (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Scene mode
        mode_colors = {'sparse': (0, 255, 0), 'medium': (0, 255, 255), 'dense': (0, 165, 255)}
        mode_color = mode_colors.get(scene['mode'], (255, 255, 255))
        cv2.putText(frame, f"Mode: {scene['mode'].upper()}", (20, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        
        # Metrics
        y = 90
        metrics = [
            f"People: {track_count}",
            f"Density: {scene['density']:.1f}",
            f"Speed: {motion['avg_speed']:.1f} px/f",
            f"Panic: {motion['panic_score']:.0f}/100"
        ]
        
        for text in metrics:
            cv2.putText(frame, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += 22
