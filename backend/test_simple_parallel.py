"""
Simple Multi-Camera Parallel Test - NO THREADING
Direct frame processing to verify parallel capability
"""
import cv2
import time
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, '.')
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics


class SimpleCamera:
    """Simple camera processor without threading"""
    
    def __init__(self, name, video_path):
        self.name = name
        self.video_path = video_path
        
        # Open video
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video info
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"[{name}] Loaded: {self.width}x{self.height} @ {self.fps} FPS")
        
        # Initialize AI pipeline
        self.detector = RobustDetectionPipeline(enable_heatmap=True)
        self.tracker = ByteTracker(
            track_thresh=0.05,
            match_thresh=0.20,
            min_hits=1,
            max_age=20
        )
        self.metrics = CrowdMetrics()
        
        print(f"[{name}] AI pipeline ready")
    
    def read_frame(self):
        """Read next frame, loop if at end"""
        ret, frame = self.cap.read()
        if not ret:
            # Loop video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        return frame if ret else None
    
    def process_frame(self, frame):
        """Process frame through AI pipeline"""
        h, w = frame.shape[:2]
        
        # Detect
        detections, _ = self.detector.detect(frame)
        
        # Track
        tracks = self.tracker.update(detections, (h, w), self.detector.heatmap)
        
        # Metrics
        metrics_dict = self.metrics.calculate(self.tracker.tracks, (h, w), self.detector.heatmap)
        risk_score = self.metrics.calculate_risk_score(metrics_dict)
        
        if risk_score < 40:
            risk_level = "NORMAL"
        elif risk_score < 70:
            risk_level = "WARNING"
        else:
            risk_level = "CRITICAL"
        
        # Annotate
        annotated = self.annotate(frame, tracks, metrics_dict, risk_score, risk_level)
        
        return annotated, metrics_dict, risk_score, risk_level
    
    def annotate(self, frame, tracks, metrics, risk_score, risk_level):
        """Draw annotations"""
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw tracks
        for track in tracks:
            x1, y1, x2, y2 = map(int, track.tlbr)
            track_id = track.track_id
            
            # Speed color
            speed = track.velocity_magnitude if hasattr(track, 'velocity_magnitude') else 0
            if speed < 3:
                color = (0, 255, 0)
            elif speed < 7:
                color = (0, 255, 255)
            else:
                color = (0, 0, 255)
            
            # Box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, f"ID:{track_id}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Info overlay
        cv2.rectangle(annotated, (5, 5), (250, 100), (0, 0, 0), -1)
        cv2.putText(annotated, self.name, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(annotated, f"People: {metrics['count']}", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(annotated, f"Risk: {risk_score:.0f} ({risk_level})", (10, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return annotated
    
    def close(self):
        """Release resources"""
        self.cap.release()


def create_grid(frames):
    """Create 2x2 grid from frames"""
    if len(frames) < 1:
        return None
    
    # Resize all to same size
    target_size = (640, 360)
    resized = [cv2.resize(f, target_size) for f in frames]
    
    # Pad if needed
    while len(resized) < 4:
        resized.append(np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8))
    
    # Create grid
    top_row = np.hstack([resized[0], resized[1]])
    bottom_row = np.hstack([resized[2], resized[3]])
    grid = np.vstack([top_row, bottom_row])
    
    return grid


def main():
    print("="*60)
    print("SIMPLE MULTI-CAMERA PARALLEL TEST")
    print("="*60)
    
    # Initialize cameras
    cameras = [
        SimpleCamera("Stampede", "../check_vids/stampede.mp4"),
        SimpleCamera("Test2", "../check_vids/test2.mp4"),
        SimpleCamera("Test3", "../check_vids/test3.mp4")
    ]
    
    print(f"\n✅ {len(cameras)} cameras initialized")
    print("\n" + "="*60)
    print("Processing frames - Press Q to quit")
    print("="*60)
    
    # Create window for better Windows compatibility
    cv2.namedWindow("Multi-Camera Grid", cv2.WINDOW_NORMAL)
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            loop_start = time.time()
            frames = []
            total_people = 0
            max_risk = 0
            
            # Process all cameras
            for cam in cameras:
                raw_frame = cam.read_frame()
                if raw_frame is not None:
                    annotated, metrics, risk, level = cam.process_frame(raw_frame)
                    frames.append(annotated)
                    
                    people = metrics['count']
                    total_people += people
                    max_risk = max(max_risk, risk)
                    
                    if frame_count % 30 == 0:
                        print(f"  {cam.name}: {people} people | Risk: {risk:.0f} ({level})")
            
            # Create grid
            if len(frames) >= 3:
                grid = create_grid(frames)
                if grid is not None and grid.size > 0:
                    # Calculate FPS
                    elapsed = time.time() - start_time
                    display_fps = frame_count / elapsed if elapsed > 0 else 0
                    loop_time = (time.time() - loop_start) * 1000  # ms
                    
                    # Add global info
                    h, w = grid.shape[:2]
                    cv2.rectangle(grid, (0, 0), (w, 50), (0, 0, 0), -1)
                    cv2.putText(grid, f"MULTI-CAMERA MONITORING - Frame {frame_count} | FPS: {display_fps:.1f}", 
                               (w//2 - 300, 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(grid, f"Total: {total_people} people | Max Risk: {max_risk:.0f} | Process: {loop_time:.0f}ms", 
                               (w//2 - 250, 42),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    cv2.imshow("Multi-Camera Grid", grid)
                else:
                    print(f"⚠️ Grid creation failed at frame {frame_count}")
            else:
                print(f"⚠️ Only {len(frames)} frames available (need 3)")
            
            frame_count += 1
            
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"\n[Frame {frame_count}] Total: {total_people} people | Max Risk: {max_risk:.0f} | FPS: {fps:.1f}\n")
            
            # Controls (30ms = ~33 FPS max display rate)
            if cv2.waitKey(30) & 0xFF == ord('q'):
                print("\n⛔ Quit requested")
                break
                
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n\nCleaning up...")
        for cam in cameras:
            cam.close()
        cv2.destroyAllWindows()
        
        print("\n" + "="*60)
        print("✅ Complete")
        print("="*60)


if __name__ == "__main__":
    main()
