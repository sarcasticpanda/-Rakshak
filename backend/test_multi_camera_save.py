"""
Multi-Camera Parallel Processing - Auto-Save Mode
Saves annotated frames to output folder instead of display
"""
import cv2
import time
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, '.')
from app.core.camera_pipeline import CameraPipeline, CameraConfig


def create_grid(frames, grid_cols=2):
    """Arrange multiple frames in a grid."""
    if not frames:
        return None
    
    n_frames = len(frames)
    grid_rows = (n_frames + grid_cols - 1) // grid_cols
    h, w = frames[0][1].shape[:2]
    
    grid_h = h * grid_rows
    grid_w = w * grid_cols
    grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
    
    for idx, (name, frame) in enumerate(frames):
        row = idx // grid_cols
        col = idx % grid_cols
        y1 = row * h
        y2 = y1 + h
        x1 = col * w
        x2 = x1 + w
        grid[y1:y2, x1:x2] = frame
    
    return grid


def main():
    print("="*60)
    print("MULTI-CAMERA PARALLEL PROCESSING - AUTO-SAVE MODE")
    print("="*60)
    
    # Create output folder
    output_dir = Path("output/multi_camera_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output folder: {output_dir}")
    
    # Create pipelines for 3 cameras
    cameras = []
    
    print("\n[Setup] Initializing cameras...")
    
    # Camera 1: Stampede
    cam1 = CameraPipeline(CameraConfig(
        camera_id="cam_stampede",
        name="Stampede Dense",
        source="../check_vids/stampede.mp4",
        location="Location 1",
        target_fps=10
    ))
    if cam1.connect():
        cam1.start()
        cameras.append(("Stampede", cam1))
    
    # Camera 2: Test2
    cam2 = CameraPipeline(CameraConfig(
        camera_id="cam_test2",
        name="Test2 Sparse",
        source="../check_vids/test2.mp4",
        location="Location 2",
        target_fps=10
    ))
    if cam2.connect():
        cam2.start()
        cameras.append(("Test2", cam2))
    
    # Camera 3: Test3
    cam3 = CameraPipeline(CameraConfig(
        camera_id="cam_test3",
        name="Test3 Medium",
        source="../check_vids/test3.mp4",
        location="Location 3",
        target_fps=10
    ))
    if cam3.connect():
        cam3.start()
        cameras.append(("Test3", cam3))
    
    print(f"\n✅ {len(cameras)} cameras active")
    print("\n" + "="*60)
    print("CAPTURING FRAMES - Will save 10 snapshots")
    print("="*60)
    
    # Wait for cameras to warm up
    print("\n⏳ Warming up cameras...")
    time.sleep(5)
    
    try:
        for snapshot_num in range(1, 11):
            print(f"\n📸 Snapshot {snapshot_num}/10")
            
            # Collect frames from all cameras
            frames = []
            total_people = 0
            max_risk = 0
            
            for name, cam in cameras:
                frame = cam.get_frame()
                metrics = cam.get_metrics()
                
                if frame is not None:
                    # Resize for grid display
                    frame_resized = cv2.resize(frame, (640, 360))
                    frames.append((name, frame_resized))
                    
                    if metrics:
                        print(f"   {name}: {metrics.people_count} people | Risk: {metrics.risk_score:.1f} | {metrics.risk_level}")
                        total_people += metrics.people_count
                        max_risk = max(max_risk, metrics.risk_score)
            
            if frames:
                # Create grid
                grid = create_grid(frames, grid_cols=2)
                
                if grid is not None:
                    # Add global stats overlay
                    h, w = grid.shape[:2]
                    
                    # Top banner
                    cv2.rectangle(grid, (0, 0), (w, 60), (0, 0, 0), -1)
                    cv2.putText(grid, f"MULTI-CAMERA MONITORING - Snapshot {snapshot_num}", 
                               (w//2 - 250, 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(grid, f"Total People: {total_people} | Max Risk: {max_risk:.1f}", 
                               (w//2 - 150, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    
                    # Save
                    filename = output_dir / f"snapshot_{snapshot_num:02d}.jpg"
                    cv2.imwrite(str(filename), grid)
                    print(f"   💾 Saved: {filename.name}")
                    print(f"   📊 Total: {total_people} people | Max Risk: {max_risk:.1f}")
            
            # Wait between snapshots
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    
    finally:
        print("\n\nStopping cameras...")
        for _, cam in cameras:
            cam.stop()
            cam.disconnect()
        
        print("\n" + "="*60)
        print(f"✅ Complete! Check {output_dir} for results")
        print("="*60)


if __name__ == "__main__":
    main()
