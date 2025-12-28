"""
Comprehensive Detection Test
Tests YOLO detection on multiple datasets:
1. MOT17 sequences
2. Real Indian crowd videos
"""
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.video_reader import FrameReader
from app.core.detector import PersonDetector
from app.utils.preprocessing import preprocess_frame
from app.utils.config import OUTPUT_DIR

def test_video_source(source_path, source_name, output_prefix, max_frames=50, source_type="auto"):
    """Test detection on a single video source"""
    
    print(f"\n{'='*60}")
    print(f"Testing: {source_name}")
    print(f"{'='*60}")
    
    if not Path(source_path).exists():
        print(f"❌ Source not found: {source_path}")
        return False
    
    # Initialize
    reader = FrameReader(str(source_path), source_type=source_type, fps=10)
    detector = PersonDetector()
    
    # Get first frame for video setup
    success, first_frame = reader.read_frame()
    if not success:
        print(f"❌ Failed to read first frame")
        return False
    
    height, width = first_frame.shape[:2]
    
    # Setup output paths
    output_video = OUTPUT_DIR / f"{output_prefix}_detection.mp4"
    output_image = OUTPUT_DIR / f"{output_prefix}_frame.jpg"
    
    # Video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video), fourcc, 10.0, (width, height))
    
    # Process first frame
    preprocessed = preprocess_frame(first_frame)
    annotated, detections = detector.detect_and_draw(preprocessed, color=(0, 255, 0), thickness=2)
    stats = detector.get_stats(detections)
    
    # Save first frame
    cv2.imwrite(str(output_image), annotated)
    out.write(annotated)
    
    print(f"✅ Frame 1: {stats['count']} people (conf: {stats['avg_confidence']:.2f})")
    
    frame_count = 1
    total_people = stats['count']
    
    # Process remaining frames
    while frame_count < max_frames:
        success, frame = reader.read_frame()
        if not success:
            break
        
        preprocessed = preprocess_frame(frame)
        annotated, detections = detector.detect_and_draw(preprocessed, color=(0, 255, 0), thickness=2)
        stats = detector.get_stats(detections)
        
        out.write(annotated)
        frame_count += 1
        total_people += stats['count']
        
        if frame_count % 10 == 0:
            print(f"✅ Frame {frame_count}: avg {total_people/frame_count:.1f} people/frame")
    
    # Cleanup
    out.release()
    reader.release()
    
    avg_people = total_people / frame_count
    
    print(f"\n📊 Summary:")
    print(f"   - Frames processed: {frame_count}")
    print(f"   - Total detections: {total_people}")
    print(f"   - Avg people/frame: {avg_people:.1f}")
    print(f"   - Image saved: {output_image}")
    print(f"   - Video saved: {output_video}")
    
    return True


def main():
    print("=" * 60)
    print("COMPREHENSIVE DETECTION TEST")
    print("Testing on multiple datasets")
    print("=" * 60)
    
    results = {}
    
    # Test 1: MOT17-02 (original)
    mot17_02 = Path(__file__).parent.parent / "MOT17" / "MOT17" / "train" / "MOT17-02-FRCNN" / "img1"
    if mot17_02.exists():
        results['MOT17-02'] = test_video_source(
            mot17_02, "MOT17-02 (Plaza)", "mot17_02", 
            max_frames=50, source_type="images"
        )
    
    # Test 2: MOT17-04 (different sequence)
    mot17_04 = Path(__file__).parent.parent / "MOT17" / "MOT17" / "train" / "MOT17-04-FRCNN" / "img1"
    if mot17_04.exists():
        results['MOT17-04'] = test_video_source(
            mot17_04, "MOT17-04 (Street)", "mot17_04",
            max_frames=50, source_type="images"
        )
    
    # Test 3: MOT17-09 (different sequence)
    mot17_09 = Path(__file__).parent.parent / "MOT17" / "MOT17" / "train" / "MOT17-09-FRCNN" / "img1"
    if mot17_09.exists():
        results['MOT17-09'] = test_video_source(
            mot17_09, "MOT17-09 (Station)", "mot17_09",
            max_frames=50, source_type="images"
        )
    
    # Test 4-6: Real Indian crowd videos
    check_vids_dir = Path(__file__).parent.parent / "check_vids"
    
    if check_vids_dir.exists():
        for video_file in check_vids_dir.glob("*.mp4"):
            video_name = video_file.stem
            results[video_name] = test_video_source(
                video_file, f"Indian Crowd - {video_name}", f"indian_{video_name}",
                max_frames=100, source_type="video"
            )
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")
    
    print("\n📁 All outputs saved to: backend/output/")
    print("\n🎯 Next Steps:")
    print("   1. Check all output images and videos")
    print("   2. Verify detection quality on Indian crowd videos")
    print("   3. If good → Proceed to Phase 3 (Tracking)")
    
    return all(results.values())


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
