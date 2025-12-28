"""
AGGRESSIVE DETECTION TEST - Target 200-400 people on dense crowds
Test multiple confidence thresholds to find optimal setting
"""

import sys
sys.path.insert(0, str(__file__).replace('test_optimal_detection.py', ''))

import cv2
from pathlib import Path
from ultralytics import YOLO
import numpy as np

def test_conf_sweep():
    print("=" * 80)
    print("CONFIDENCE SWEEP TEST - Find optimal setting for 200-400 people")
    print("=" * 80)
    
    # Test video - dense crowd
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Load model
    print("\n🔧 Loading YOLOv8m...")
    model = YOLO("yolov8m.pt")
    model.to('cuda')
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "conf_sweep"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test different confidence thresholds
    conf_values = [0.05, 0.03, 0.02, 0.015, 0.01]
    IOU = 0.45  # Keep standard NMS
    
    # Aspect ratio filter
    MIN_ASPECT = 0.3
    MAX_ASPECT = 4.0
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"\n📹 Video: {video_path.name}")
    print(f"   Resolution: {width}x{height}, FPS: {fps}")
    print(f"   IoU/NMS: {IOU} (fixed for proper suppression)")
    
    # Read a sample of frames
    frames = []
    for i in range(30):  # Test on 30 frames
        ret, frame = cap.read()
        if not ret:
            break
        if i % 3 == 0:  # Sample every 3rd frame
            frames.append(frame)
    cap.release()
    
    print(f"\n   Testing on {len(frames)} sample frames...")
    
    results_table = []
    
    for conf in conf_values:
        print(f"\n{'='*60}")
        print(f"Testing Confidence: {conf}")
        print(f"{'='*60}")
        
        detection_counts = []
        
        for frame in frames:
            results = model.predict(
                source=frame,
                conf=conf,
                iou=IOU,
                classes=[0],
                max_det=1500,
                imgsz=1920,
                half=True,
                verbose=False
            )
            
            # Count with aspect filter
            count = 0
            for result in results:
                boxes = result.boxes
                for j in range(len(boxes)):
                    box = boxes.xyxy[j].cpu().numpy()
                    x1, y1, x2, y2 = box
                    w = x2 - x1
                    h = y2 - y1
                    if w > 0 and h > 0:
                        aspect = h / w
                        if MIN_ASPECT <= aspect <= MAX_ASPECT:
                            count += 1
            
            detection_counts.append(count)
        
        avg = np.mean(detection_counts)
        max_det = max(detection_counts)
        min_det = min(detection_counts)
        
        results_table.append({
            'conf': conf,
            'avg': avg,
            'max': max_det,
            'min': min_det
        })
        
        print(f"   Avg: {avg:.1f}, Max: {max_det}, Min: {min_det}")
        
        # Check if this meets target
        if avg >= 200:
            print(f"   ✅ TARGET MET! (200-400)")
        elif avg >= 150:
            print(f"   ⚠️  Close to target")
        else:
            print(f"   ❌ Below target")
    
    # Summary table
    print("\n" + "=" * 80)
    print("📊 CONFIDENCE SWEEP RESULTS")
    print("=" * 80)
    print(f"\n{'Confidence':<15} {'Avg Det':<12} {'Max Det':<10} {'Min Det':<10} {'Status'}")
    print("-" * 60)
    
    for r in results_table:
        status = "✅ TARGET" if r['avg'] >= 200 else ("⚠️ CLOSE" if r['avg'] >= 150 else "❌ LOW")
        print(f"{r['conf']:<15} {r['avg']:<12.1f} {r['max']:<10} {r['min']:<10} {status}")
    
    # Find best config
    best = max(results_table, key=lambda x: x['avg'])
    
    print(f"\n🏆 BEST CONFIGURATION:")
    print(f"   Confidence: {best['conf']}")
    print(f"   Average: {best['avg']:.1f} people/frame")
    print(f"   Maximum: {best['max']} people")
    
    # Generate video with best config
    print(f"\n🎬 Generating output video with conf={best['conf']}...")
    
    cap = cv2.VideoCapture(str(video_path))
    output_path = output_dir / f"dense_crowd_conf_{best['conf']}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    for i in range(100):
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model.predict(
            source=frame,
            conf=best['conf'],
            iou=IOU,
            classes=[0],
            max_det=1500,
            imgsz=1920,
            half=True,
            verbose=False
        )
        
        annotated = frame.copy()
        det_count = 0
        
        for result in results:
            boxes = result.boxes
            for j in range(len(boxes)):
                box = boxes.xyxy[j].cpu().numpy()
                conf_score = float(boxes.conf[j].cpu().numpy())
                x1, y1, x2, y2 = box
                w = x2 - x1
                h = y2 - y1
                if w > 0 and h > 0:
                    aspect = h / w
                    if MIN_ASPECT <= aspect <= MAX_ASPECT:
                        det_count += 1
                        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        cv2.putText(annotated, f"Dense Crowd - Optimized", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(annotated, f"People: {det_count}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        cv2.putText(annotated, f"Conf={best['conf']} IoU={IOU}", (10, 130),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        out.write(annotated)
    
    cap.release()
    out.release()
    
    print(f"\n📁 Output saved: {output_path}")
    print("\n" + "=" * 80)
    print("📝 RECOMMENDATION")
    print("=" * 80)
    
    if best['avg'] >= 200:
        print(f"\n  ✅ Use Confidence={best['conf']} for dense Indian crowds")
        print(f"     This achieves {best['avg']:.0f} avg, {best['max']} max people/frame")
    else:
        print(f"\n  ⚠️  Maximum detection is {best['avg']:.0f} people/frame")
        print(f"     The video may not contain 200-400 visible people")
        print(f"     OR people are too small/occluded for detection")
        print(f"\n  💡 Options:")
        print(f"     1. Try a denser crowd video")
        print(f"     2. Use YOLOv8x (larger model, slower)")
        print(f"     3. Current detection may be accurate for this video")
    
    print("=" * 80)
    

if __name__ == "__main__":
    test_conf_sweep()
