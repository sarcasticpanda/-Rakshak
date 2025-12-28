"""
Test YOLOv11 with different confidence thresholds
Goal: Find optimal threshold for dense crowd detection
"""

import cv2
import torch
from ultralytics import YOLO
from pathlib import Path
import numpy as np

def filter_detections(results, aspect_filter=True, min_ratio=0.3, max_ratio=4.0):
    """Apply person-only and aspect ratio filtering"""
    filtered_boxes = []
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls[0])
            
            # Only person class (0)
            if class_id != 0:
                continue
            
            # Aspect ratio filtering
            if aspect_filter:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                width = x2 - x1
                height = y2 - y1
                aspect_ratio = height / (width + 1e-6)
                
                if aspect_ratio < min_ratio or aspect_ratio > max_ratio:
                    continue
            
            filtered_boxes.append(box)
    
    return filtered_boxes

def test_confidence_levels(model_name, video_path, test_frames=10):
    """Test model with different confidence thresholds"""
    print(f"\n{'='*60}")
    print(f"Testing {model_name} with various confidence levels")
    print(f"{'='*60}")
    
    # Load model
    model = YOLO(model_name)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    
    # Read test frames
    frames = []
    for i in range(test_frames):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    
    print(f"Loaded {len(frames)} frames from {video_path.name}")
    
    # Test different confidence thresholds
    confidence_levels = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    results_table = []
    
    for conf in confidence_levels:
        total_detections = 0
        
        for frame in frames:
            results = model(
                frame,
                conf=conf,
                iou=0.45,
                device=device,
                verbose=False
            )
            
            filtered_boxes = filter_detections(results, aspect_filter=True)
            total_detections += len(filtered_boxes)
        
        avg_detections = total_detections / len(frames)
        results_table.append({
            'confidence': conf,
            'avg_detections': avg_detections
        })
        
        print(f"  Conf={conf:.2f}: Avg {avg_detections:.1f} people/frame")
    
    return results_table


def main():
    """Run confidence threshold tests"""
    print("=" * 60)
    print("CONFIDENCE THRESHOLD OPTIMIZATION")
    print("=" * 60)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Test YOLOv8m
    print("\n1. YOLOv8m:")
    v8_results = test_confidence_levels("yolov8m.pt", video_path, test_frames=10)
    
    # Test YOLOv11m
    print("\n2. YOLOv11m:")
    v11m_results = test_confidence_levels("yolo11m.pt", video_path, test_frames=10)
    
    # Test YOLOv11x
    print("\n3. YOLOv11x:")
    v11x_results = test_confidence_levels("yolo11x.pt", video_path, test_frames=10)
    
    # Find best configurations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    
    # Find max detections for each model
    v8_max = max(v8_results, key=lambda x: x['avg_detections'])
    v11m_max = max(v11m_results, key=lambda x: x['avg_detections'])
    v11x_max = max(v11x_results, key=lambda x: x['avg_detections'])
    
    print(f"\nYOLOv8m:  Best at conf={v8_max['confidence']:.2f} with {v8_max['avg_detections']:.1f} people/frame")
    print(f"YOLOv11m: Best at conf={v11m_max['confidence']:.2f} with {v11m_max['avg_detections']:.1f} people/frame")
    print(f"YOLOv11x: Best at conf={v11x_max['confidence']:.2f} with {v11x_max['avg_detections']:.1f} people/frame")
    
    # Find overall best
    all_results = [
        ('yolov8m.pt', v8_max),
        ('yolo11m.pt', v11m_max),
        ('yolo11x.pt', v11x_max)
    ]
    best_model, best_config = max(all_results, key=lambda x: x[1]['avg_detections'])
    
    print(f"\n✅ BEST CONFIGURATION:")
    print(f"   Model: {best_model}")
    print(f"   Confidence: {best_config['confidence']:.2f}")
    print(f"   Average detections: {best_config['avg_detections']:.1f} people/frame")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
