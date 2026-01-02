"""
CameraPipeline - Self-contained processing pipeline for a single camera
Each camera instance has its own detector, tracker, metrics - NO SHARED STATE

Supports:
- IP Webcam (HTTP MJPEG)
- RTSP (CCTV cameras)
- USB Webcam
- Video files (for testing)
"""
import cv2
import numpy as np
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Dict, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics


class CameraStatus(Enum):
    """Camera connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    STOPPED = "stopped"


class SourceType(Enum):
    """Type of camera source"""
    IP_WEBCAM = "ip_webcam"      # HTTP MJPEG stream
    RTSP = "rtsp"                # RTSP stream (CCTV)
    USB_WEBCAM = "usb_webcam"    # Local USB camera
    VIDEO_FILE = "video_file"   # MP4/AVI file
    UNKNOWN = "unknown"


@dataclass
class CameraConfig:
    """Configuration for a camera"""
    camera_id: str
    name: str
    source: str                          # URL, RTSP, file path, or int
    location: str = "Unknown"            # Physical location description
    context: str = "general"             # temple, mall, event, station, etc.
    enabled: bool = True
    
    # Processing settings
    target_fps: int = 10                 # Target processing FPS
    resolution: Tuple[int, int] = None   # Optional resize (width, height)
    
    # Alert thresholds (can customize per camera)
    warning_threshold: float = 40.0
    critical_threshold: float = 70.0


@dataclass
class CameraMetrics:
    """Real-time metrics from a camera"""
    camera_id: str
    timestamp: float
    
    # Detection
    people_count: int = 0
    detection_count: int = 0
    
    # Risk
    risk_score: float = 0.0
    risk_level: str = "NORMAL"
    
    # Crowd metrics
    density: float = 0.0
    density_normalized: float = 0.0  # 0-1 range for percentage display
    compression: float = 0.0
    velocity_variance: float = 0.0
    flow_collision: float = 0.0
    panic_wave: float = 0.0
    
    # Prediction
    prediction: str = "STABLE"
    trend: float = 0.0
    
    # Performance
    fps: float = 0.0
    latency_ms: float = 0.0
    
    # Status
    status: str = "connected"
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict"""
        return {
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "people_count": self.people_count,
            "detection_count": self.detection_count,
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "density": round(self.density, 3),
            "compression": round(self.compression, 1),
            "velocity_variance": round(self.velocity_variance, 2),
            "flow_collision": round(self.flow_collision, 3),
            "panic_wave": round(self.panic_wave, 3),
            "prediction": self.prediction,
            "trend": round(self.trend, 3),
            "fps": round(self.fps, 1),
            "latency_ms": round(self.latency_ms, 1),
            "status": self.status
        }


