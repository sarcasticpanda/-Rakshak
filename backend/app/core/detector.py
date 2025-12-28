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
    
    def detect(self, frame: np.ndarray) -> List[dict]:
        """
        Detect people in frame with advanced filtering for Indian crowds
        
        Args:
            frame: Input BGR image
        
        Returns:
            List of detections, each dict contains:
                - bbox: [x1, y1, x2, y2]
                - confidence: float
                - class_id: int (always 0 for person)
                - class_name: str (always 'person')
        """
        if frame is None:
            return []
        
        # Run YOLO with original frame - YOLO handles resizing internally
        # DO NOT resize frame manually - it destroys small people!
        # iou=0.35 for aggressive NMS (fixes sparse duplicates, keeps dense detection)
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,  # 0.01 for dense crowds (200-400 people)
            iou=self.iou_threshold,    # 0.35 = aggressive NMS (suppress 35%+ overlap)
            classes=[0],     # Person class only (includes heads, partial bodies)
            max_det=1500,    # Allow up to 1500 detections
            imgsz=1920,      # YOLO resizes internally to this
            half=True,       # FP16 for speed
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
                    
                    # Reject if aspect ratio suggests vehicle (wide/flat shape)
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
