"""
Test YOLOv8l (Large) and compare with YOLOv8m
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

def test_model(model_name, frames, conf_threshold=0.10):
    """Test a model on frames"""
    print(f"\nTesting {model_name} (conf={conf_threshold})...")
    
    model = YOLO(model_name)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    total_detections = 0
    inference_times = []
    
    for frame in frames:
        import time
        start = time.time()
        results = model(
            frame,
            conf=conf_threshold,
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
    fps = 1000 / avg_inference if avg_inference > 0 else 0
    
    print(f"  ✅ Avg detections: {avg_detections:.1f} people/frame")
    print(f"  ⏱️  Avg inference: {avg_inference:.1f}ms ({fps:.1f} FPS)")
    
    return {
        'model': model_name,
        'avg_detections': avg_detections,
        'avg_inference_ms': avg_inference,
        'fps': fps
    }


def main():
    """Test YOLOv8l and compare"""
    print("=" * 60)
    print("YOLOv8l (Large) Testing")
    print("=" * 60)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Load 20 frames
    print(f"\nLoading frames from {video_path.name}...")
    cap = cv2.VideoCapture(str(video_path))
    frames = []
    for i in range(20):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    print(f"Loaded {len(frames)} frames")
    
    # Test YOLOv8 models at conf=0.10
    results = []
    
    # Test yolov8m (baseline)
    results.append(test_model("yolov8m.pt", frames, conf_threshold=0.10))
    
    # Test yolov8l (larger)
    results.append(test_model("yolov8l.pt", frames, conf_threshold=0.10))
    
    # Test yolov8x (extra large)
    results.append(test_model("yolov8x.pt", frames, conf_threshold=0.10))
    
    # Print comparison
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS (conf=0.10)")
    print("=" * 60)
    print(f"\n{'Model':<15} {'Detections':<15} {'Inference':<15} {'FPS':<10}")
    print("-" * 55)
    
    for result in results:
        print(f"{result['model']:<15} {result['avg_detections']:<15.1f} {result['avg_inference_ms']:<15.1f} {result['fps']:<10.1f}")
    
    # Find best
    best = max(results, key=lambda x: x['avg_detections'])
    
    print("\n" + "=" * 60)
    print(f"✅ BEST: {best['model']} with {best['avg_detections']:.1f} people/frame")
    print("=" * 60)
    
    # Check if real-time capable
    if best['fps'] >= 15:
        print(f"\n✓ {best['model']} is REAL-TIME capable ({best['fps']:.1f} FPS)")
    else:
        print(f"\n⚠ {best['model']} may struggle with real-time ({best['fps']:.1f} FPS)")
    
    print("\nRECOMMENDATION:")
    if best['model'] == 'yolov8x.pt' and best['fps'] < 15:
        print("  Use yolov8l.pt - Better balance of accuracy and speed")
    else:
        print(f"  Use {best['model']} for best detection performance")


if __name__ == "__main__":
    main()
