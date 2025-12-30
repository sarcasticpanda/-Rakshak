"""
Test True Parallel Multi-Camera Processing
Shows all 3 cameras in grid view with parallel processing
"""
import cv2
import time
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, '.')
from app.core.multi_camera_parallel import ParallelCameraManager, CameraConfig


def create_grid(frames_dict, camera_order):
    """
    Create 2x2 grid from camera frames.
    
    Args:
        frames_dict: Dict mapping camera_id to CameraFrame
        camera_order: List of camera_ids in display order
        
    Returns:
        Combined grid image
    """
    target_size = (640, 360)
    frames = []
    
    # Get frames in order
    for cam_id in camera_order:
        if cam_id in frames_dict:
            frame = frames_dict[cam_id].annotated_frame
            frame_resized = cv2.resize(frame, target_size)
            frames.append(frame_resized)
        else:
            # Placeholder for missing camera
            placeholder = np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)
            cv2.putText(placeholder, f"No signal: {cam_id}", (150, 180),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            frames.append(placeholder)
    
    # Pad to 4 frames
    while len(frames) < 4:
        frames.append(np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8))
    
    # Create 2x2 grid
    top_row = np.hstack([frames[0], frames[1]])
    bottom_row = np.hstack([frames[2], frames[3]])
    grid = np.vstack([top_row, bottom_row])
    
    return grid


def main():
    print("="*60)
    print("TRUE PARALLEL MULTI-CAMERA PROCESSING")
    print("="*60)
    print("Using multiprocessing - each camera in own process")
    print("="*60)
    
    # Create manager
    manager = ParallelCameraManager(max_cameras=10)
    
    # Add 3 cameras
    print("\n[Setup] Adding cameras...")
    cameras = [
        CameraConfig(
            camera_id="cam_stampede",
            name="Stampede Dense",
            source="../check_vids/stampede.mp4",
            location="Location 1",
            target_fps=10
        ),
        CameraConfig(
            camera_id="cam_test2",
            name="Test2 Sparse",
            source="../check_vids/test2.mp4",
            location="Location 2",
            target_fps=10
        ),
        CameraConfig(
            camera_id="cam_test3",
            name="Test3 Medium",
            source="../check_vids/test3.mp4",
            location="Location 3",
            target_fps=10
        )
    ]
    
    camera_order = []
    for config in cameras:
        if manager.add_camera(config):
            camera_order.append(config.camera_id)
    
    print(f"\n✅ {len(camera_order)} cameras added")
    
    # Start all cameras (parallel processing begins)
    manager.start_all()
    
    print("\n" + "="*60)
    print("PARALLEL GRID VIEW - Press Q to quit, S for screenshot")
    print("="*60)
    print("Each camera runs in separate process with own YOLO")
    print("="*60)
    
    # Wait for first frames
    print("\n⏳ Waiting for cameras to produce frames...")
    time.sleep(8)  # Give more time for parallel initialization
    
    # Create window
    cv2.namedWindow("Parallel Multi-Camera Grid", cv2.WINDOW_NORMAL)
    
    frame_count = 0
    start_time = time.time()
    last_stats_time = time.time()
    
    try:
        while True:
            loop_start = time.time()
            
            # Get frames from all cameras (non-blocking)
            frames = manager.get_frames()
            
            if len(frames) > 0:
                # Create grid
                grid = create_grid(frames, camera_order)
                
                if grid is not None and grid.size > 0:
                    # Calculate display FPS
                    elapsed = time.time() - start_time
                    display_fps = frame_count / elapsed if elapsed > 0 else 0
                    loop_time = (time.time() - loop_start) * 1000
                    
                    # Get stats
                    stats = manager.get_stats()
                    
                    # Add global overlay
                    h, w = grid.shape[:2]
                    cv2.rectangle(grid, (0, 0), (w, 70), (0, 0, 0), -1)
                    
                    # Title
                    cv2.putText(grid, f"PARALLEL MULTI-CAMERA MONITORING - Frame {frame_count}", 
                               (w//2 - 350, 22),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                    # Stats line 1
                    cv2.putText(grid, f"Display FPS: {display_fps:.1f} | Process Time: {loop_time:.0f}ms | Active: {stats['active_cameras']}/{stats['total_cameras']}", 
                               (w//2 - 350, 44),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    
                    # Stats line 2
                    cv2.putText(grid, f"Total People: {stats['total_people']} | Max Risk: {stats['max_risk']:.0f}", 
                               (w//2 - 350, 62),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Display
                    cv2.imshow("Parallel Multi-Camera Grid", grid)
                    frame_count += 1
                    
                    # Print stats every 5 seconds
                    if time.time() - last_stats_time >= 5.0:
                        print(f"\n[Frame {frame_count}] Display FPS: {display_fps:.1f}")
                        for cam_id, cam_stats in stats['cameras'].items():
                            print(f"  {cam_id}: {cam_stats['people']} people | Risk: {cam_stats['risk']:.0f} | FPS: {cam_stats['fps']:.1f}")
                        print(f"  TOTAL: {stats['total_people']} people | Max Risk: {stats['max_risk']:.0f}")
                        last_stats_time = time.time()
                else:
                    print(f"⚠️ Grid creation failed")
            else:
                print(f"⏳ No frames yet... waiting")
                time.sleep(0.5)
            
            # Controls (30ms = ~33 FPS display rate)
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                print("\n⛔ Quit requested")
                break
            elif key == ord('s'):
                if 'grid' in locals() and grid is not None:
                    output_dir = Path("output/parallel_test")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = output_dir / f"parallel_{int(time.time())}.jpg"
                    cv2.imwrite(str(filename), grid)
                    print(f"\n📸 Screenshot saved: {filename}")
                    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n\n[Cleanup] Stopping all cameras...")
        manager.stop_all()
        cv2.destroyAllWindows()
        
        # Final stats
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed if elapsed > 0 else 0
        print("\n" + "="*60)
        print("PARALLEL PROCESSING COMPLETE")
        print("="*60)
        print(f"Total frames displayed: {frame_count}")
        print(f"Total time: {elapsed:.1f}s")
        print(f"Average display FPS: {avg_fps:.1f}")
        print("="*60)


if __name__ == "__main__":
    # Set multiprocessing start method (important for Windows)
    import multiprocessing as mp
    mp.set_start_method('spawn', force=True)
    
    main()