class CameraPipeline:
    """
    Self-contained processing pipeline for a single camera.
    
    Each instance has:
    - Own video capture
    - Own YOLO detector
    - Own tracker (isolated track IDs)
    - Own crowd metrics
    - Own heatmap
    
    NO SHARED STATE between camera instances.
    """
    
    def __init__(self, config: CameraConfig):
        """
        Initialize camera pipeline.
        
        Args:
            config: CameraConfig with camera settings
        """
        self.config = config
        self.camera_id = config.camera_id
        
        # Status
        self.status = CameraStatus.DISCONNECTED
        self.error_message: Optional[str] = None
        
        # Video capture
        self.cap: Optional[cv2.VideoCapture] = None
        self.source_type = self._detect_source_type(config.source)
        self.frame_width = 0
        self.frame_height = 0
        self.source_fps = 25
        
        # Processing components (initialized on connect)
        self.detector: Optional[RobustDetectionPipeline] = None
        self.tracker: Optional[ByteTracker] = None
        self.metrics_calc: Optional[CrowdMetrics] = None
        
        # Current state
        self.current_frame: Optional[np.ndarray] = None
        self.current_annotated: Optional[np.ndarray] = None
        self.current_metrics: Optional[CameraMetrics] = None
        self.current_detections: list = []
        self.current_tracks: list = []
        
        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_queue = queue.Queue(maxsize=2)
        self._lock = threading.Lock()
        
        # Performance tracking
        self._frame_count = 0
        self._start_time = 0
        self._fps = 0.0
        
        # Callbacks
        self._on_metrics_callback: Optional[Callable] = None
        self._on_alert_callback: Optional[Callable] = None
        
        print(f"[CameraPipeline:{self.camera_id}] Created")
        print(f"   Source: {config.source}")
        print(f"   Type: {self.source_type.value}")
        print(f"   Location: {config.location}")
    
    def _detect_source_type(self, source) -> SourceType:
        """Detect the type of camera source"""
        if isinstance(source, int):
            return SourceType.USB_WEBCAM
        elif source.startswith("rtsp://"):
            return SourceType.RTSP
        elif source.startswith("http://") or source.startswith("https://"):
            return SourceType.IP_WEBCAM
        elif Path(source).resolve().exists():
            return SourceType.VIDEO_FILE
        else:
            return SourceType.UNKNOWN
    
    def connect(self) -> bool:
        """
        Connect to camera source and initialize processing components.
        
        Returns:
            True if connected successfully
        """
        self.status = CameraStatus.CONNECTING
        print(f"[CameraPipeline:{self.camera_id}] Connecting...")
        
        try:
            # Connect to video source
            source = self.config.source
            if isinstance(source, str) and source.isdigit():
                source = int(source)
            
            if self.source_type == SourceType.RTSP:
                self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                self.cap = cv2.VideoCapture(source)
            
            if not self.cap.isOpened():
                raise ConnectionError(f"Could not open source: {source}")
            
            # Get source properties
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.source_fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 25
            
            print(f"[CameraPipeline:{self.camera_id}] Source connected")
            print(f"   Resolution: {self.frame_width}x{self.frame_height}")
            print(f"   FPS: {self.source_fps}")
            
            # Initialize processing components
            print(f"[CameraPipeline:{self.camera_id}] Loading AI pipeline...")
            self.detector = RobustDetectionPipeline(enable_heatmap=False)  # Disabled - was dropping 40%+ detections
            self.tracker = ByteTracker()
            self.metrics_calc = CrowdMetrics()
            
            self.status = CameraStatus.CONNECTED
            self.error_message = None
            print(f"[CameraPipeline:{self.camera_id}] ✅ Ready")
            return True
            
        except Exception as e:
            self.status = CameraStatus.ERROR
            self.error_message = str(e)
            print(f"[CameraPipeline:{self.camera_id}] ❌ Error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from camera and cleanup"""
        self.stop()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.status = CameraStatus.DISCONNECTED
        print(f"[CameraPipeline:{self.camera_id}] Disconnected")
    
    def start(self):
        """Start processing in background thread"""
        if self._running:
            return
        
        if self.status != CameraStatus.CONNECTED:
            if not self.connect():
                return
        
        self._running = True
        self._frame_count = 0
        self._start_time = time.time()
        
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        print(f"[CameraPipeline:{self.camera_id}] Started processing")
    
    def stop(self):
        """Stop processing"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.status = CameraStatus.STOPPED
        print(f"[CameraPipeline:{self.camera_id}] Stopped")
    
    def _process_loop(self):
        """Main processing loop (runs in thread)"""
        frame_time = 1.0 / self.config.target_fps
        print(f"[CameraPipeline:{self.camera_id}] _process_loop started")
        
        while self._running:
            loop_start = time.time()
            
            try:
                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    if self.source_type == SourceType.VIDEO_FILE:
                        # Loop video file
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        print(f"[CameraPipeline:{self.camera_id}] Frame read failed")
                        time.sleep(0.1)
                        continue
                
                # Optional resize
                if self.config.resolution:
                    frame = cv2.resize(frame, self.config.resolution)
                
                # Process frame (this sets current_annotated)
                metrics = self._process_frame(frame)
                
                # Debug: Log first processed frame
                if self._frame_count == 1:
                    print(f"[CameraPipeline:{self.camera_id}] ✅ First frame processed")
                
                # Update FPS
                self._frame_count += 1
                if self._frame_count % 30 == 0:
                    elapsed = time.time() - self._start_time
                    self._fps = self._frame_count / elapsed
                
                # Callbacks
                if self._on_metrics_callback:
                    self._on_metrics_callback(metrics)
                
                # Check for alerts
                if self._on_alert_callback and metrics.risk_level == "CRITICAL":
                    self._on_alert_callback(self.camera_id, metrics)
                
                # Rate limiting
                process_time = time.time() - loop_start
                if process_time < frame_time:
                    time.sleep(frame_time - process_time)
                    
            except Exception as e:
                print(f"[CameraPipeline:{self.camera_id}] Error: {e}")
                time.sleep(0.1)
    
    def _process_frame(self, frame: np.ndarray) -> CameraMetrics:
        """
        Process a single frame through the full pipeline.
        
        Args:
            frame: BGR image
            
        Returns:
            CameraMetrics with all analysis results
        """
        process_start = time.time()
        h, w = frame.shape[:2]
        
        # Detection
        detections, metadata = self.detector.detect(frame)
        
        # Tracking
        tracks = self.tracker.update(detections, (h, w), self.detector.heatmap)
        
        # Crowd metrics
        metrics_dict = self.metrics_calc.calculate(
            self.tracker.tracks, (h, w), self.detector.heatmap
        )
        
        # Risk score
        risk_score = self.metrics_calc.calculate_risk_score(metrics_dict)
        
        # Risk level
        if risk_score < self.config.warning_threshold:
            risk_level = "NORMAL"
        elif risk_score < self.config.critical_threshold:
            risk_level = "WARNING"
        else:
            risk_level = "CRITICAL"
        
        # Prediction
        prediction = self.metrics_calc.predict_risk_trend()
        
        # Build annotated frame
        annotated = self._annotate_frame(frame, detections, tracks, metrics_dict, risk_score, risk_level)
        
        # Calculate latency
        latency_ms = (time.time() - process_start) * 1000
        
        # DEBUG: Log density values
        if self.camera_id == 'cam_stampede':  # Only log for one camera
            print(f"[Pipeline:{self.camera_id}] density={metrics_dict.get('density', 'N/A')}, density_normalized={metrics_dict.get('density_normalized', 'N/A')}")
        
        # Build metrics object
        camera_metrics = CameraMetrics(
            camera_id=self.camera_id,
            timestamp=time.time(),
            people_count=metrics_dict['count'],
            detection_count=len(detections),
            risk_score=risk_score,
            risk_level=risk_level,
            density=metrics_dict['density'],
            density_normalized=metrics_dict['density_normalized'],
            compression=metrics_dict['compression'],
            velocity_variance=metrics_dict['velocity_variance'],
            flow_collision=metrics_dict.get('flow_collision', 0),
            panic_wave=metrics_dict.get('panic_wave', 0),
            prediction=prediction.get('prediction', 'STABLE'),
            trend=prediction.get('trend', 0),
            fps=self._fps,
            latency_ms=latency_ms,
            status=self.status.value
        )
        
        if self.camera_id == 'cam_stampede':  # Debug
            print(f"[Pipeline:{self.camera_id}] CameraMetrics object density_normalized = {camera_metrics.density_normalized}")
        
        # Update current state (thread-safe)
        with self._lock:
            self.current_frame = frame
            self.current_annotated = annotated
            self.current_metrics = camera_metrics
            self.current_detections = detections
            self.current_tracks = tracks
        
        return camera_metrics
    
    def _annotate_frame(self, frame: np.ndarray, detections: list, tracks: list,
                        metrics: dict, risk_score: float, risk_level: str) -> np.ndarray:
        """Draw annotations on frame"""
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        # Heatmap overlay DISABLED - heatmap feature completely removed
        # No heatmap visualization to avoid confusion
        # if self.detector.heatmap and self.detector.heatmap.is_bootstrapped():
        #     heat_vis = self.detector.heatmap.get_visualization(frame)
        #     if heat_vis is not None:
        #         annotated = cv2.addWeighted(annotated, 0.5, heat_vis, 0.5, 0)
        
        # Skip drawing raw detections - tracks already show all people
        # This saves 10-15% rendering time with no accuracy impact
        
        # Draw tracks (colored by speed)
        for track in tracks:
            x1, y1, x2, y2 = map(int, track['bbox'])
            speed = np.sqrt(track['velocity'][0]**2 + track['velocity'][1]**2)
            
            if speed < 5:
                color = (0, 255, 0)
            elif speed < 15:
                color = (0, 255, 255)
            else:
                color = (0, 0, 255)
            
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, f"ID:{track['track_id']}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Trajectory - optimized: draw every 3rd frame only
            if self._frame_count % 3 == 0:
                trajectory = track.get('trajectory', [])
                if len(trajectory) > 5:
                    pts = np.array(trajectory[-10:], dtype=np.int32)  # Reduced from 15
                    cv2.polylines(annotated, [pts], False, color, 1)  # Thinner line
        
        # Dashboard
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (350, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)
        
        cv2.putText(annotated, f"Camera: {self.config.name}", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(annotated, f"Location: {self.config.location}", (10, 45),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(annotated, f"People: {metrics['count']}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(annotated, f"FPS: {self._fps:.1f}", (10, 95),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(annotated, f"Density: {metrics['density']:.2f} | Var: {metrics['velocity_variance']:.1f}",
                   (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(annotated, f"Flow: {metrics.get('flow_collision', 0):.2f} | Panic: {metrics.get('panic_wave', 0):.2f}",
                   (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Risk display
        risk_color = (0, 255, 0) if risk_level == "NORMAL" else (0, 165, 255) if risk_level == "WARNING" else (0, 0, 255)
        cv2.rectangle(annotated, (w-180, 10), (w-10, 90), (0, 0, 0), -1)
        cv2.rectangle(annotated, (w-180, 10), (w-10, 90), risk_color, 3)
        cv2.putText(annotated, f"{risk_score:.0f}", (w-150, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, risk_color, 3)
        cv2.putText(annotated, "/100", (w-70, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(annotated, risk_level, (w-160, 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, risk_color, 2)
        
        # Critical banner
        if risk_level == "CRITICAL":
            cv2.rectangle(annotated, (0, h-50), (w, h), (0, 0, 200), -1)
            cv2.putText(annotated, "!! STAMPEDE RISK !!", (w//2 - 150, h-15),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        return annotated
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current annotated frame (thread-safe)"""
        with self._lock:
            return self.current_annotated.copy() if self.current_annotated is not None else None
    
    def get_raw_frame(self) -> Optional[np.ndarray]:
        """Get current raw frame (thread-safe)"""
        with self._lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_metrics(self) -> Optional[CameraMetrics]:
        """Get current metrics (thread-safe)"""
        with self._lock:
            return self.current_metrics
    
    def get_jpeg_frame(self, quality: int = 80) -> Optional[bytes]:
        """Get current frame as JPEG bytes for streaming"""
        frame = self.get_frame()
        if frame is None:
            return None
        
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ret, jpeg = cv2.imencode('.jpg', frame, encode_param)
        return jpeg.tobytes() if ret else None
    
    def set_metrics_callback(self, callback: Callable):
        """Set callback for metrics updates"""
        self._on_metrics_callback = callback
    
    def set_alert_callback(self, callback: Callable):
        """Set callback for critical alerts"""
        self._on_alert_callback = callback
    
    def get_status(self) -> Dict:
        """Get camera status info"""
        return {
            "camera_id": self.camera_id,
            "name": self.config.name,
            "location": self.config.location,
            "source_type": self.source_type.value,
            "status": self.status.value,
            "resolution": f"{self.frame_width}x{self.frame_height}",
            "fps": self._fps,
            "error": self.error_message
        }


# ============================================================
# QUICK TEST
# ============================================================
if __name__ == "__main__":
    # Test with IP Webcam
    config = CameraConfig(
        camera_id="cam_001",
        name="Test Camera",
        source="http://100.115.33.220:8080/video",
        location="Test Room",
        context="testing"
    )
    
    pipeline = CameraPipeline(config)
    
    if pipeline.connect():
        print("\n" + "="*50)
        print("Press Q to quit, S for screenshot")
        print("="*50 + "\n")
        
        pipeline.start()
        
        try:
            while True:
                frame = pipeline.get_frame()
                if frame is not None:
                    cv2.imshow(f"Camera: {config.name}", frame)
                
                metrics = pipeline.get_metrics()
                if metrics:
                    print(f"\rPeople: {metrics.people_count} | Risk: {metrics.risk_score:.1f} | FPS: {metrics.fps:.1f}", end="")
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    if frame is not None:
                        cv2.imwrite(f"screenshot_{int(time.time())}.jpg", frame)
                        print("\nScreenshot saved!")
                        
        except KeyboardInterrupt:
            pass
        
        finally:
            pipeline.stop()
            pipeline.disconnect()
            cv2.destroyAllWindows()
            
            print("\n\nFinal Status:", pipeline.get_status())
