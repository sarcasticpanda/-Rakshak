"""
Optimized detection for DENSE STAMPEDE scenarios
Lower thresholds, more aggressive detection, handle occlusions
"""
import sys
sys.path.insert(0, str(__file__).replace('test_stampede_optimized.py', ''))

import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO


def test_ultra_dense_detection():
    print("=" * 70)
    print("ULTRA-DENSE STAMPEDE DETECTION TEST")
    print("Optimizing for heavily overlapping people")
    print("=" * 70)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Load model
    print("\n🔧 Loading YOLOv8m...")
    model = YOLO("yolov8m.pt")
    
    # Test different configurations
    configs = [
        {
            'name': 'Current (Conservative)',
            'conf': 0.02,
            'iou': 0.35,
            'max_det': 1500,
        },
        {
            'name': 'Aggressive (More Detections)',
            'conf': 0.01,
            'iou': 0.25,
            'max_det': 2000,
        },
        {
            'name': 'Ultra-Aggressive (Maximum)',
            'conf': 0.005,
            'iou': 0.20,
            'max_det': 3000,
        }
    ]
    
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Test on frame 200 (high panic from earlier test)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 200)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to read frame")
        return
    
    print(f"\n📹 Testing on Frame 200 (Peak panic frame)")
    print(f"   Resolution: {width}x{height}")
    print(f"\n{'='*70}")
    
    results_data = []
    
    for i, config in enumerate(configs):
        print(f"\n🧪 Testing: {config['name']}")
        print(f"   conf={config['conf']}, iou={config['iou']}, max_det={config['max_det']}")
        
        # Run detection
        results = model.predict(
            frame,
            conf=config['conf'],
            iou=config['iou'],
            max_det=config['max_det'],
            classes=[0],  # Person only
            imgsz=1920,
            half=True,
            verbose=False
        )
        
        # Filter detections
        detections = []
        for r in results:
            if r.boxes is not None and len(r.boxes) > 0:
                boxes = r.boxes.xyxy.cpu().numpy()
                confs = r.boxes.conf.cpu().numpy()
                
                for box, conf in zip(boxes, confs):
                    x1, y1, x2, y2 = box
                    w = x2 - x1
                    h = y2 - y1
                    area = w * h
                    
                    # Relaxed size filters for dense crowds
                    if w > 400 or h > 650:  # Slightly relaxed
                        continue
                    if h / height > 0.55:  # Allow slightly taller
                        continue
                    if w / width > 0.3:  # Allow slightly wider
                        continue
                    if area > 120000:  # Slightly relaxed area
                        continue
                    
                    # Relaxed aspect ratio (allow more squished people)
                    if h > 0:
                        aspect = w / h
                        if aspect < 0.6 or aspect > 3.5:  # More permissive
                            continue
                    
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf
                    })
        
        count = len(detections)
        print(f"   ✅ Detected: {count} people")
        
        results_data.append({
            'config': config,
            'count': count,
            'detections': detections,
            'frame': frame.copy()
        })
    
    # Save comparison images
    output_dir = Path(__file__).parent / "output" / "stampede_optimization"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("📊 RESULTS COMPARISON")
    print(f"{'='*70}")
    
    for i, result in enumerate(results_data):
        config_name = result['config']['name']
        count = result['count']
        frame_vis = result['frame'].copy()
        
        # Draw all detections
        for det in result['detections']:
            x1, y1, x2, y2 = map(int, det['bbox'])
            conf = det['confidence']
            
            # Color based on confidence
            if conf > 0.5:
                color = (0, 255, 0)  # Green - high conf
            elif conf > 0.2:
                color = (0, 255, 255)  # Yellow - medium
            else:
                color = (255, 165, 0)  # Orange - low
            
            cv2.rectangle(frame_vis, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame_vis, f"{conf:.2f}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Add title
        cv2.putText(frame_vis, f"{config_name}: {count} people", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        
        output_path = output_dir / f"config_{i+1}_{config_name.lower().replace(' ', '_')}.jpg"
        cv2.imwrite(str(output_path), frame_vis)
        
        print(f"\n   Config {i+1}: {config_name}")
        print(f"   └─ Detected: {count} people")
        print(f"   └─ Image: {output_path.name}")
    
    print(f"\n{'='*70}")
    print(f"📁 Comparison images saved to: {output_dir}")
    print(f"{'='*70}")
    
    # Recommendation
    best = max(results_data, key=lambda x: x['count'])
    print(f"\n✅ RECOMMENDATION: Use '{best['config']['name']}'")
    print(f"   Detected {best['count']} people (most comprehensive)")
    
    return results_data


if __name__ == "__main__":
    test_ultra_dense_detection()
