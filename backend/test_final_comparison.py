"""
Final visual comparison: YOLOv8m vs YOLOv11m at conf=0.10
Create side-by-side comparison video
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

def annotate_frame(frame, boxes, model_name, detection_count, color):
    """Draw boxes and stats on frame"""
    annotated = frame.copy()
    
    # Draw bounding boxes
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0])
        
        cv2.rectangle(
            annotated,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            color,
            2
        )
    
    # Add model name and count overlay
    cv2.putText(
        annotated,
        model_name,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        2
    )
    cv2.putText(
        annotated,
        f"People: {detection_count}",
        (10, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        2
    )
    
    return annotated


def main():
    """Create side-by-side comparison"""
    print("=" * 60)
    print("SIDE-BY-SIDE COMPARISON: YOLOv8m vs YOLOv11m")
    print("=" * 60)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    output_dir = Path(__file__).parent / "output" / "final_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load both models
    print("\nLoading models...")
    v8_model = YOLO("yolov8m.pt")
    v11_model = YOLO("yolo11m.pt")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device.upper()}")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Prepare output (side-by-side, so double width)
    output_path = output_dir / "yolov8m_vs_yolo11m_sidebyside.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width * 2, height))
    
    print(f"\nProcessing 50 frames from {video_path.name}...")
    
    v8_total = 0
    v11_total = 0
    frame_count = 0
    
    for i in range(50):
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run YOLOv8m
        v8_results = v8_model(
            frame,
            conf=0.10,
            iou=0.45,
            device=device,
            verbose=False
        )
        v8_boxes = filter_detections(v8_results)
        v8_count = len(v8_boxes)
        v8_total += v8_count
        
        # Run YOLOv11m
        v11_results = v11_model(
            frame,
            conf=0.10,
            iou=0.45,
            device=device,
            verbose=False
        )
        v11_boxes = filter_detections(v11_results)
        v11_count = len(v11_boxes)
        v11_total += v11_count
        
        # Annotate frames
        v8_frame = annotate_frame(frame, v8_boxes, "YOLOv8m (conf=0.10)", v8_count, (0, 255, 0))  # Green
        v11_frame = annotate_frame(frame, v11_boxes, "YOLOv11m (conf=0.10)", v11_count, (0, 165, 255))  # Orange
        
        # Combine side-by-side
        combined = np.hstack([v8_frame, v11_frame])
        
        # Add divider line
        cv2.line(combined, (width, 0), (width, height), (255, 255, 255), 3)
        
        # Add frame number
        cv2.putText(
            combined,
            f"Frame: {i+1}/50",
            (width - 200, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        out.write(combined)
        frame_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/50 frames...")
    
    cap.release()
    out.release()
    
    # Print results
    v8_avg = v8_total / frame_count if frame_count > 0 else 0
    v11_avg = v11_total / frame_count if frame_count > 0 else 0
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"\nYOLOv8m  (conf=0.10): {v8_avg:.1f} people/frame (GREEN boxes)")
    print(f"YOLOv11m (conf=0.10): {v11_avg:.1f} people/frame (ORANGE boxes)")
    print(f"\nDifference: {v8_avg - v11_avg:+.1f} people/frame ({(v8_avg - v11_avg) / v11_avg * 100:+.1f}%)")
    
    print(f"\n✅ Output saved: {output_path}")
    print("\nNOTE: Watch the video to see which model has:")
    print("  - Fewer false positives (vehicles, objects)")
    print("  - Better detection of small/distant people")
    print("  - More stable bounding boxes")
    
    print("\n" + "=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print("\nYOLOv8m detects MORE people, but may include:")
    print("  ✓ More small/distant people (good)")
    print("  ✗ More false positives (bad)")
    
    print("\nYOLOv11m detects FEWER people, but may have:")
    print("  ✓ Higher precision (fewer false positives)")
    print("  ✗ Missing some true people (lower recall)")
    
    print("\nFor stampede detection, you need to balance:")
    print("  - High recall (don't miss people) → YOLOv8m")
    print("  - High precision (no false alarms) → YOLOv11m")
    print("\n  RECOMMENDATION: Review video and decide based on your priority!")
    print("=" * 60)


if __name__ == "__main__":
    main()
