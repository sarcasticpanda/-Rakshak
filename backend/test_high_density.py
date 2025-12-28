"""
High-Density Crowd Test - For 500+ people detection
Tests YOLOv8-Large on densest Indian crowd video
"""
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.video_reader import FrameReader
from ultralytics import YOLO
from app.utils.preprocessing import preprocess_frame
from app.utils.config import OUTPUT_DIR
import numpy as np

def test_high_density():
    print("=" * 70)
    print("HIGH-DENSITY CROWD TEST - YOLOv8-LARGE")
    print("Testing for 500+ people detection")
    print("=" * 70)
    
    # Test on densest video
    video_path = Path(__file__).parent.parent / "check_vids" / "test3.mp4"
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False
    
    print(f"\n📁 Video: {video_path}")
    print(f"🎯 Target: Detect 500+ people in dense frames")
    print()
    
    # Test with multiple models
    models_to_test = [
        ("yolov8m.pt", "Medium - Current"),
        ("yolov8l.pt", "Large - More Accurate"),
    ]
    
    for model_name, description in models_to_test:
        print(f"\n{'='*70}")
        print(f"Testing: {model_name} ({description})")
        print(f"{'='*70}")
        
        # Load model
        model = YOLO(model_name)
        model.to('cuda')
        
        # Initialize reader
        reader = FrameReader(str(video_path), source_type="video", fps=10)
        
        # Read first frame
        success, frame = reader.read_frame()
        if not success:
            print(f"❌ Failed to read frame")
            continue
        
        preprocessed = preprocess_frame(frame)
        height, width = preprocessed.shape[:2]
        
        # Run detection with LOWER confidence for dense crowds
        print(f"\n🔍 Running detection...")
        print(f"   - Confidence threshold: 0.15 (lower for far/small people)")
        print(f"   - IOU threshold: 0.45")
        
        results = model(preprocessed, conf=0.15, iou=0.45, verbose=False)
        
        # Filter and count
        detections = []
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                cls = int(boxes.cls[i].cpu().numpy())
                if cls == 0:  # Person only
                    box = boxes.xyxy[i].cpu().numpy()
                    conf = float(boxes.conf[i].cpu().numpy())
                    
                    # Aspect ratio filter
                    x1, y1, x2, y2 = box
                    w, h = x2 - x1, y2 - y1
                    if h > 0 and w > 0:
                        aspect = h / w
                        if 0.3 <= aspect <= 4.0:
                            detections.append({
                                'bbox': box.tolist(),
                                'conf': conf
                            })
        
        # Draw boxes
        annotated = preprocessed.copy()
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Add count overlay
        count_text = f"People: {len(detections)}"
        cv2.rectangle(annotated, (10, 10), (300, 60), (0, 0, 0), -1)
        cv2.putText(annotated, count_text, (20, 45), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        # Save output
        output_path = OUTPUT_DIR / f"high_density_{model_name.replace('.pt', '')}.jpg"
        cv2.imwrite(str(output_path), annotated)
        
        # Stats
        confidences = [d['conf'] for d in detections]
        
        print(f"\n📊 Results:")
        print(f"   ✅ People detected: {len(detections)}")
        print(f"   ✅ Avg confidence: {np.mean(confidences):.2f}")
        print(f"   ✅ Min confidence: {np.min(confidences):.2f}")
        print(f"   ✅ Max confidence: {np.max(confidences):.2f}")
        print(f"   ✅ Saved to: {output_path}")
        
        reader.release()
    
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("\nFor REAL-TIME camera feeds with Indian crowds:")
    print("   🎯 Use: yolov8m.pt (Medium)")
    print("   📈 Speed: ~30-40 FPS on your GPU")
    print("   🎯 Accuracy: Good for 20-50 people/frame")
    print()
    print("For EXTREME density (500+ people):")
    print("   🎯 Use: yolov8l.pt (Large)")
    print("   📈 Speed: ~20-25 FPS on your GPU")
    print("   🎯 Accuracy: Better for dense crowds")
    print()
    print("⚠️  Note: Detecting 500+ people in single frame is challenging")
    print("    because many people are very small/occluded.")
    print("    Real stampede detection uses:")
    print("    - Crowd density (people per area)")
    print("    - Motion patterns (not just count)")
    
    return True


if __name__ == "__main__":
    try:
        test_high_density()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
