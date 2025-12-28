"""
Comprehensive confidence threshold sweep for YOLOv8m vs YOLOv11m vs YOLOv11x
Testing more threshold values to find optimal configuration
"""

import cv2
import torch
from ultralytics import YOLO
from pathlib import Path
import numpy as np

def filter_detections(results, aspect_filter=True):
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
                
                if aspect_ratio < 0.3 or aspect_ratio > 4.0:
                    continue
            
            filtered_boxes.append(box)
    
    return filtered_boxes

def test_model_comprehensive(model_name, frames):
    """Test a model with comprehensive confidence thresholds"""
    print(f"\n{'='*60}")
    print(f"Testing {model_name}")
    print(f"{'='*60}")
    
    model = YOLO(model_name)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # More granular confidence levels
    confidence_levels = [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.35, 0.40]
    
    results_list = []
    
    for conf in confidence_levels:
        total_detections = 0
        inference_times = []
        
        for frame in frames:
            import time
            start = time.time()
            results = model(
                frame,
                conf=conf,
                iou=0.45,
                device=device,
                verbose=False
            )
            inference_time = (time.time() - start) * 1000
            inference_times.append(inference_time)
            
            filtered_boxes = filter_detections(results)
            total_detections += len(filtered_boxes)
        
        avg_detections = total_detections / len(frames)
        avg_inference = np.mean(inference_times)
        
        results_list.append({
            'conf': conf,
            'detections': avg_detections,
            'inference_ms': avg_inference
        })
        
        print(f"  conf={conf:.2f}: {avg_detections:>5.1f} people/frame, {avg_inference:>6.1f}ms")
    
    return results_list


def main():
    """Run comprehensive comparison"""
    print("=" * 60)
    print("COMPREHENSIVE YOLOv8 vs YOLOv11 THRESHOLD SWEEP")
    print("=" * 60)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Load 20 frames for faster testing
    print(f"\nLoading 20 frames from {video_path.name}...")
    cap = cv2.VideoCapture(str(video_path))
    frames = []
    for i in range(20):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    print(f"✅ Loaded {len(frames)} frames\n")
    
    # Test all models
    v8m_results = test_model_comprehensive("yolov8m.pt", frames)
    v11m_results = test_model_comprehensive("yolo11m.pt", frames)
    v11x_results = test_model_comprehensive("yolo11x.pt", frames)
    
    # Find best configuration for each model
    v8m_best = max(v8m_results, key=lambda x: x['detections'])
    v11m_best = max(v11m_results, key=lambda x: x['detections'])
    v11x_best = max(v11x_results, key=lambda x: x['detections'])
    
    # Print comparison table
    print("\n" + "=" * 60)
    print("BEST CONFIGURATIONS")
    print("=" * 60)
    print(f"\n{'Model':<15} {'Best Conf':<12} {'Detections':<15} {'Inference':<12}")
    print("-" * 54)
    print(f"{'YOLOv8m':<15} {v8m_best['conf']:<12.2f} {v8m_best['detections']:<15.1f} {v8m_best['inference_ms']:<12.1f}")
    print(f"{'YOLOv11m':<15} {v11m_best['conf']:<12.2f} {v11m_best['detections']:<15.1f} {v11m_best['inference_ms']:<12.1f}")
    print(f"{'YOLOv11x':<15} {v11x_best['conf']:<12.2f} {v11x_best['detections']:<15.1f} {v11x_best['inference_ms']:<12.1f}")
    
    # Overall best
    all_best = [
        ('yolov8m.pt', v8m_best),
        ('yolo11m.pt', v11m_best),
        ('yolo11x.pt', v11x_best)
    ]
    overall_best = max(all_best, key=lambda x: x[1]['detections'])
    
    print("\n" + "=" * 60)
    print("OVERALL WINNER")
    print("=" * 60)
    print(f"\n✅ {overall_best[0]}")
    print(f"   Confidence: {overall_best[1]['conf']:.2f}")
    print(f"   Detections: {overall_best[1]['detections']:.1f} people/frame")
    print(f"   Inference: {overall_best[1]['inference_ms']:.1f}ms")
    
    # Check if YOLOv11 can match YOLOv8m at any threshold
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    
    v8m_max = v8m_best['detections']
    v11m_max = v11m_best['detections']
    v11x_max = v11x_best['detections']
    
    print(f"\nYOLOv8m max:  {v8m_max:.1f} people/frame @ conf={v8m_best['conf']:.2f}")
    print(f"YOLOv11m max: {v11m_max:.1f} people/frame @ conf={v11m_best['conf']:.2f}")
    print(f"YOLOv11x max: {v11x_max:.1f} people/frame @ conf={v11x_best['conf']:.2f}")
    
    v11m_diff = ((v8m_max - v11m_max) / v11m_max * 100)
    v11x_diff = ((v8m_max - v11x_max) / v11x_max * 100)
    
    print(f"\nYOLOv8m detects {v11m_diff:+.1f}% more people than YOLOv11m")
    print(f"YOLOv8m detects {v11x_diff:+.1f}% more people than YOLOv11x")
    
    # Recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION FOR STAMPEDE DETECTION")
    print("=" * 60)
    
    if overall_best[0] == 'yolov8m.pt':
        print("\n✅ Use YOLOv8m")
        print(f"   Config: YOLO_MODEL = 'yolov8m.pt'")
        print(f"   Config: YOLO_CONF_THRESHOLD = {v8m_best['conf']:.2f}")
        print(f"\n   Reason: Highest detection rate ({v8m_max:.1f} people/frame)")
        print(f"   - Best for safety-critical stampede detection (high recall)")
        print(f"   - Detects {v11m_diff:.1f}% more people than YOLOv11m")
    else:
        print(f"\n✅ Use {overall_best[0]}")
        print(f"   Config: YOLO_MODEL = '{overall_best[0]}'")
        print(f"   Config: YOLO_CONF_THRESHOLD = {overall_best[1]['conf']:.2f}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
