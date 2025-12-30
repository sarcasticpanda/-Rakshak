"""
Visual Multi-Camera Display
Shows all cameras in a tiled grid view with live annotations
"""
import cv2
import time
import numpy as np
from pathlib import Path
import sys
import threading
from queue import Queue, Empty

sys.path.insert(0, '.')
from app.core.camera_pipeline import CameraPipeline, CameraConfig

    # CameraContext: holds per-camera state and queue
class CameraContext:
    def __init__(self, name, cam):
        self.name = name
        self.cam = cam
        self.frame_queue = Queue(maxsize=1)  # Only latest frame kept
        self.latest_frame = None
        self.latest_metrics = None
        self.people_count = 0
        self.risk = 0
        self.fps = 0
        self.last_update = time.time()
        self.error = None
        self.lock = threading.Lock()

    def update(self, frame, metrics):
        with self.lock:
            self.latest_frame = frame
            self.latest_metrics = metrics
            self.people_count = getattr(metrics, 'people_count', 0) if metrics else 0
            self.risk = getattr(metrics, 'risk_score', 0) if metrics else 0
            self.last_update = time.time()
            # FPS is updated in processing thread

    def get_display_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    def get_metrics(self):
        with self.lock:
            return self.latest_metrics
    def get_stats(self):
        with self.lock:
            return self.people_count, self.risk, self.fps, self.error

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
    print("VISUAL MULTI-CAMERA PARALLEL PROCESSING")
    print("="*60)
    
    # Create pipelines for 3 cameras
    cameras = []
    
    # Camera 1: Stampede
    print("\n[Setup] Initializing cameras...")
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
    print("GRID VIEW - Press Q to quit, S for screenshot")
    print("="*60)
    
    # Wait for cameras to produce first frames
    print("\nWaiting for cameras to produce frames...")
    time.sleep(5)
    
    frame_count = 0
    last_errors = {name: None for name, _ in cameras}
    last_fps = {name: 0 for name, _ in cameras}
    last_frame_time = {name: time.time() for name, _ in cameras}
    try:
        while True:
            frames = []
            total_people = 0
            max_risk = 0
            for name, cam in cameras:
                try:
                    frame = cam.get_frame()
                    metrics = cam.get_metrics()
                    now = time.time()
                    # FPS calculation
                    if frame is not None:
                        dt = now - last_frame_time[name]
                        last_fps[name] = 1.0/dt if dt > 0 else 0
                        last_frame_time[name] = now
                    # Resize for grid display (smaller)
                    if frame is not None:
                        frame_resized = cv2.resize(frame, (640, 360))
                        # Overlay camera name and FPS
                        cv2.rectangle(frame_resized, (0,0), (200,30), (0,0,0), -1)
                        cv2.putText(frame_resized, f"{name} | FPS: {last_fps[name]:.1f}", (10,22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
                        # Overlay error if any
                        if last_errors[name]:
                            cv2.putText(frame_resized, f"ERROR: {last_errors[name]}", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                        frames.append((name, frame_resized))
                        if metrics:
                            total_people += getattr(metrics, 'people_count', 0)
                            max_risk = max(max_risk, getattr(metrics, 'risk_score', 0))
                        else:
                            # Overlay no metrics
                            cv2.putText(frame_resized, "NO METRICS", (10,70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                    else:
                        # No frame: show error overlay
                        error_img = np.zeros((360, 640, 3), dtype=np.uint8)
                        cv2.putText(error_img, f"NO FRAME", (120, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
                        if last_errors[name]:
                            cv2.putText(error_img, f"ERROR: {last_errors[name]}", (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                        frames.append((name, error_img))
                except Exception as e:
                    last_errors[name] = str(e)
                    print(f"[ERROR] Camera {name}: {e}")
                    # Show error overlay
                    error_img = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(error_img, f"CAMERA ERROR", (100, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
                    cv2.putText(error_img, f"{e}", (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                    frames.append((name, error_img))
            if len(frames) > 0:
                frame_count += 1
                grid = create_grid(frames, grid_cols=2)
                if grid is not None:
                    h, w = grid.shape[:2]
                    # Top banner
                    cv2.rectangle(grid, (0, 0), (w, 60), (0, 0, 0), -1)
                    cv2.putText(grid, f"MULTI-CAMERA MONITORING", (w//2 - 200, 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(grid, f"Total People: {total_people if total_people else '?'} | Max Risk: {max_risk if max_risk else '?'}", 
                               (w//2 - 150, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    cv2.imshow("Multi-Camera Grid View", grid)
                    if frame_count % 30 == 1:
                        for name in last_fps:
                            print(f"[Frame {frame_count}] {name}: FPS={last_fps[name]:.1f} | Last error: {last_errors[name]}")
            else:
                print(f"⚠️ No frames available yet... waiting")
                time.sleep(0.5)
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                print("\n⛔ Quit requested")
                break
            elif key == ord('s'):
                if 'grid' in locals() and grid is not None:
                    filename = f"output/multi_camera_{int(time.time())}.jpg"
                    cv2.imwrite(filename, grid)
                    print(f"\n📸 Screenshot saved: {filename}")
    except KeyboardInterrupt:
        pass
    finally:
        print("\n\nStopping cameras...")
        for _, cam in cameras:
            cam.stop()
            cam.disconnect()
        cv2.destroyAllWindows()
        print("\n" + "="*60)
        print("✅ All cameras stopped")
        print("="*60)

def camera_capture_loop(context: CameraContext):
    while True:
        try:
            frame = context.cam.get_frame()
            metrics = context.cam.get_metrics()
            # Always keep only the latest frame in the queue
            if frame is not None:
                try:
                    context.frame_queue.get_nowait()
                except Empty:
                    pass
                context.frame_queue.put((frame, metrics))
        except Exception as e:
            context.error = str(e)
        time.sleep(0.01)  # Small sleep to avoid busy loop

def camera_processing_loop(context: CameraContext):
    last_time = time.time()
    while True:
        try:
            frame, metrics = context.frame_queue.get()
            now = time.time()
            dt = now - last_time
            context.fps = 1.0/dt if dt > 0 else 0
            last_time = now
            context.update(frame, metrics)
        except Exception as e:
            context.error = str(e)

def main():
    print("="*60)
    print("VISUAL MULTI-CAMERA PARALLEL PROCESSING")
    print("="*60)

    # Camera setup
    camera_configs = [
        ("Stampede", CameraConfig(
            camera_id="cam_stampede",
            name="Stampede Dense",
            source="../check_vids/stampede.mp4",
            location="Location 1",
            target_fps=10)),
        ("Test2", CameraConfig(
            camera_id="cam_test2",
            name="Test2 Sparse",
            source="../check_vids/test2.mp4",
            location="Location 2",
            target_fps=10)),
        ("Test3", CameraConfig(
            camera_id="cam_test3",
            name="Test3 Medium",
            source="../check_vids/test3.mp4",
            location="Location 3",
            target_fps=10)),
    ]
    contexts = []
    print("\n[Setup] Initializing cameras...")
    for name, config in camera_configs:
        cam = CameraPipeline(config)
        if cam.connect():
            cam.start()
            context = CameraContext(name, cam)
            contexts.append(context)
            # Start capture and processing threads
            threading.Thread(target=camera_capture_loop, args=(context,), daemon=True).start()
            threading.Thread(target=camera_processing_loop, args=(context,), daemon=True).start()

    print(f"\n✅ {len(contexts)} cameras active")
    print("\n" + "="*60)
    print("GRID VIEW - Press Q to quit, S for screenshot")
    print("="*60)

    print("\nWaiting for cameras to produce frames...")
    time.sleep(5)

    frame_count = 0
    try:
        while True:
            frames = []
            for context in contexts:
                frame = context.get_display_frame()
                people, risk, fps, error = context.get_stats()
                # Defensive: overlay stats on each frame
                if frame is not None:
                    frame_resized = cv2.resize(frame, (640, 360))
                    cv2.rectangle(frame_resized, (0,0), (320,60), (0,0,0), -1)
                    cv2.putText(frame_resized, f"{context.name} | FPS: {fps:.1f}", (10,22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
                    cv2.putText(frame_resized, f"People: {people} | Risk: {risk:.1f}", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                    if error:
                        cv2.putText(frame_resized, f"ERROR: {error}", (10,80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                    frames.append((context.name, frame_resized))
                else:
                    error_img = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(error_img, f"NO FRAME", (120, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
                    if error:
                        cv2.putText(error_img, f"ERROR: {error}", (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                    frames.append((context.name, error_img))
            if len(frames) > 0:
                frame_count += 1
                grid = create_grid(frames, grid_cols=2)
                if grid is not None:
                    h, w = grid.shape[:2]
                    # Top banner
                    cv2.rectangle(grid, (0, 0), (w, 60), (0, 0, 0), -1)
                    cv2.putText(grid, f"MULTI-CAMERA MONITORING", (w//2 - 200, 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.imshow("Multi-Camera Grid View", grid)
                    if frame_count % 30 == 1:
                        for context in contexts:
                            print(f"[Frame {frame_count}] {context.name}: FPS={context.fps:.1f} | People={context.people_count} | Risk={context.risk:.1f} | Error={context.error}")
            else:
                print(f"⚠️ No frames available yet... waiting")
                time.sleep(0.5)
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                print("\n⛔ Quit requested")
                break
            elif key == ord('s'):
                if 'grid' in locals() and grid is not None:
                    filename = f"output/multi_camera_{int(time.time())}.jpg"
                    cv2.imwrite(filename, grid)
                    print(f"\n📸 Screenshot saved: {filename}")
    except KeyboardInterrupt:
        pass
    finally:
        print("\n\nStopping cameras...")
        for context in contexts:
            context.cam.stop()
            context.cam.disconnect()
        cv2.destroyAllWindows()
        print("\n" + "="*60)
        print("✅ All cameras stopped")
        print("="*60)

if __name__ == "__main__":
    main()
