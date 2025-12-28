"""
Create video from image frames to verify frame reading
"""
import cv2
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.video_reader import FrameReader
from app.utils.preprocessing import preprocess_frame
from app.utils.config import OUTPUT_DIR

def create_video_from_frames():
    print("=" * 60)
    print("CREATING VIDEO FROM FRAMES")
    print("=" * 60)
    
    # MOT17 dataset path
    image_source = Path(__file__).parent.parent / "MOT17" / "MOT17" / "train" / "MOT17-02-FRCNN" / "img1"
    
    if not image_source.exists():
        print(f"❌ MOT17 dataset not found at: {image_source}")
        return False
    
    print(f"📁 Source: {image_source}")
    print(f"🎯 Processing: 100 frames")
    print()
    
    # Initialize reader
    print("1. Initializing frame reader...")
    reader = FrameReader(str(image_source), source_type="images", fps=10)
    
    # Get first frame to set up video writer
    success, first_frame = reader.read_frame()
    if not success:
        print("❌ Failed to read first frame")
        return False
    
    height, width = first_frame.shape[:2]
    print(f"   ✅ Frame size: {width}x{height}")
    print(f"   ✅ Total frames available: {reader.frame_count}")
    print()
    
    # Setup video writer
    output_path = OUTPUT_DIR / "test_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, 10.0, (width, height))
    
    if not out.isOpened():
        print("❌ Failed to create video writer")
        return False
    
    print(f"2. Creating video: {output_path}")
    print()
    
    # Write first frame
    out.write(first_frame)
    frame_count = 1
    
    # Process remaining frames
    max_frames = 100
    print("3. Processing frames...")
    
    while frame_count < max_frames:
        success, frame = reader.read_frame()
        
        if not success:
            print(f"   ⚠️  Stopped at frame {frame_count} (end of sequence)")
            break
        
        # Apply preprocessing
        processed = preprocess_frame(frame)
        
        # Write to video
        out.write(processed)
        frame_count += 1
        
        # Progress indicator
        if frame_count % 20 == 0:
            print(f"   ✅ Processed {frame_count} frames...")
    
    # Cleanup
    out.release()
    reader.release()
    
    print()
    print(f"✅ Video created successfully!")
    print(f"   - Total frames: {frame_count}")
    print(f"   - Duration: {frame_count/10:.1f} seconds")
    print(f"   - FPS: 10")
    print(f"   - Output: {output_path}")
    print()
    print("=" * 60)
    print("🎬 NOW PLAY THE VIDEO!")
    print("=" * 60)
    print(f"\nLocation: {output_path}")
    print("\nDouble-click to play or use VLC/Windows Media Player")
    print("\n✅ If video plays smoothly → Frame reading is working perfectly!")
    print("✅ Then we can proceed to Phase 2 (YOLO Detection)")
    
    return True


if __name__ == "__main__":
    try:
        success = create_video_from_frames()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
