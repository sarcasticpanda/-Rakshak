"""
Test IP Webcam / RTSP / Video File Connection
Supports multiple source types without breaking existing code.

Usage:
    python test_ip_webcam.py                    # Uses default IP Webcam URL
    python test_ip_webcam.py --source URL       # Custom URL or file path
    python test_ip_webcam.py --source 0         # Laptop webcam
    python test_ip_webcam.py --source video.mp4 # Video file

Controls:
    q - Quit
    s - Save screenshot
    r - Reset tracker
"""
import cv2
import numpy as np
import argparse
import time
from pathlib import Path
import sys

sys.path.insert(0, '.')
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics


# Default IP Webcam URL (your phone)
DEFAULT_IP_WEBCAM = "http://100.115.33.220:8080/video"


class CameraSource:
    """
    Universal camera source handler
    Supports: IP Webcam, RTSP, USB webcam, video files
    """
    
    def __init__(self, source):
        self.source = source
        self.cap = None
        self.source_type = self._detect_source_type(source)
        self.width = 0
        self.height = 0
        self.fps = 25
        print(f"[CameraSource] Type: {self.source_type}")
        print(f"[CameraSource] Source: {source}")
        
    def _detect_source_type(self, source):
        if isinstance(source, int):
            return "USB_WEBCAM"
        elif source.startswith("rtsp://"):
            return "RTSP"
        elif source.startswith("http://") or source.startswith("https://"):
            return "IP_WEBCAM"
        elif Path(source).exists():
            return "VIDEO_FILE"
        else:
            return "UNKNOWN"
    
    def connect(self) -> bool:
        print(f"[CameraSource] Connecting to {self.source}...")
        
        if self.source_type == "RTSP":
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            print(f"[CameraSource] ❌ Failed to connect!")
            return False
        
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 25
        
        print(f"[CameraSource] ✅ Connected!")
        print(f"[CameraSource] Resolution: {self.width}x{self.height}")
        print(f"[CameraSource] FPS: {self.fps}")
        return True
    
    def read(self):
        if self.cap is None:
            return False, None
        return self.cap.read()
    
    def release(self):
        if self.cap:
            self.cap.release()
            print("[CameraSource] Released")
    
    def get_info(self) -> dict:
        return {
            "source": str(self.source),
            "type": self.source_type,
            "width": self.width,
            "height": self.height,
            "fps": self.fps
        }


