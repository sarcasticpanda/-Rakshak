"""
BALANCED TEST: Detect 200-400 people in dense crowds + clean in sparse
Goal: Maximize detection on dense crowds WITHOUT duplicates
"""

import sys
sys.path.insert(0, str(__file__).replace('test_balanced_detection.py', ''))

import cv2
from pathlib import Path
from ultralytics import YOLO
import time
import numpy as np

def test_balanced_detection():
    print("=" * 80)
    print("BALANCED DETECTION TEST")
    print("Goal: 200-400 people on dense crowds, clean detection on sparse")
    print("=" * 80)
    
    # Test videos
    test_videos = [
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4"), "Dense_Crowd_test_d1"),
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4"), "Dense_Crowd_test3"),
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4"), "Medium_Crowd_test2"),
    ]
    
    # Find available videos
    available_videos = [(p, n) for p, n in test_videos if p.exists()]
    print(f"\n✅ Found {len(available_videos)} test videos")
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "balanced_detection"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Results will be saved to: {output_dir}")
    
    # Load model
    print("\n🔧 Loading YOLOv8m...")
    model = YOLO("yolov8m.pt")
    model.to('cuda')
    
    # BALANCED SETTINGS - Lower conf to catch more people, keep proper NMS
    CONF = 0.03  # Lower than 0.05 to catch more distant/small people
    IOU = 0.45   # Standard NMS - prevents duplicate boxes
    
    # Aspect ratio filter for Indian crowds (reject vehicles)
    MIN_ASPECT = 0.3
    MAX_ASPECT = 4.0
    
    print(f"\n📊 Settings:")
    print(f"   Confidence: {CONF} (lower to catch more people)")
    print(f"   IoU/NMS: {IOU} (standard - prevents duplicates)")
    print(f"   Aspect Filter: {MIN_ASPECT} - {MAX_ASPECT}")
    print(f"   Max Detections: 1500")
    print(f"   Image Size: 1920")
    
    all_results = []
    
    for video_path, video_name in available_videos:
        print(f"\n{'='*80}")
        print(f"Testing: {video_name}")
        print(f"{'='*80}")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"❌ Failed to open {video_path}")
            continue
        
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"   Resolution: {width}x{height}, FPS: {fps}, Total: {total_frames}")
        
        # Output video
        output_path = output_dir / f"{video_name}_balanced.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        # Process frames
        detection_counts = []
        frames_to_test = min(50, total_frames)
        
        for i in range(frames_to_test):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect with balanced settings
            results = model.predict(
                source=frame,
                conf=CONF,
                iou=IOU,
                classes=[0],      # Person only
                max_det=1500,
                imgsz=1920,
                half=True,
                verbose=False
            )
            
            # Parse and filter results
            detections = []
            for result in results:
                boxes = result.boxes
                for j in range(len(boxes)):
                    box = boxes.xyxy[j].cpu().numpy()
                    conf_score = float(boxes.conf[j].cpu().numpy())
                    
                    # Aspect ratio filter
                    x1, y1, x2, y2 = box
                    w = x2 - x1
                    h = y2 - y1
                    if w > 0 and h > 0:
                        aspect = h / w
                        if MIN_ASPECT <= aspect <= MAX_ASPECT:
                            detections.append({
                                'bbox': box,
                                'conf': conf_score
                            })
            
            num_det = len(detections)
            detection_counts.append(num_det)
            
            # Annotate frame
            annotated = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(annotated, f"{det['conf']:.2f}", (int(x1), int(y1)-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
            
            # Overlay info
            cv2.putText(annotated, f"{video_name}", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(annotated, f"People: {num_det}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(annotated, f"Conf={CONF} IoU={IOU} (Balanced)", (10, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            out.write(annotated)
            
            if (i + 1) % 10 == 0:
                print(f"   Frame {i+1}: {num_det} people")
        
        cap.release()
        out.release()
        
        # Stats
        avg_det = np.mean(detection_counts) if detection_counts else 0
        max_det = max(detection_counts) if detection_counts else 0
        min_det = min(detection_counts) if detection_counts else 0
        
        print(f"\n   Results for {video_name}:")
        print(f"   ├─ Average: {avg_det:.1f} people/frame")
        print(f"   ├─ Maximum: {max_det} people")
        print(f"   ├─ Minimum: {min_det} people")
        print(f"   └─ Output: {output_path.name}")
        
        all_results.append({
            'name': video_name,
            'avg': avg_det,
            'max': max_det,
            'min': min_det,
            'resolution': f"{width}x{height}"
        })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS SUMMARY")
    print("=" * 80)
    print(f"\n{'Video':<30} {'Avg Det':<12} {'Max Det':<10} {'Min Det':<10} {'Resolution'}")
    print("-" * 80)
    
    for r in all_results:
        print(f"{r['name']:<30} {r['avg']:<12.1f} {r['max']:<10} {r['min']:<10} {r['resolution']}")
    
    # Validation
    print("\n" + "=" * 80)
    print("✅ VALIDATION CHECK")
    print("=" * 80)
    
    dense_results = [r for r in all_results if 'Dense' in r['name']]
    medium_results = [r for r in all_results if 'Medium' in r['name']]
    
    if dense_results:
        avg_dense = sum(r['avg'] for r in dense_results) / len(dense_results)
        max_dense = max(r['max'] for r in dense_results)
        
        print(f"\n  🔥 Dense Crowd Performance:")
        print(f"     Average: {avg_dense:.1f} people/frame")
        print(f"     Maximum: {max_dense} people")
        
        if avg_dense >= 200:
            print(f"     ✅ EXCELLENT - Target 200-400 achieved!")
        elif avg_dense >= 150:
            print(f"     ⚠️  GOOD but below 200 target")
        elif avg_dense >= 100:
            print(f"     ⚠️  MODERATE - Try lower confidence")
        else:
            print(f"     ❌ LOW - Need further tuning")
    
    if medium_results:
        avg_medium = sum(r['avg'] for r in medium_results) / len(medium_results)
        print(f"\n  📊 Medium/Sparse Crowd Performance:")
        print(f"     Average: {avg_medium:.1f} people/frame")
        print(f"     ✅ Should have clean single boxes (watch video to verify)")
    
    print(f"\n  📁 OUTPUT LOCATION:")
    print(f"     {output_dir}")
    print(f"\n  📹 Videos to check:")
    for r in all_results:
        print(f"     • {r['name']}_balanced.mp4")
    
    print("\n  👁️ WATCH THE VIDEOS TO VERIFY:")
    print("     1. Dense crowds: Are 200-400 people detected?")
    print("     2. Each person has ONE box (no duplicates)")
    print("     3. Sparse crowds: Clean detection, no over-detection")
    print("     4. No vehicles/objects misclassified as people")
    print("=" * 80)


if __name__ == "__main__":
    test_balanced_detection()
