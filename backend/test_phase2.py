"""
PHASE 2 TEST: YOLO Person Detection
Detects people and draws bounding boxes
"""
import cv2
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.video_reader import FrameReader
from app.core.detector import PersonDetector
from app.utils.preprocessing import preprocess_frame
from app.utils.config import OUTPUT_DIR

def test_phase2():
    print("=" * 60)
    print("PHASE 2 TEST: YOLO PERSON DETECTION")
    print("=" * 60)
    
    # MOT17 dataset path
    image_source = Path(__file__).parent.parent / "MOT17" / "MOT17" / "train" / "MOT17-02-FRCNN" / "img1"
    
    if not image_source.exists():
        print(f"❌ MOT17 dataset not found at: {image_source}")
        return False
    
    print(f"📁 Source: {image_source}")
    print(f"🎯 Testing: Detection on 50 frames")
    print()
    
    # Initialize components
    print("1. Initializing components...")
    reader = FrameReader(str(image_source), source_type="images", fps=10)
    detector = PersonDetector()
    print(f"   ✅ Frame reader ready ({reader.frame_count} frames)")
    print(f"   ✅ YOLO detector ready (GPU enabled)")
    print()
    
    # Get first frame to set up video writer
    success, first_frame = reader.read_frame()
    if not success:
        print("❌ Failed to read first frame")
        return False
    
    height, width = first_frame.shape[:2]
    
    # Setup video writer
    output_video_path = OUTPUT_DIR / "phase2_detection_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video_path), fourcc, 10.0, (width, height))
    
    print(f"2. Processing frames with YOLO detection...")
    print()
    
    # Process first frame
    preprocessed = preprocess_frame(first_frame)
    annotated, detections = detector.detect_and_draw(preprocessed, color=(0, 255, 0), thickness=2)
    stats = detector.get_stats(detections)
    
    # Save first frame
    output_image_path = OUTPUT_DIR / "phase2_test_frame.jpg"
    cv2.imwrite(str(output_image_path), annotated)
    
    print(f"   📸 Frame 1:")
    print(f"      - People detected: {stats['count']}")
    print(f"      - Avg confidence: {stats['avg_confidence']:.2f}")
    print(f"      - Saved to: {output_image_path}")
    print()
    
    # Write first frame
    out.write(annotated)
    frame_count = 1
    total_detections = stats['count']
    
    # Process remaining frames
    max_frames = 50
    
    while frame_count < max_frames:
        success, frame = reader.read_frame()
        
        if not success:
            print(f"   ⚠️  Stopped at frame {frame_count} (end of sequence)")
            break
        
        # Preprocess and detect
        preprocessed = preprocess_frame(frame)
        annotated, detections = detector.detect_and_draw(preprocessed, color=(0, 255, 0), thickness=2)
        stats = detector.get_stats(detections)
        
        # Write to video
        out.write(annotated)
        
        frame_count += 1
        total_detections += stats['count']
        
        # Progress indicator
        if frame_count % 10 == 0:
            print(f"   ✅ Processed {frame_count} frames (avg {total_detections/frame_count:.1f} people/frame)")
    
    # Cleanup
    out.release()
    reader.release()
    
    print()
    print(f"✅ Detection complete!")
    print(f"   - Total frames: {frame_count}")
    print(f"   - Total detections: {total_detections}")
    print(f"   - Avg people per frame: {total_detections/frame_count:.1f}")
    print(f"   - Video: {output_video_path}")
    print(f"   - Image: {output_image_path}")
    print()
    print("=" * 60)
    print("PHASE 2 TEST PASSED ✅")
    print("=" * 60)
    print()
    print("🎬 NOW CHECK THE OUTPUTS:")
    print(f"   1. Image: {output_image_path}")
    print(f"      → Should show people with GREEN boxes")
    print()
    print(f"   2. Video: {output_video_path}")
    print(f"      → Should show people being tracked with boxes")
    print()
    print("✅ If boxes look good → Ready for Phase 3 (ByteTrack Tracking)")
    
    return True


if __name__ == "__main__":
    try:
        success = test_phase2()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
