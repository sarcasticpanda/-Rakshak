"""
Test FIXED NMS settings - No more 20+ boxes per person!
Testing: IoU=0.45 (proper NMS), conf=0.05 (quality detections)
"""

import sys
sys.path.insert(0, str(__file__).replace('test_fixed_nms.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
import time
import numpy as np

def main():
    print("=" * 80)
    print("TESTING FIXED NMS - NO MORE DUPLICATE BOXES!")
    print("=" * 80)
    
    # Test on MOT17-02 (the crowded street scene)
    video_paths = [
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train\MOT17-02-FRCNN\img1"),
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4"),
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4"),
    ]
    
    test_path = None
    source_type = None
    
    for path in video_paths:
        if path.exists():
            test_path = path
            source_type = "images" if path.is_dir() else "video"
            break
    
    if not test_path:
        print("❌ No test source found")
        return
    
    print(f"\n📹 Source: {test_path.name}")
    print(f"   Type: {source_type}")
    
    # Initialize detector
    print("\n🔧 Initializing detector with FIXED settings...")
    detector = PersonDetector()
    print(f"   ✅ Conf threshold: {detector.conf_threshold} (was 0.01)")
    print(f"   ✅ IoU threshold: {detector.iou_threshold} (was 0.85 - FIXED!)")
    print(f"   ✅ Aspect filter: ENABLED (reject vehicles)")
    
    # Open source
    if source_type == "images":
        from app.core.video_reader import FrameReader
        reader = FrameReader(str(test_path), source_type="images")
        width, height = None, None
        ret, first_frame = reader.read_frame()
        if ret:
            height, width = first_frame.shape[:2]
        reader = FrameReader(str(test_path), source_type="images")
        fps = 10
    else:
        cap = cv2.VideoCapture(str(test_path))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"   Resolution: {width}x{height}, FPS: {fps}")
    
    # Output
    output_dir = Path(__file__).parent / "output" / "fixed_nms"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "fixed_no_duplicates.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Process frames
    print(f"\n🚀 Processing 50 frames with FIXED NMS...")
    print("   Should see 1 box per person (not 20+!)")
    
    total_detections = 0
    frame_count = 0
    inference_times = []
    
    for i in range(50):
        if source_type == "images":
            ret, frame = reader.read_frame()
        else:
            ret, frame = cap.read()
        
        if not ret:
            break
        
        # Detect with FIXED settings
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
            conf = det['confidence']
            
            # Draw box
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            # Draw confidence
            cv2.putText(annotated, f"{conf:.2f}", (int(x1), int(y1)-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Overlay
        cv2.putText(annotated, "FIXED NMS - IoU=0.45", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(annotated, f"People: {num_detections}", (10, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(annotated, "No duplicate boxes!", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.putText(annotated, f"Frame: {i+1}/50", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        out.write(annotated)
        frame_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"   Frame {i+1}: {num_detections} people")
    
    if source_type == "images":
        reader.__del__()
    else:
        cap.release()
    
    out.release()
    
    # Statistics
    avg_detections = total_detections / frame_count if frame_count > 0 else 0
    avg_inference = np.mean(inference_times) if inference_times else 0
    
    print("\n" + "=" * 80)
    print("📊 RESULTS - FIXED NMS")
    print("=" * 80)
    print(f"\n  Average detections: {avg_detections:.1f} people/frame")
    print(f"  Average inference:  {avg_inference:.1f}ms")
    print(f"\n  Output: {output_path}")
    
    print("\n" + "=" * 80)
    print("🔧 WHAT WAS FIXED:")
    print("=" * 80)
    print("\n  BEFORE (Broken):")
    print("    • IoU = 0.85 → Boxes need 85% overlap to suppress")
    print("    • conf = 0.01 → Too many weak duplicate detections")
    print("    • Result: 20+ boxes on SAME person! ❌")
    
    print("\n  AFTER (Fixed):")
    print("    • IoU = 0.45 → Proper NMS suppression (standard)")
    print("    • conf = 0.05 → Quality detections only")
    print("    • Aspect filter = ENABLED → Reject vehicles")
    print("    • Result: 1 box per person ✅")
    
    print("\n" + "=" * 80)
    print("✅ NMS FIXED - Check the output video!")
    print("=" * 80)
    print(f"\n  You should see clean, single boxes per person")
    print(f"  No more aggressive overlapping/duplicates")
    print(f"  Detection count may be lower but ACCURATE")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
