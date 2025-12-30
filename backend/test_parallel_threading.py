"""
Test Parallel Video Processing
3 videos in parallel threads with shared GPU model
"""
import sys
sys.path.insert(0, '.')

from app.core.multi_video_display import MultiVideoDisplay


def main():
    print("="*60)
    print("THREAD-BASED PARALLEL VIDEO PROCESSING TEST")
    print("="*60)
    print("Features:")
    print("  ✓ 3 videos in parallel threads")
    print("  ✓ Shared YOLOv8m detector (memory efficient)")
    print("  ✓ Non-blocking display (30 FPS)")
    print("  ✓ Independent video looping")
    print("  ✓ Drop old frames (always latest)")
    print("="*60)
    
    # Create manager
    manager = MultiVideoDisplay(max_videos=10)
    
    # Add 3 videos
    print("\n[Setup] Adding videos...")
    
    # Video 1: Test2 (sparse - fast processing)
    manager.add_video(
        video_source="../check_vids/test2.mp4",
        camera_id="cam_test2",
        camera_name="Test2 Sparse",
        target_fps=10
    )
    
    # Video 2: Test3 (medium - moderate processing)
    manager.add_video(
        video_source="../check_vids/test3.mp4",
        camera_id="cam_test3",
        camera_name="Test3 Medium",
        target_fps=8
    )
    
    # Video 3: Stampede (dense - slow processing)
    manager.add_video(
        video_source="../check_vids/stampede.mp4",
        camera_id="cam_stampede",
        camera_name="Stampede Dense",
        target_fps=6
    )
    
    print(f"\n✅ {len(manager.processors)} videos added")
    
    # Start all processors (parallel threading begins)
    manager.start_all()
    
    # Display loop (30 FPS, non-blocking)
    try:
        manager.display_loop()
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