def draw_dashboard(frame, metrics, risk_score, fps, camera_info):
    """Draw metrics dashboard on frame"""
    h, w = frame.shape[:2]
    
    # Semi-transparent dashboard background
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (400, 200), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Title
    cv2.putText(frame, "STAMPEDE-RAKSHAK LIVE", (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    # Camera info
    cv2.putText(frame, f"Source: {camera_info['type']}", (10, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 70),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Metrics
    y = 95
    cv2.putText(frame, f"People: {metrics['count']}", (10, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    y += 25
    cv2.putText(frame, f"Density: {metrics['density']:.2f}", (10, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y += 20
    cv2.putText(frame, f"Variance: {metrics['velocity_variance']:.1f}", (10, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y += 20
    cv2.putText(frame, f"Compression: {metrics['compression']:.1f}px", (10, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y += 20
    cv2.putText(frame, f"Flow Collision: {metrics.get('flow_collision', 0):.2f}", (10, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Risk score (top right)
    risk_color = (0, 255, 0) if risk_score < 40 else (0, 165, 255) if risk_score < 70 else (0, 0, 255)
    risk_level = "NORMAL" if risk_score < 40 else "WARNING" if risk_score < 70 else "CRITICAL"
    
    # Risk box
    cv2.rectangle(frame, (w-200, 10), (w-10, 100), (0, 0, 0), -1)
    cv2.rectangle(frame, (w-200, 10), (w-10, 100), risk_color, 3)
    cv2.putText(frame, f"{risk_score:.0f}", (w-170, 70),
               cv2.FONT_HERSHEY_SIMPLEX, 1.8, risk_color, 3)
    cv2.putText(frame, "/100", (w-80, 70),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, risk_level, (w-180, 95),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, risk_color, 2)
    
    # Critical warning banner
    if risk_score >= 70:
        banner_y = h - 60
        cv2.rectangle(frame, (0, banner_y), (w, h), (0, 0, 200), -1)
        cv2.putText(frame, "!! HIGH STAMPEDE RISK DETECTED !!", (w//2 - 280, banner_y + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    return frame


def draw_detections(frame, detections, tracks, heatmap=None):
    """Draw detections and tracks on frame"""
    h, w = frame.shape[:2]
    
    # Draw heatmap overlay if available
    if heatmap is not None and heatmap.is_bootstrapped():
        heat_img = heatmap.get_visualization(frame)
        if heat_img is not None:
            frame = cv2.addWeighted(frame, 0.7, heat_img, 0.3, 0)
    
    # Draw raw detections (gray, thin)
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 100), 1)
    
    # Draw tracks (colored by speed)
    for track in tracks:
        x1, y1, x2, y2 = map(int, track['bbox'])
        
        # Color by speed
        speed = np.sqrt(track['velocity'][0]**2 + track['velocity'][1]**2)
        if speed < 5:
            color = (0, 255, 0)    # Green - slow/stationary
        elif speed < 15:
            color = (0, 255, 255)  # Yellow - walking
        else:
            color = (0, 0, 255)    # Red - running
        
        # Draw box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw ID and speed
        label = f"ID:{track['track_id']} {speed:.1f}px/f"
        cv2.putText(frame, label, (x1, y1-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw trajectory
        trajectory = track.get('trajectory', [])
        if len(trajectory) > 1:
            pts = np.array(trajectory[-20:], dtype=np.int32)  # Last 20 points
            cv2.polylines(frame, [pts], False, color, 2)
    
    return frame


def main():
    parser = argparse.ArgumentParser(description="Test IP Webcam / RTSP / Video")
    parser.add_argument("--source", type=str, default=DEFAULT_IP_WEBCAM,
                       help="Camera source: URL, RTSP, file path, or webcam index")
    parser.add_argument("--save", type=str, default=None,
                       help="Save output to video file")
    args = parser.parse_args()
    
    # Handle integer source (webcam index)
    source = args.source
    if source.isdigit():
        source = int(source)
    
    print("="*60)
    print("STAMPEDE-RAKSHAK: Live Camera Test")
    print("="*60)
    
    # Connect to camera
    camera = CameraSource(source)
    if not camera.connect():
        print("\n❌ Could not connect to camera!")
        print("\nTroubleshooting:")
        print("  1. Is IP Webcam app running and streaming?")
        print("  2. Are phone and PC on same network?")
        print(f"  3. Can you open {source} in browser?")
        return
    
    # Initialize pipeline components
    print("\n[Init] Loading detection pipeline...")
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    metrics_calc = CrowdMetrics()
    
    # Video writer (optional)
    out = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(args.save, fourcc, camera.fps, 
                             (camera.width, camera.height))
        print(f"[Init] Saving to: {args.save}")
    
    # Output directory for screenshots
    screenshot_dir = Path("output/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("LIVE FEED STARTED")
    print("="*60)
    print("Controls: [Q]uit  [S]creenshot  [R]eset tracker")
    print("="*60 + "\n")
    
    # FPS calculation
    frame_count = 0
    start_time = time.time()
    fps = 0
    
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[Warning] Frame read failed, retrying...")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Calculate FPS every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
            
            # Run detection pipeline
            detections, metadata = pipeline.detect(frame)
            
            # Run tracker
            h, w = frame.shape[:2]
            tracks = tracker.update(detections, (h, w), pipeline.heatmap)
            
            # Calculate metrics
            metrics = metrics_calc.calculate(tracker.tracks, (h, w), pipeline.heatmap)
            risk_score = metrics_calc.calculate_risk_score(metrics)
            
            # Draw everything
            annotated = frame.copy()
            annotated = draw_detections(annotated, detections, tracks, pipeline.heatmap)
            annotated = draw_dashboard(annotated, metrics, risk_score, fps, camera.get_info())
            
            # Save to video
            if out:
                out.write(annotated)
            
            # Display
            cv2.imshow("Stampede-Rakshak Live", annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[User] Quit requested")
                break
            elif key == ord('s'):
                # Save screenshot
                ss_path = screenshot_dir / f"screenshot_{int(time.time())}.jpg"
                cv2.imwrite(str(ss_path), annotated)
                print(f"[Screenshot] Saved: {ss_path}")
            elif key == ord('r'):
                # Reset tracker
                tracker.reset()
                print("[Reset] Tracker reset")
            
            # Print status every 50 frames
            if frame_count % 50 == 0:
                print(f"Frame {frame_count}: People={metrics['count']}, "
                      f"Risk={risk_score:.1f}, FPS={fps:.1f}")
    
    except KeyboardInterrupt:
        print("\n[User] Interrupted")
    
    finally:
        # Cleanup
        camera.release()
        if out:
            out.release()
        cv2.destroyAllWindows()
        
        # Final stats
        total_time = time.time() - start_time
        print("\n" + "="*60)
        print("SESSION COMPLETE")
        print("="*60)
        print(f"  Total frames: {frame_count}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Average FPS: {frame_count/total_time:.1f}")
        print("="*60)


if __name__ == "__main__":
    main()
