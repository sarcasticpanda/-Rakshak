"""
YOLO Person Detector
Detects people using YOLOv8 with GPU acceleration
"""
import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional
from app.utils.config import (
    YOLO_MODEL, YOLO_CONF_THRESHOLD, YOLO_IOU_THRESHOLD,
    YOLO_DEVICE, DETECT_PERSON_ONLY, VERBOSE,
    ENABLE_ASPECT_RATIO_FILTER, MIN_PERSON_ASPECT_RATIO, MAX_PERSON_ASPECT_RATIO,
    ENABLE_SIZE_FILTER, MIN_BOX_AREA, MAX_BOX_AREA, MAX_BOX_AREA_RATIO, 
    MIN_BOX_HEIGHT, MAX_BOX_HEIGHT, MAX_BOX_HEIGHT_RATIO,
    MAX_BOX_WIDTH, MAX_BOX_WIDTH_RATIO
)


class PersonDetector:
    """YOLO-based person detector"""
    
    # COCO dataset class IDs
    PERSON_CLASS_ID = 0
    
    def __init__(
        self,
        model_name: str = YOLO_MODEL,
        conf_threshold: float = YOLO_CONF_THRESHOLD,
        iou_threshold: float = YOLO_IOU_THRESHOLD,
        device: str = YOLO_DEVICE
    ):
        """
        Initialize YOLO detector
        
        Args:
            model_name: YOLOv8 model (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)
            conf_threshold: Confidence threshold (0.0-1.0)
            iou_threshold: NMS IOU threshold
            device: 'cuda' or 'cpu'
        """
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        
        if VERBOSE:
            print(f"[PersonDetector] Loading {model_name} on {device}...")
        
        # Load YOLO model
        self.model = YOLO(model_name)
        
        # Move to GPU if available
        if device == 'cuda':
            self.model.to(device)
        
        if VERBOSE:
            print(f"[PersonDetector] Model loaded successfully")
    
    def detect(self, frame: np.ndarray, adaptive: bool = True) -> List[dict]:
        """
        Detect people in frame with adaptive density-based filtering
        
        Args:
            frame: Input BGR image
            adaptive: If True, automatically detect density and adjust settings
        
        Returns:
            List of detections, each dict contains:
                - bbox: [x1, y1, x2, y2]
                - confidence: float
                - class_id: int (always 0 for person)
                - class_name: str (always 'person')
        """
        if frame is None:
            return []
        
        # Step 1: Initial detection to determine density
        frame_h, frame_w = frame.shape[:2]
        frame_area = frame_h * frame_w
        
        initial_results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=[0],
            max_det=1500,
            imgsz=1920,
            half=True,
            device=self.model.device,
            verbose=False
        )
        
        # Count initial detections
        initial_count = len(initial_results[0].boxes) if initial_results else 0
        
        # Calculate density: people per 100k pixels
        density = (initial_count / frame_area) * 100000
        
        # Determine if scene is DENSE or SPARSE
        # Dense: > 5 people per 100k pixels (e.g., 46+ people in 1280x720)
        # Sparse: <= 5 people per 100k pixels
        is_dense = density > 5.0
        
        if adaptive and is_dense:
            # DENSE STAMPEDE MODE: More aggressive detection
            results = self.model.predict(
                source=frame,
                conf=0.01,          # Very low confidence for packed crowds
                iou=0.25,           # Lower IoU to allow more overlapping detections
                classes=[0],
                max_det=2000,       # Increase max detections
                imgsz=1920,
                half=True,
                device=self.model.device,
                verbose=False
            )
        else:
            # SPARSE MODE: Conservative settings (avoid double boxes)
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,  # 0.02 - normal confidence
                iou=self.iou_threshold,    # 0.35 - aggressive NMS to prevent duplicates
                classes=[0],
                max_det=1500,
                imgsz=1920,
                half=True,
                device=self.model.device,
                verbose=False
            )
        
        detections = []
        
        # Parse results
        for result in results:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                # Get box data
                box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                conf = float(boxes.conf[i].cpu().numpy())
                cls = int(boxes.cls[i].cpu().numpy())
                
                # Filter 1: Person class only
                if DETECT_PERSON_ONLY and cls != self.PERSON_CLASS_ID:
                    continue
                
                # Filter 2: Aspect ratio filter (reject vehicles like scooters)
                if ENABLE_ASPECT_RATIO_FILTER:
                    x1, y1, x2, y2 = box
                    width = x2 - x1
                    height = y2 - y1
                    
                    if width <= 0 or height <= 0:
                        continue
                    
                    aspect_ratio = height / width
                    
                    # For DENSE mode: Relax aspect ratio (people compressed/overlapping)
                    if adaptive and is_dense:
                        # Allow wider range for packed crowds
                        if aspect_ratio < 0.6 or aspect_ratio > 4.0:
                            continue
                    else:
                        # Normal mode: Strict aspect ratio for sparse scenes
                        if aspect_ratio < MIN_PERSON_ASPECT_RATIO or aspect_ratio > MAX_PERSON_ASPECT_RATIO:
                            continue
                
                # Filter 3: Size filter (reject buildings, sky, huge boxes)
                if ENABLE_SIZE_FILTER:
                    x1, y1, x2, y2 = box
                    width = x2 - x1
                    height = y2 - y1
                    box_area = width * height
                    frame_h, frame_w = frame.shape[:2]
                    frame_area = frame_h * frame_w
                    
                    # Reject tiny boxes (noise)
                    if box_area < MIN_BOX_AREA:
                        continue
                    
                    # Reject huge boxes by absolute area
                    if box_area > MAX_BOX_AREA:
                        continue
                    
                    # Reject huge boxes by ratio (buildings, sky, background)
                    if box_area > frame_area * MAX_BOX_AREA_RATIO:
                        continue
                    
                    # Reject boxes too short (horizontal bars, signs)
                    if height < MIN_BOX_HEIGHT:
                        continue
                    
                    # Reject boxes too tall (absolute)
                    if height > MAX_BOX_HEIGHT:
                        continue
                    
                    # Reject boxes too tall (ratio - full-frame height = likely not a person)
                    if height > frame_h * MAX_BOX_HEIGHT_RATIO:
                        continue
                    
                    # Reject boxes too wide (absolute)
                    if width > MAX_BOX_WIDTH:
                        continue
                    
                    # Reject boxes too wide (ratio)
                    if width > frame_w * MAX_BOX_WIDTH_RATIO:
                        continue
                
                detection = {
                    'bbox': box.tolist(),
                    'confidence': conf,
                    'class_id': cls,
                    'class_name': result.names[cls]
                }
                
                detections.append(detection)
        
        return detections
    
    def detect_and_draw(
        self,
        frame: np.ndarray,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
        show_conf: bool = True
    ) -> Tuple[np.ndarray, List[dict]]:
        """
        Detect people and draw bounding boxes
        
        Args:
            frame: Input BGR image
            color: Box color (B, G, R)
            thickness: Box line thickness
            show_conf: Show confidence scores
        
        Returns:
            (annotated_frame, detections)
        """
        # Detect
        detections = self.detect(frame)
        
        # Draw
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            conf = det['confidence']
            label = det['class_name']
            
            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label with confidence
            if show_conf:
                text = f"{label}: {conf:.2f}"
            else:
                text = label
            
            # Text background
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - text_h - 4), (x1 + text_w, y1), color, -1)
            
            # Text
            cv2.putText(
                annotated, text, (x1, y1 - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1
            )
        
        return annotated, detections
    
    def get_person_count(self, frame: np.ndarray) -> int:
        """Get number of people detected in frame"""
        detections = self.detect(frame)
        return len(detections)
    
    def get_stats(self, detections: List[dict]) -> dict:
        """Get detection statistics"""
        if not detections:
            return {
                'count': 0,
                'avg_confidence': 0.0,
                'max_confidence': 0.0,
                'min_confidence': 0.0
            }
        
        confidences = [d['confidence'] for d in detections]
        
        return {
            'count': len(detections),
            'avg_confidence': np.mean(confidences),
            'max_confidence': np.max(confidences),
            'min_confidence': np.min(confidences)
        }
