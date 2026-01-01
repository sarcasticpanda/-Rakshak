"""
Visual Multi-Camera Display - OPTIMIZED FOR MINIMUM LATENCY
Shows all cameras with live annotations including heatmap
Direct CameraPipeline access - no redundant threading layers
"""
import cv2
import time
import numpy as np
import sys

sys.path.insert(0, '.')
from app.core.camera_pipeline import CameraPipeline, CameraConfig

def create_grid(frames, grid_cols=2):
    """
    Arrange multiple frames in a grid.
    
    Args:
        frames: List of (name, frame) tuples
        grid_cols: Number of columns in grid
        
    Returns:
        Combined grid image
    """
    if not frames:
        return None
    
    # Calculate grid dimensions
    n_frames = len(frames)
    grid_rows = (n_frames + grid_cols - 1) // grid_cols
    
    # Get frame dimensions (assume all same size)
    h, w = frames[0][1].shape[:2]
    
    # Create blank canvas
    grid_h = h * grid_rows
    grid_w = w * grid_cols
    grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
    
    # Place frames in grid
    for idx, (name, frame) in enumerate(frames):
        row = idx // grid_cols
        col = idx % grid_cols
        y1 = row * h
        y2 = y1 + h
        x1 = col * w
        x2 = x1 + w
        # Defensive: if frame is None or wrong size, fill with error
        if frame is None or frame.shape[0] != h or frame.shape[1] != w:
            error_img = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(error_img, f"NO DATA", (30, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
            grid[y1:y2, x1:x2] = error_img
        else:
            grid[y1:y2, x1:x2] = frame
    
    return grid


def main():
    print("="*60)
    print("OPTIMIZED MULTI-CAMERA MONITORING")
    print("="*60)

    # Direct CameraPipeline setup - no wrapper layers
    cameras = []
    configs = [
        ("Stampede", "cam_stampede", "../check_vids/stampede.mp4"),
        ("Test2", "cam_test2", "../check_vids/test2.mp4"),
        ("Test3", "cam_test3", "../check_vids/test3.mp4"),
    ]
    
    print("\n[Setup] Initializing cameras...")
    for name, cam_id, source in configs:
        cam = CameraPipeline(CameraConfig(
            camera_id=cam_id,
            name=name,
            source=source,
            location=f"Location {len(cameras)+1}",
            target_fps=30  # 30 FPS = 33ms per frame (smooth)
        ))
        if cam.connect():
            cam.start()  # CameraPipeline already runs detection in its own thread
            cameras.append((name, cam))
            print(f"  ✅ {name} ready")

    print(f"\n✅ {len(cameras)} cameras active")
    print("\n" + "="*60)
    print("CONTROLS: Q = Quit | S = Screenshot")
    print("Heatmap appears after ~30 frames")
    print("="*60)

    time.sleep(2)  # Reduced wait time

    frame_count = 0
    last_time = time.time()
    display_fps = 0
    try:
        while True:
            frames = []
            
            # Track display FPS
            now = time.time()
            if frame_count % 30 == 0:
                dt = now - last_time
                if dt > 0:
                    display_fps = 30.0 / dt
                last_time = now
            
            # Direct frame access - minimal overhead
            for name, cam in cameras:
                try:
                    # CameraPipeline.get_frame() returns fully annotated frame
                    # (detection boxes, IDs, heatmap, metrics dashboard)
                    frame = cam.get_frame()
                    
                    if frame is not None:
                        # Just resize for grid - frame already has all annotations
                        frame_resized = cv2.resize(frame, (640, 360))
                        frames.append((name, frame_resized))
                    else:
                        # Loading placeholder
                        placeholder = np.zeros((360, 640, 3), dtype=np.uint8)
                        cv2.putText(placeholder, f"LOADING {name}...", (150, 180), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                        frames.append((name, placeholder))
                        
                except Exception as e:
                    print(f"[ERROR] {name}: {e}")
                    error_img = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(error_img, f"ERROR", (250, 180), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    frames.append((name, error_img))
            
            if frames:
                frame_count += 1
                grid = create_grid(frames, grid_cols=2)
                
                if grid is not None:
                    h, w = grid.shape[:2]
                    # Minimal top banner with FPS
                    cv2.rectangle(grid, (0, 0), (w, 50), (0, 0, 0), -1)
                    status = "🟢 HEATMAP ACTIVE" if frame_count > 30 else "🟡 WARMING UP"
                    cv2.putText(grid, f"MULTI-CAMERA | Frame {frame_count} | {status} | Display: {display_fps:.1f} FPS", 
                               (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    cv2.imshow("Multi-Camera Grid", grid)
                    
                    # Status update every 60 frames
                    if frame_count % 60 == 1:
                        print(f"[Frame {frame_count}] {len(cameras)} cameras | {status}")
            
            # Minimal wait for smooth display (1ms vs 30ms)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n⛔ Quit")
                break
            elif key == ord('s'):
                if 'grid' in locals() and grid is not None:
                    filename = f"output/multi_camera_{int(time.time())}.jpg"
                    cv2.imwrite(filename, grid)
                    print(f"\n📸 Saved: {filename}")
                    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    finally:
        print("\nStopping cameras...")
        for name, cam in cameras:
            cam.stop()
            cam.disconnect()
        cv2.destroyAllWindows()
        print("✅ Done")

if __name__ == "__main__":
    main()
