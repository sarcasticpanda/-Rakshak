"""
ULTRA AGGRESSIVE settings to push detection to maximum
Testing: conf=0.01, iou=0.80, NO aspect filter, imgsz=1920
"""

import cv2
import torch
from ultralytics import YOLO
from pathlib import Path
import numpy as np

def test_ultra_aggressive():
    """Test with ULTRA aggressive settings"""
    print("=" * 70)
    print("ULTRA AGGRESSIVE DETECTION TEST")
    print("=" * 70)
    
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    
    # Load model
    print("\nLoading YOLOv8m...")
    model = YOLO("yolov8m.pt")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    
    # Test different configurations
    configs = [
        {"name": "Config 1: Original", "conf": 0.05, "iou": 0.70, "max_det": 1000, "imgsz": 1280, "filter": True},
        {"name": "Config 2: Lower conf", "conf": 0.02, "iou": 0.70, "max_det": 1000, "imgsz": 1280, "filter": True},
        {"name": "Config 3: No filter", "conf": 0.05, "iou": 0.70, "max_det": 1000, "imgsz": 1280, "filter": False},
        {"name": "Config 4: Higher IoU", "conf": 0.05, "iou": 0.80, "max_det": 1000, "imgsz": 1280, "filter": True},
        {"name": "Config 5: Larger imgsz", "conf": 0.05, "iou": 0.70, "max_det": 1000, "imgsz": 1920, "filter": True},
        {"name": "Config 6: ULTRA (all)", "conf": 0.01, "iou": 0.85, "max_det": 1500, "imgsz": 1920, "filter": False},
    ]
    
    results = []
    
    for config in configs:
        print(f"\n{'='*70}")
        print(f"{config['name']}")
        print(f"  conf={config['conf']}, iou={config['iou']}, max_det={config['max_det']}")
        print(f"  imgsz={config['imgsz']}, aspect_filter={config['filter']}")
        print(f"{'='*70}")
        
        # Reset video
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        total_detections = 0
        frame_count = 0
        
        for i in range(10):  # Test 10 frames
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run detection
            detections = model(
                frame,
                conf=config['conf'],
                iou=config['iou'],
                max_det=config['max_det'],
                imgsz=config['imgsz'],
                half=True,
                device=device,
                verbose=False
            )
            
            # Count detections
            count = 0
            for result in detections:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    
                    # Only person class
                    if class_id != 0:
                        continue
                    
                    # Apply aspect filter if enabled
                    if config['filter']:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        width = x2 - x1
                        height = y2 - y1
                        aspect_ratio = height / (width + 1e-6)
                        
                        if aspect_ratio < 0.3 or aspect_ratio > 4.0:
                            continue
                    
                    count += 1
            
            total_detections += count
            frame_count += 1
        
        avg = total_detections / frame_count if frame_count > 0 else 0
        results.append({'config': config['name'], 'avg': avg})
        print(f"\n  ✅ Average: {avg:.1f} people/frame")
    
    cap.release()
    
    # Print comparison
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)
    print(f"\n{'Configuration':<30} {'Avg Detections':<20}")
    print("-" * 50)
    
    for result in results:
        print(f"{result['config']:<30} {result['avg']:<20.1f}")
    
    # Find best
    best = max(results, key=lambda x: x['avg'])
    
    print("\n" + "=" * 70)
    print(f"✅ BEST: {best['config']} with {best['avg']:.1f} people/frame")
    print("=" * 70)
    
    if best['avg'] < 100:
        print("\n⚠️  IMPORTANT REALITY CHECK:")
        print("   Your test video (test3.mp4) may NOT contain 400-500 people!")
        print("   - Current detection: ~67-80 people/frame")
        print("   - This might be the ACTUAL crowd size in the video")
        print("   - Dense crowds of 400-500 require special conditions:")
        print("     • Very tight packing (stampede-level density)")
        print("     • Aerial/high-angle view to see everyone")
        print("     • Large frame coverage area")
        print("\n   RECOMMENDATION:")
        print("   1. Visually count people in one frame to verify")
        print("   2. Test on a KNOWN high-density video (500+ people)")
        print("   3. If video has <100 people, detection is working correctly!")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_ultra_aggressive()
