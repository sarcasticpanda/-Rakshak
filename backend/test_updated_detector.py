"""
Test the updated detector.py with ULTRA settings
"""

import sys
sys.path.insert(0, str(__file__).replace('test_updated_detector.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
import time

def main():
    print("=" * 70)
    print("TESTING UPDATED DETECTOR WITH ULTRA SETTINGS")
    print("=" * 70)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    # Initialize detector
    print("\nInitializing detector...")
    detector = PersonDetector()
    print(f"✅ Detector loaded")
    print(f"   Model: {detector.model}")
    print(f"   Conf threshold: {detector.conf_threshold}")
    print(f"   IoU threshold: {detector.iou_threshold}")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"\nVideo: {video_path.name}")
    print(f"Resolution: {width}x{height}, FPS: {fps}")
    
    # Output
    output_dir = Path(__file__).parent / "output" / "ultra_detector"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "ultra_detector_test.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Process frames
    print("\nProcessing 50 frames...")
    total_detections = 0
    frame_count = 0
    inference_times = []
    
    for i in range(50):
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect
        start = time.time()
        detections = detector.detect(frame)
        inference_time = (time.time() - start) * 1000
        inference_times.append(inference_time)
        
        num_detections = len(detections)
        total_detections += num_detections
        
        # Annotate
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        # Overlay
        cv2.putText(annotated, f"ULTRA DETECTOR", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        cv2.putText(annotated, f"People: {num_detections}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(annotated, f"Frame: {i+1}/50", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(annotated)
        frame_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"  Frame {i+1}: {num_detections} people")
    
    cap.release()
    out.release()
    
    # Stats
    import numpy as np
    avg_detections = total_detections / frame_count
    avg_inference = np.mean(inference_times)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\n  Average detections: {avg_detections:.1f} people/frame")
    print(f"  Average inference:  {avg_inference:.1f}ms")
    print(f"  Output: {output_path}")
    
    if avg_detections >= 150:
        print("\n  ✅ EXCELLENT! Detecting 150+ people per frame")
        print("     Ultra settings are working!")
    elif avg_detections >= 100:
        print("\n  ✅ GOOD! Detecting 100+ people per frame")
    else:
        print("\n  ⚠️  Video may not contain that many people")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
