"""
PHASE 1 TEST: Video Reader + Preprocessing
Test frame reading from image sequences and videos
"""
import cv2
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.video_reader import FrameReader
from app.utils.preprocessing import preprocess_frame, auto_detect_lighting
from app.utils.config import OUTPUT_DIR

def test_phase1():
    print("=" * 60)
    print("PHASE 1 TEST: FRAME READER + PREPROCESSING")
    print("=" * 60)
    
    # Test with image sequence (MOT17)
    # Use MOT17-02-FRCNN sequence from parent folder
    image_source = Path(__file__).parent.parent / "MOT17" / "MOT17" / "train" / "MOT17-02-FRCNN" / "img1"
    
    if not image_source.exists():
        print(f"\n⚠ Image folder not found: {image_source}")
        print("Please check MOT17 dataset location")
        print("\nSkipping image sequence test...")
        return False
    
    print(f"\n📁 Testing Image Sequence Reader")
    print(f"   Source: {image_source}")
    print("-" * 60)
    
    try:
        # Initialize reader
        reader = FrameReader(str(image_source), source_type="images", fps=10)
        info = reader.get_frame_info()
        print(f"✓ Initialized successfully")
        print(f"  - Source type: {info['source_type']}")
        print(f"  - Total frames: {info['total_frames']}")
        print(f"  - FPS: {info['fps']}")
        
        # Read and process first 10 frames
        print(f"\n📸 Reading first 10 frames...")
        frame_count = 0
        
        for i in range(10):
            success, frame = reader.read_frame()
            
            if not success:
                print(f"  ⚠ Failed to read frame {i+1}")
                break
            
            # Test preprocessing
            lighting = auto_detect_lighting(frame)
            processed_frame = preprocess_frame(frame)
            
            frame_count += 1
            
            if i == 0:
                # Display first frame info
                print(f"\n  First Frame Info:")
                print(f"    - Shape: {frame.shape}")
                print(f"    - Lighting: {lighting}")
                print(f"    - Preprocessed shape: {processed_frame.shape}")
                
                # Save first frame for visual check
                output_path = OUTPUT_DIR / "phase1_test_frame.jpg"
                cv2.imwrite(str(output_path), processed_frame)
                print(f"    - Saved to: {output_path}")
            
            # Simple progress indicator
            if (i + 1) % 5 == 0:
                print(f"  ✓ Processed {i+1} frames")
        
        print(f"\n✅ Successfully processed {frame_count} frames")
        print(f"📊 Progress: {reader.get_progress()*100:.1f}%")
        
        # Cleanup
        reader.release()
        print(f"\n✓ Resources released")
        
        print("\n" + "=" * 60)
        print("PHASE 1 TEST PASSED ✅")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Check output/phase1_test_frame.jpg")
        print("2. Verify frame looks correct")
        print("3. Ready to move to Phase 2 (YOLO Detection)")
        
    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_phase1()
    sys.exit(0 if success else 1)
