"""
Thread-Based Video Stream Processor
Processes single video in thread with shared GPU model
"""
import cv2
import time
import numpy as np
import threading
from typing import Optional, Dict
import torch


class VideoStreamProcessor:
    """
    Processes a single video stream in a thread.
    
    Features:
    - Thread-based (not multiprocessing)
    - Shared GPU YOLO model (memory efficient)
    - Non-blocking frame access (Option A: drop old frames)
    - Independent video looping (Option A: loop independently)
    - GPU memory monitoring
    """
    
    def __init__(self, video_source: str, camera_id: str, camera_name: str, 
                 detector, target_fps: int = 8):
        """
        Initialize processor.
        
        Args:
            video_source: Path to video file or stream URL
            camera_id: Unique camera identifier
            camera_name: Display name
            detector: Shared RobustDetectionPipeline instance
            target_fps: Target processing FPS (8-10 recommended)
        """
        self.video_source = video_source
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.detector = detector  # SHARED detector (no duplication)
        self.target_fps = target_fps
        
        # Video capture
        self.cap = None
        self.frame_width = 0
        self.frame_height = 0
        self.source_fps = 0
        
        # AI components (NOT shared - each thread has own)
        self.tracker = None
        self.metrics_calc = None
        
        # Current state (thread-safe access)
        self._lock = threading.Lock()
        self._latest_frame = None  # Annotated frame (Option A: only latest)
        self._latest_metrics = None
        self._frame_count = 0
        self._process_fps = 0.0
        
        # Threading
        self._running = False
        self._thread = None
        self._start_time = 0
        
        print(f"[VideoStreamProcessor:{camera_id}] Created ({camera_name})")
    
    def connect(self) -> bool:
        """Open video source"""
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            print(f"[{self.camera_id}] ❌ Failed to open: {self.video_source}")
            return False
        
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.source_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"[{self.camera_id}] Source: {self.frame_width}x{self.frame_height} @ {self.source_fps:.1f} FPS")
        
        # Initialize tracker and metrics (own instances)
        from app.core.tracker import ByteTracker
        from app.core.crowd_metrics import CrowdMetrics
        
        self.tracker = ByteTracker(
            track_thresh=0.05,
            match_thresh=0.20,
            min_hits=1,
            max_age=20
        )
        self.metrics_calc = CrowdMetrics()
        
        print(f"[{self.camera_id}] ✅ Connected")
        return True
    
    def start(self):
        """Start processing thread"""
        if self._running:
            return
        
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        
        print(f"[{self.camera_id}] Started processing thread")
    
    def stop(self):
        """Stop processing thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print(f"[{self.camera_id}] Stopped")
    
    def disconnect(self):
        """Release resources"""
        if self.cap:
            self.cap.release()
        print(f"[{self.camera_id}] Disconnected")
    
    def _process_loop(self):
        """Main processing loop (runs in thread)"""
        frame_time = 1.0 / self.target_fps
        
        # GPU memory before processing
        if torch.cuda.is_available():
            gpu_mem_start = torch.cuda.memory_allocated(0) / 1024**2
            print(f"[{self.camera_id}] GPU memory: {gpu_mem_start:.0f} MB")
        
        while self._running:
            loop_start = time.time()
            
            try:
                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    # Option A: Loop video independently
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                h, w = frame.shape[:2]
                
                # Process frame
                # Detection (SHARED detector - YOLO is thread-safe during inference)
                detections, _ = self.detector.detect(frame)
                
                # Tracking (own tracker) - returns list of track objects
                tracks = self.tracker.update(detections, (h, w), self.detector.heatmap)
                
                # Get actual track objects from tracker (self.tracker.tracks is a List[Track])
                # Use only confirmed tracks (same criteria as tracker._get_output)
                track_objects = [t for t in self.tracker.tracks if t.hits >= self.tracker.min_hits and t.time_since_update <= 5]
                
                # Metrics (own calculator) - use track objects
                metrics_dict = self.metrics_calc.calculate(track_objects, (h, w), self.detector.heatmap)
                risk_score = self.metrics_calc.calculate_risk_score(metrics_dict)
                
                # Risk level
                if risk_score < 40:
                    risk_level = "NORMAL"
                elif risk_score < 70:
                    risk_level = "WARNING"
                else:
                    risk_level = "CRITICAL"
                
                # Annotate frame
                annotated = self._annotate_frame(frame, track_objects, metrics_dict, risk_score, risk_level)
                
                # Update FPS
                self._frame_count += 1
                elapsed = time.time() - self._start_time
                self._process_fps = self._frame_count / elapsed if elapsed > 0 else 0
                
                # Store latest frame (Option A: drop old, keep only latest)
                with self._lock:
                    self._latest_frame = annotated  # Overwrite old frame
                    self._latest_metrics = {
                        'people_count': metrics_dict['count'],
                        'risk_score': risk_score,
                        'risk_level': risk_level,
                        'density': metrics_dict['density'],
                        'fps': self._process_fps
                    }
                
                # Rate limiting
                process_time = time.time() - loop_start
                if process_time < frame_time:
                    time.sleep(frame_time - process_time)
                
            except Exception as e:
                print(f"[{self.camera_id}] Processing error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get latest annotated frame (non-blocking).
        Option A: Returns last frame if new one not ready.
        
        Returns:
            Annotated frame or None
        """
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None
    
    def get_metrics(self) -> Optional[Dict]:
        """Get latest metrics (non-blocking)"""
        with self._lock:
            return self._latest_metrics.copy() if self._latest_metrics is not None else None
    
    def _annotate_frame(self, frame: np.ndarray, tracks: list, metrics: dict,
                       risk_score: float, risk_level: str) -> np.ndarray:
        """Draw annotations on frame"""
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw tracks with speed colors
        for track in tracks:
            # Track.bbox is [x1, y1, x2, y2] numpy array
            x1, y1, x2, y2 = map(int, track.bbox)
            track_id = track.track_id
            
            # Speed color from velocity magnitude
            vel_mag = np.linalg.norm(track.velocity) if hasattr(track, 'velocity') else 0
            if vel_mag < 3:
                color = (0, 255, 0)  # Green
            elif vel_mag < 7:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red
            
            # Box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, f"ID:{track_id}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Info overlay (top-left)
        cv2.rectangle(annotated, (5, 5), (300, 120), (0, 0, 0), -1)
        cv2.putText(annotated, self.camera_name, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(annotated, f"People: {metrics['count']}", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(annotated, f"FPS: {self._process_fps:.1f}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(annotated, f"Density: {metrics['density']:.3f}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(annotated, f"Flow: {metrics.get('flow_collision', 0):.2f} | Panic: {metrics.get('panic_wave', 0):.2f}",
                   (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Risk display (top-right)
        risk_color = (0, 255, 0) if risk_level == "NORMAL" else (0, 165, 255) if risk_level == "WARNING" else (0, 0, 255)
        cv2.rectangle(annotated, (w-150, 5), (w-5, 90), (0, 0, 0), -1)
        cv2.rectangle(annotated, (w-150, 5), (w-5, 90), risk_color, 3)
        cv2.putText(annotated, f"{risk_score:.0f}", (w-120, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, risk_color, 3)
        cv2.putText(annotated, risk_level, (w-140, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, risk_color, 2)
        
        return annotated
