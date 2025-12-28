"""
Test detection quality on MOT17 and test3.mp4
Check if we're detecting enough people or missing too many
"""
import sys
sys.path.insert(0, str(__file__).replace('test_detection_quality.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker
import numpy as np

def main():
    print("=" * 70)
    print("DETECTION QUALITY TEST")
    print("Checking if we're detecting enough people")
    print("=" * 70)
    
    # Test videos
    test_videos = [
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4"), "Indian_test3"),
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train\MOT17-04-FRCNN\img1"), "MOT17-04_Dense"),
    ]
    
    output_dir = Path(__file__).parent / "output" / "detection_quality"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Output: {output_dir}")
    print("\n🔧 Loading detector...")
    detector = PersonDetector()
    
    # Show current settings
    print(f"\n📊 Current Settings:")
    print(f"   Confidence: {detector.conf_threshold}")
    print(f"   IoU/NMS: {detector.iou_threshold}")
    
    for path, name in test_videos:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        tracker = ByteTracker(track_thresh=0.3, track_buffer=15, match_thresh=0.4, min_hits=3, max_age=10)
        
        # Check if video or image sequence
        is_video = path.suffix == '.mp4'
        
        if is_video:
            if not path.exists():
                print(f"   ❌ Video not found: {path}")
                continue
            cap = cv2.VideoCapture(str(path))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frames_source = "video"
        else:
            if not path.exists():
                print(f"   ❌ Path not found: {path}")
                continue
            img_files = sorted(path.glob("*.jpg"))
            if not img_files:
                print(f"   ❌ No images found")
                continue
            first_img = cv2.imread(str(img_files[0]))
            height, width = first_img.shape[:2]
            fps = 10
            total = len(img_files)
            frames_source = "images"
        
        print(f"   Resolution: {width}x{height}, Frames: {total}")
        
        # Output video
        output_path = output_dir / f"{name}_quality.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames_to_process = min(100, total)
        det_counts = []
        track_counts = []
        
        for i in range(frames_to_process):
            if is_video:
                ret, frame = cap.read()
                if not ret:
                    break
            else:
                if i >= len(img_files):
                    break
                frame = cv2.imread(str(img_files[i]))
                if frame is None:
                    continue
            
            # Detect
            detections = detector.detect(frame)
            
            # Track
            tracks = tracker.update(detections, frame_size=(width, height))
            
            det_counts.append(len(detections))
            track_counts.append(len(tracks))
            
            # Draw detections (green) and show count
            annotated = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = map(int, det['bbox'])
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Large count display
            cv2.putText(annotated, f"{name}", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(annotated, f"DETECTED: {len(detections)}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            cv2.putText(annotated, f"Frame {i+1}/{frames_to_process}", (10, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            out.write(annotated)
            
            if (i+1) % 20 == 0:
                print(f"   Frame {i+1}: {len(detections)} detected")
        
        if is_video:
            cap.release()
        out.release()
        
        avg_det = np.mean(det_counts)
        max_det = max(det_counts)
        min_det = min(det_counts)
        
        print(f"\n   📊 RESULTS for {name}:")
        print(f"   ├─ Average: {avg_det:.1f} people/frame")
        print(f"   ├─ Maximum: {max_det} people")
        print(f"   ├─ Minimum: {min_det} people")
        print(f"   └─ Saved: {output_path.name}")
        
        # Assessment
        if "MOT17" in name:
            if avg_det >= 40:
                print(f"   ✅ GOOD - MOT17 detection looks healthy")
            else:
                print(f"   ⚠️  LOW - May be missing people")
        else:
            if avg_det >= 60:
                print(f"   ✅ GOOD - Dense crowd detection")
            elif avg_det >= 40:
                print(f"   ⚠️  MODERATE - Could detect more")
            else:
                print(f"   ❌ LOW - Definitely missing people")
    
    print("\n" + "=" * 70)
    print("📁 Videos saved to:", output_dir)
    print("=" * 70)
    print("\nWatch the videos to see:")
    print("  1. Are visible people getting green boxes?")
    print("  2. How many people are being missed?")
    print("  3. Are the boxes the right size?")
    print("=" * 70)


if __name__ == "__main__":
    main()
