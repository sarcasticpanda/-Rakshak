"""
Test YOLOv8m with OPTIMIZED settings for detecting 400-500 people
Settings: max_det=1000, imgsz=1280, conf=0.05, iou=0.70
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


def test_optimized_settings():
    """Test with optimized settings for 400-500 people detection"""
    print("=" * 70)
    print("YOLOv8m OPTIMIZED FOR 400-500 PEOPLE DETECTION")
    print("=" * 70)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Load model
    print("\nLoading YOLOv8m...")
    model = YOLO("yolov8m.pt")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device.upper()}")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {video_path.name}")
    print(f"Resolution: {width}x{height}, FPS: {fps}")
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "optimized_detection"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare output video
    output_path = output_dir / "yolov8m_optimized_400plus.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    print("\n" + "=" * 70)
    print("OPTIMIZED SETTINGS (aiming for 400-500 people):")
    print("=" * 70)
    print("  max_det:     1000  (default 300 is too low)")
    print("  imgsz:       1280  (default 640 is too small)")
    print("  conf:        0.05  (very low for maximum detection)")
    print("  iou:         0.70  (less aggressive NMS suppression)")
    print("  half:        True  (FP16 for faster inference)")
    print("  aspect_filter: True  (reject vehicles)")
    print("=" * 70)
    
    # Process frames
    frame_count = 0
    total_detections = 0
    inference_times = []
    detection_counts = []
    
    print("\nProcessing 50 frames...")
    
    for i in range(50):
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run detection with optimized settings
        import time
        start = time.time()
        results = model(
            frame,
            conf=0.05,      # Very low confidence
            iou=0.70,       # Less NMS suppression
            max_det=1000,   # Allow many detections
            imgsz=1280,     # Larger input size
            half=True,      # FP16
            device=device,
            verbose=False
        )
        inference_time = (time.time() - start) * 1000
        inference_times.append(inference_time)
        
        # Filter detections
        filtered_boxes = filter_detections(results, aspect_filter=True)
        num_detections = len(filtered_boxes)
        total_detections += num_detections
        detection_counts.append(num_detections)
        
        # Annotate frame
        annotated_frame = frame.copy()
        for box in filtered_boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cv2.rectangle(
                annotated_frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2
            )
        
        # Add overlay
        cv2.putText(
            annotated_frame,
            f"YOLOv8m OPTIMIZED",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 255),
            3
        )
        cv2.putText(
            annotated_frame,
            f"People Detected: {num_detections}",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0) if num_detections >= 100 else (0, 165, 255),
            3
        )
        cv2.putText(
            annotated_frame,
            f"Frame: {i+1}/50",
            (10, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )
        cv2.putText(
            annotated_frame,
            f"Inference: {inference_time:.1f}ms",
            (10, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2
        )
        
        out.write(annotated_frame)
        frame_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"  Frame {i+1}: {num_detections} people detected")
    
    cap.release()
    out.release()
    
    # Calculate statistics
    avg_detections = total_detections / frame_count if frame_count > 0 else 0
    max_detections = max(detection_counts) if detection_counts else 0
    min_detections = min(detection_counts) if detection_counts else 0
    avg_inference = np.mean(inference_times) if inference_times else 0
    fps_real = 1000 / avg_inference if avg_inference > 0 else 0
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\n  Average detections:  {avg_detections:.1f} people/frame")
    print(f"  Maximum detections:  {max_detections} people (single frame)")
    print(f"  Minimum detections:  {min_detections} people (single frame)")
    print(f"  Average inference:   {avg_inference:.1f}ms")
    print(f"  Real-time FPS:       {fps_real:.1f}")
    print(f"\n  Output saved: {output_path}")
    
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    if avg_detections >= 400:
        print("\n  ✅ SUCCESS! Detecting 400+ people per frame")
        print("     Settings are optimal for high-density crowds")
    elif avg_detections >= 200:
        print("\n  ⚠️  PARTIAL: Detecting 200+ people per frame")
        print("     May need to lower confidence further or check video quality")
    elif avg_detections >= 100:
        print("\n  ⚠️  MODERATE: Detecting 100+ people per frame")
        print("     Video may not have 400-500 visible people")
        print("     Or people are too small/occluded")
    else:
        print("\n  ⚠️  LOW: Detecting <100 people per frame")
        print("     Possible issues:")
        print("       - Video doesn't contain 400-500 people")
        print("       - People are extremely small (aerial/wide-angle shot)")
        print("       - Heavy occlusion in dense crowd")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    
    if avg_detections < 400:
        print("\n  To increase detections further:")
        print("    1. Lower conf threshold: Try 0.03 or 0.02")
        print("    2. Disable aspect ratio filter temporarily")
        print("    3. Increase imgsz to 1920 (if GPU memory allows)")
        print("    4. Verify video actually contains 400-500 people")
        print("    5. Check if people are too small (aerial/wide shots)")
    else:
        print("\n  ✅ Ready to proceed to Phase 3: ByteTrack Tracking!")
    
    print("\n" + "=" * 70)
    
    return {
        'avg': avg_detections,
        'max': max_detections,
        'min': min_detections,
        'inference_ms': avg_inference
    }


if __name__ == "__main__":
    test_optimized_settings()
