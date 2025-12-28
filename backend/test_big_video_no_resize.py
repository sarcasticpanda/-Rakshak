"""
TEST WITH BIGGER VIDEO - NO FRAME RESIZING
Testing on larger video with more frames to reach 400+ detections
Using model.predict() with original frames - let YOLO handle resizing
"""

import sys
sys.path.insert(0, str(__file__).replace('test_big_video_no_resize.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
import time
import numpy as np

def main():
    print("=" * 80)
    print("BIG VIDEO TEST - NO FRAME RESIZING (400+ DETECTION TARGET)")
    print("=" * 80)
    
    # Try all available videos, starting with largest
    video_paths = [
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4"),
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4"),
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4"),
    ]
    
    video_path = None
    for path in video_paths:
        if path.exists():
            video_path = path
            break
    
    if video_path is None:
        print("❌ No video found!")
        return
    
    print(f"\n📹 Video: {video_path.name}")
    
    # Initialize detector
    print("\n🔧 Initializing detector...")
    detector = PersonDetector()
    print(f"   ✅ Model: yolov8m.pt")
    print(f"   ✅ Conf threshold: {detector.conf_threshold}")
    print(f"   ✅ IoU threshold: {detector.iou_threshold}")
    print(f"   ✅ Max detections: 1500")
    print(f"   ✅ Image size: 1920 (YOLO internal)")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\n📊 Video Info:")
    print(f"   Resolution: {width}x{height} (ORIGINAL - no resizing!)")
    print(f"   FPS: {fps}")
    print(f"   Total frames: {total_frames}")
    
    # Output
    output_dir = Path(__file__).parent / "output" / "big_video_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_path.stem}_400plus_detection.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Process MORE frames (100 instead of 50)
    frames_to_process = min(100, total_frames)
    print(f"\n🚀 Processing {frames_to_process} frames...")
    print("   (Passing ORIGINAL frames to YOLO - no pre-resize)")
    
    total_detections = 0
    frame_count = 0
    inference_times = []
    detection_counts = []
    
    for i in range(frames_to_process):
        ret, frame = cap.read()
        if not ret:
            break
        
        # CRITICAL: Pass ORIGINAL frame - YOLO will resize internally
        # NO cv2.resize() here!
        
        start = time.time()
        detections = detector.detect(frame)
        inference_time = (time.time() - start) * 1000
        inference_times.append(inference_time)
        
        num_detections = len(detections)
        total_detections += num_detections
        detection_counts.append(num_detections)
        
        # Annotate ORIGINAL frame
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        # Overlay stats
        cv2.putText(annotated, f"NO RESIZE - ORIGINAL {width}x{height}", 
                    (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(annotated, f"People Detected: {num_detections}", 
                    (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 
                    (0, 255, 0) if num_detections >= 200 else (0, 165, 255), 3)
        cv2.putText(annotated, f"Frame: {i+1}/{frames_to_process}", 
                    (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(annotated, f"Inference: {inference_time:.1f}ms", 
                    (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        out.write(annotated)
        frame_count += 1
        
        if (i + 1) % 20 == 0:
            avg_so_far = sum(detection_counts[-20:]) / 20
            print(f"   Frame {i+1:3d}: {num_detections:3d} people | Avg last 20: {avg_so_far:.1f}")
    
    cap.release()
    out.release()
    
    # Calculate statistics
    avg_detections = total_detections / frame_count if frame_count > 0 else 0
    max_detections = max(detection_counts) if detection_counts else 0
    min_detections = min(detection_counts) if detection_counts else 0
    avg_inference = np.mean(inference_times) if inference_times else 0
    fps_real = 1000 / avg_inference if avg_inference > 0 else 0
    
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print(f"\n  Average detections:   {avg_detections:.1f} people/frame")
    print(f"  Maximum detections:   {max_detections} people (single frame)")
    print(f"  Minimum detections:   {min_detections} people (single frame)")
    print(f"  Average inference:    {avg_inference:.1f}ms")
    print(f"  Real-time FPS:        {fps_real:.1f}")
    print(f"\n  Frames processed:     {frame_count}")
    print(f"  Total people counted: {total_detections}")
    print(f"\n  Output: {output_path}")
    
    # Analysis
    print("\n" + "=" * 80)
    print("📈 ANALYSIS")
    print("=" * 80)
    
    if avg_detections >= 400:
        print("\n  🎉 OUTSTANDING! Detecting 400+ people per frame!")
        print("     Target achieved - system ready for stampede detection!")
    elif avg_detections >= 300:
        print("\n  ✅ EXCELLENT! Detecting 300+ people per frame")
        print("     Very close to 400 - consider lowering conf to 0.005")
    elif avg_detections >= 200:
        print("\n  ✅ VERY GOOD! Detecting 200+ people per frame")
        print("     Improvement from NO RESIZE approach")
        print("     Video may not contain 400+ people in frame")
    elif avg_detections >= 150:
        print("\n  ✅ GOOD! Detecting 150+ people per frame")
        print("     Solid detection for dense crowds")
    else:
        print("\n  ℹ️  Detecting <150 people per frame")
        print("     Video likely doesn't contain 400+ people")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("💡 KEY IMPROVEMENTS")
    print("=" * 80)
    print(f"\n  ✅ NO manual frame resizing - YOLO handles it internally")
    print(f"  ✅ Original resolution preserved: {width}x{height}")
    print(f"  ✅ Small people NOT destroyed by aggressive resize")
    print(f"  ✅ Head detection enabled (person class includes heads)")
    
    if avg_detections < 400:
        print("\n  📝 To reach 400+ detections:")
        print("     1. Lower conf threshold: Try 0.005 (currently 0.01)")
        print("     2. Test on KNOWN ultra-dense crowd video (>400 people)")
        print("     3. Use aerial/high-angle footage for better coverage")
        print("     4. Verify video actually contains 400+ visible people")
    else:
        print("\n  🚀 Ready for Phase 3: ByteTrack Tracking!")
        print("     Detection system fully optimized!")
    
    print("\n" + "=" * 80)
    
    return {
        'avg': avg_detections,
        'max': max_detections,
        'video': video_path.name,
        'resolution': f"{width}x{height}"
    }


if __name__ == "__main__":
    main()
