"""
Compare YOLOv8m vs YOLOv11m vs YOLOv11x on dense Indian crowd videos
Test all three models and compare detection quality
"""

import cv2
import torch
from ultralytics import YOLO
from pathlib import Path
import time
import numpy as np
from app.utils.config import (
    YOLO_CONF_THRESHOLD,
    YOLO_IOU_THRESHOLD,
    ENABLE_ASPECT_RATIO_FILTER,
    MIN_PERSON_ASPECT_RATIO,
    MAX_PERSON_ASPECT_RATIO
)

def filter_detections(results, enable_aspect_filter=True):
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
            if enable_aspect_filter:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                width = x2 - x1
                height = y2 - y1
                aspect_ratio = height / (width + 1e-6)
                
                if aspect_ratio < MIN_PERSON_ASPECT_RATIO or aspect_ratio > MAX_PERSON_ASPECT_RATIO:
                    continue
            
            filtered_boxes.append(box)
    
    return filtered_boxes

def test_model(model_name, video_path, output_path, test_frames=30):
    """Test a single model on video"""
    print(f"\n{'='*60}")
    print(f"Testing {model_name}")
    print(f"{'='*60}")
    
    # Load model
    print(f"Loading {model_name}...")
    model = YOLO(model_name)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device.upper()}")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video: {video_path.name}")
    print(f"Resolution: {width}x{height}, FPS: {fps}, Total frames: {total_frames}")
    
    # Prepare output video
    output_path.parent.mkdir(exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Statistics
    total_detections = 0
    frame_count = 0
    inference_times = []
    
    print(f"\nProcessing first {test_frames} frames...")
    
    for i in range(test_frames):
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run detection
        start_time = time.time()
        results = model(
            frame,
            conf=YOLO_CONF_THRESHOLD,
            iou=YOLO_IOU_THRESHOLD,
            device=device,
            verbose=False
        )
        inference_time = (time.time() - start_time) * 1000  # ms
        inference_times.append(inference_time)
        
        # Filter detections
        filtered_boxes = filter_detections(results, ENABLE_ASPECT_RATIO_FILTER)
        num_detections = len(filtered_boxes)
        total_detections += num_detections
        
        # Draw boxes
        annotated_frame = frame.copy()
        for box in filtered_boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            
            # Draw bounding box
            cv2.rectangle(
                annotated_frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),  # Green
                2
            )
            
            # Draw confidence
            label = f"{conf:.2f}"
            cv2.putText(
                annotated_frame,
                label,
                (int(x1), int(y1) - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
        
        # Add stats overlay
        cv2.putText(
            annotated_frame,
            f"Model: {model_name}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        cv2.putText(
            annotated_frame,
            f"Frame: {i+1}/{test_frames}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        cv2.putText(
            annotated_frame,
            f"People Detected: {num_detections}",
            (10, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        cv2.putText(
            annotated_frame,
            f"Inference: {inference_time:.1f}ms",
            (10, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )
        
        out.write(annotated_frame)
        frame_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{test_frames} frames...")
    
    cap.release()
    out.release()
    
    # Calculate stats
    avg_detections = total_detections / frame_count if frame_count > 0 else 0
    avg_inference = np.mean(inference_times) if inference_times else 0
    
    print(f"\n✅ Results for {model_name}:")
    print(f"   Average detections per frame: {avg_detections:.1f}")
    print(f"   Average inference time: {avg_inference:.1f}ms")
    print(f"   Output saved: {output_path}")
    
    return {
        'model': model_name,
        'avg_detections': avg_detections,
        'avg_inference_ms': avg_inference,
        'fps': 1000 / avg_inference if avg_inference > 0 else 0
    }


def main():
    """Run comparison test"""
    print("=" * 60)
    print("YOLOv8m vs YOLOv11m vs YOLOv11x COMPARISON")
    print("=" * 60)
    
    # Test video (densest crowd)
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "yolo_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test models
    models_to_test = [
        ("yolov8m.pt", output_dir / "yolov8m_test3.mp4"),
        ("yolo11m.pt", output_dir / "yolo11m_test3.mp4"),
        ("yolo11x.pt", output_dir / "yolo11x_test3.mp4"),
    ]
    
    results = []
    
    for model_name, output_path in models_to_test:
        try:
            result = test_model(model_name, video_path, output_path, test_frames=30)
            results.append(result)
        except Exception as e:
            print(f"❌ Error testing {model_name}: {e}")
            continue
    
    # Print comparison table
    print("\n" + "=" * 60)
    print("FINAL COMPARISON RESULTS")
    print("=" * 60)
    print(f"\n{'Model':<15} {'Avg Detections':<20} {'Avg Inference':<20} {'Real-time FPS':<15}")
    print("-" * 70)
    
    for result in results:
        print(f"{result['model']:<15} {result['avg_detections']:<20.1f} {result['avg_inference_ms']:<20.1f} {result['fps']:<15.1f}")
    
    print("\n" + "=" * 60)
    print("KEY FINDINGS:")
    print("=" * 60)
    
    if len(results) >= 3:
        v8_detections = results[0]['avg_detections']
        v11m_detections = results[1]['avg_detections']
        v11x_detections = results[2]['avg_detections']
        
        improvement_m = ((v11m_detections - v8_detections) / v8_detections * 100) if v8_detections > 0 else 0
        improvement_x = ((v11x_detections - v8_detections) / v8_detections * 100) if v8_detections > 0 else 0
        
        print(f"\nYOLOv11m vs YOLOv8m: {improvement_m:+.1f}% detection improvement")
        print(f"YOLOv11x vs YOLOv8m: {improvement_x:+.1f}% detection improvement")
        
        if v11x_detections > v11m_detections:
            print(f"\n✅ BEST: YOLOv11x detected {v11x_detections:.1f} people per frame")
        else:
            print(f"\n✅ BEST: YOLOv11m detected {v11m_detections:.1f} people per frame")
        
        print("\nRECOMMENDATION:")
        if results[2]['fps'] >= 15:  # YOLOv11x real-time capable
            print("  Use yolo11x.pt - Best accuracy, still real-time capable")
        else:
            print("  Use yolo11m.pt - Good balance of accuracy and speed")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
