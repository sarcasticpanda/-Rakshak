"""
True Parallel Multi-Camera Processing using Multiprocessing
Each camera runs in its own process with isolated YOLO instance
"""
import cv2
import time
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, asdict
import multiprocessing as mp
from multiprocessing import Process, Queue, Event
import traceback
import os


@dataclass
class CameraConfig:
    """Configuration for a single camera"""
    camera_id: str
    name: str
    source: str  # video file path, RTSP URL, or webcam index
    location: str = "Unknown"
    target_fps: int = 10
    resolution: Optional[tuple] = None  # (width, height) or None for original


@dataclass
class CameraFrame:
    """Frame data from camera process"""
    camera_id: str
    frame_number: int
    annotated_frame: np.ndarray
    people_count: int
    risk_score: float
    risk_level: str
    density: float
    compression: float
    velocity_variance: float
    flow_collision: float
    panic_wave: float
    fps: float
    timestamp: float


def camera_worker(config_dict: dict, frame_queue: Queue, control_queue: Queue, stop_event: Event):
    """
    Worker process for a single camera.
    Runs in separate process with own YOLO instance.
    
    Args:
        config_dict: CameraConfig as dict
        frame_queue: Queue to send processed frames (maxsize=2 to drop old frames)
        control_queue: Queue to receive control commands
        stop_event: Event to signal shutdown
    """
    try:
        # Import here to avoid pickling issues
        import sys
        sys.path.insert(0, '.')
        from app.core.robust_pipeline import RobustDetectionPipeline
        from app.core.tracker import ByteTracker
        from app.core.crowd_metrics import CrowdMetrics
        import torch
        
        config = CameraConfig(**config_dict)
        
        print(f"[Worker:{config.camera_id}] Starting in PID {os.getpid()}")
        
        # GPU Memory Management
        if torch.cuda.is_available():
            device_id = torch.cuda.current_device()
            gpu_mem_before = torch.cuda.memory_allocated(device_id) / 1024**2  # MB
            print(f"[Worker:{config.camera_id}] GPU {device_id} memory before: {gpu_mem_before:.0f} MB")
        
        # Open video source
        cap = cv2.VideoCapture(config.source)
        if not cap.isOpened():
            print(f"[Worker:{config.camera_id}] ❌ Failed to open source: {config.source}")
            return
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        source_fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"[Worker:{config.camera_id}] Source: {width}x{height} @ {source_fps:.1f} FPS")
        
        # Initialize AI pipeline (each process gets own instances)
        detector = RobustDetectionPipeline(enable_heatmap=True)
        tracker = ByteTracker(
            track_thresh=0.05,
            match_thresh=0.20,
            min_hits=1,
            max_age=20
        )
        metrics_calc = CrowdMetrics()
        
        # GPU memory after loading
        if torch.cuda.is_available():
            gpu_mem_after = torch.cuda.memory_allocated(device_id) / 1024**2
            print(f"[Worker:{config.camera_id}] GPU memory after: {gpu_mem_after:.0f} MB (Δ {gpu_mem_after - gpu_mem_before:.0f} MB)")
        
        print(f"[Worker:{config.camera_id}] ✅ Ready")
        
        frame_count = 0
        start_time = time.time()
        frame_time = 1.0 / config.target_fps
        
        while not stop_event.is_set():
            loop_start = time.time()
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                # Loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            # Optional resize
            if config.resolution:
                frame = cv2.resize(frame, config.resolution)
            
            h, w = frame.shape[:2]
            
            # Process frame
            try:
                # Detection
                detections, _ = detector.detect(frame)
                
                # Tracking
                tracks = tracker.update(detections, (h, w), detector.heatmap)
                
                # Metrics (use tracks, not tracker.tracks)
                metrics_dict = metrics_calc.calculate(tracks, (h, w), detector.heatmap)
                risk_score = metrics_calc.calculate_risk_score(metrics_dict)
                
                # Risk level
                if risk_score < 40:
                    risk_level = "NORMAL"
                elif risk_score < 70:
                    risk_level = "WARNING"
                else:
                    risk_level = "CRITICAL"
                
                # Annotate
                annotated = _annotate_frame(frame, tracks, metrics_dict, risk_score, risk_level, config.name)
                
                # Calculate FPS
                frame_count += 1
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                
                # Create frame data
                camera_frame = CameraFrame(
                    camera_id=config.camera_id,
                    frame_number=frame_count,
                    annotated_frame=annotated,
                    people_count=metrics_dict['count'],
                    risk_score=risk_score,
                    risk_level=risk_level,
                    density=metrics_dict['density'],
                    compression=metrics_dict['compression'],
                    velocity_variance=metrics_dict['velocity_variance'],
                    flow_collision=metrics_dict.get('flow_collision', 0),
                    panic_wave=metrics_dict.get('panic_wave', 0),
                    fps=fps,
                    timestamp=time.time()
                )
                
                # Send to queue (non-blocking, drop if full)
                try:
                    frame_queue.put_nowait(camera_frame)
                except:
                    # Queue full, drop frame (Option A: drop old frames)
                    try:
                        frame_queue.get_nowait()  # Remove old
                        frame_queue.put_nowait(camera_frame)  # Add new
                    except:
                        pass
                
                # Log every 60 frames
                if frame_count % 60 == 0:
                    print(f"[Worker:{config.camera_id}] Frame {frame_count} | {metrics_dict['count']} people | Risk: {risk_score:.0f} | FPS: {fps:.1f}")
                
            except Exception as e:
                print(f"[Worker:{config.camera_id}] Processing error: {e}")
                traceback.print_exc()
            
            # Rate limiting
            process_time = time.time() - loop_start
            if process_time < frame_time:
                time.sleep(frame_time - process_time)
        
        print(f"[Worker:{config.camera_id}] Shutting down...")
        cap.release()
        
        # Final GPU memory
        if torch.cuda.is_available():
            gpu_mem_final = torch.cuda.memory_allocated(device_id) / 1024**2
            print(f"[Worker:{config.camera_id}] GPU memory at exit: {gpu_mem_final:.0f} MB")
        
    except Exception as e:
        print(f"[Worker:{config.camera_id}] Fatal error: {e}")
        traceback.print_exc()


def _annotate_frame(frame: np.ndarray, tracks: list, metrics: dict, 
                    risk_score: float, risk_level: str, camera_name: str) -> np.ndarray:
    """Draw annotations on frame"""
    annotated = frame.copy()
    h, w = frame.shape[:2]
    
    # Draw tracks
    for track in tracks:
        x1, y1, x2, y2 = map(int, track.tlbr)
        track_id = track.track_id
        
        # Speed color
        speed = track.velocity_magnitude if hasattr(track, 'velocity_magnitude') else 0
        if speed < 3:
            color = (0, 255, 0)  # Green
        elif speed < 7:
            color = (0, 255, 255)  # Yellow
        else:
            color = (0, 0, 255)  # Red
        
        # Box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated, f"ID:{track_id}", (x1, y1-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Info overlay
    cv2.rectangle(annotated, (5, 5), (280, 110), (0, 0, 0), -1)
    cv2.putText(annotated, camera_name, (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(annotated, f"People: {metrics['count']}", (10, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(annotated, f"Density: {metrics['density']:.2f}", (10, 70),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(annotated, f"Flow: {metrics.get('flow_collision', 0):.2f} | Panic: {metrics.get('panic_wave', 0):.2f}",
               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    # Risk display
    risk_color = (0, 255, 0) if risk_level == "NORMAL" else (0, 165, 255) if risk_level == "WARNING" else (0, 0, 255)
    cv2.rectangle(annotated, (w-150, 10), (w-10, 80), (0, 0, 0), -1)
    cv2.rectangle(annotated, (w-150, 10), (w-10, 80), risk_color, 3)
    cv2.putText(annotated, f"{risk_score:.0f}", (w-130, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, risk_color, 3)
    cv2.putText(annotated, risk_level, (w-140, 73),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, risk_color, 2)
    
    return annotated


class ParallelCameraManager:
    """
    Manages multiple camera processes for true parallel processing.
    Each camera runs in separate process with own YOLO instance.
    """
    
    def __init__(self, max_cameras: int = 10):
        """
        Initialize manager.
        
        Args:
            max_cameras: Maximum number of simultaneous cameras (GPU memory limit)
        """
        self.max_cameras = max_cameras
        self.cameras: Dict[str, Dict] = {}
        self._lock = mp.Lock()
        
        print(f"[ParallelCameraManager] Initialized (max {max_cameras} cameras)")
    
    def add_camera(self, config: CameraConfig) -> bool:
        """
        Add a new camera.
        
        Args:
            config: CameraConfig
            
        Returns:
            True if added successfully
        """
        with self._lock:
            if len(self.cameras) >= self.max_cameras:
                print(f"[ParallelCameraManager] ❌ Max cameras reached ({self.max_cameras})")
                return False
            
            if config.camera_id in self.cameras:
                print(f"[ParallelCameraManager] ❌ Camera {config.camera_id} already exists")
                return False
            
            # Create queues and events
            frame_queue = mp.Queue(maxsize=2)  # Small queue, drop old frames
            control_queue = mp.Queue()
            stop_event = mp.Event()
            
            # Create process
            process = Process(
                target=camera_worker,
                args=(asdict(config), frame_queue, control_queue, stop_event),
                daemon=True
            )
            
            self.cameras[config.camera_id] = {
                'config': config,
                'process': process,
                'frame_queue': frame_queue,
                'control_queue': control_queue,
                'stop_event': stop_event,
                'running': False,
                'latest_frame': None
            }
            
            print(f"[ParallelCameraManager] Added camera: {config.camera_id} ({config.name})")
            return True
    
    def start_camera(self, camera_id: str) -> bool:
        """Start a specific camera"""
        with self._lock:
            if camera_id not in self.cameras:
                return False
            
            cam = self.cameras[camera_id]
            if not cam['running']:
                cam['process'].start()
                cam['running'] = True
                print(f"[ParallelCameraManager] Started camera: {camera_id}")
            return True
    
    def start_all(self):
        """Start all cameras simultaneously"""
        print(f"[ParallelCameraManager] Starting {len(self.cameras)} cameras...")
        for camera_id in list(self.cameras.keys()):
            self.start_camera(camera_id)
        time.sleep(2)  # Give processes time to initialize
        print(f"[ParallelCameraManager] All cameras started")
    
    def stop_camera(self, camera_id: str):
        """Stop a specific camera"""
        with self._lock:
            if camera_id not in self.cameras:
                return
            
            cam = self.cameras[camera_id]
            if cam['running']:
                cam['stop_event'].set()
                cam['process'].join(timeout=3.0)
                if cam['process'].is_alive():
                    cam['process'].terminate()
                cam['running'] = False
                print(f"[ParallelCameraManager] Stopped camera: {camera_id}")
    
    def stop_all(self):
        """Stop all cameras"""
        print(f"[ParallelCameraManager] Stopping all cameras...")
        for camera_id in list(self.cameras.keys()):
            self.stop_camera(camera_id)
        print(f"[ParallelCameraManager] All cameras stopped")
    
    def get_frames(self) -> Dict[str, CameraFrame]:
        """
        Get latest frames from all cameras (non-blocking).
        
        Returns:
            Dict mapping camera_id to CameraFrame
        """
        frames = {}
        
        for camera_id, cam in self.cameras.items():
            # Get latest frame from queue (non-blocking)
            try:
                while not cam['frame_queue'].empty():
                    cam['latest_frame'] = cam['frame_queue'].get_nowait()
            except:
                pass
            
            # Return cached latest frame
            if cam['latest_frame'] is not None:
                frames[camera_id] = cam['latest_frame']
        
        return frames
    
    def get_stats(self) -> Dict:
        """Get global statistics"""
        frames = self.get_frames()
        
        total_people = sum(f.people_count for f in frames.values())
        max_risk = max((f.risk_score for f in frames.values()), default=0)
        active_cameras = sum(1 for cam in self.cameras.values() if cam['running'])
        
        return {
            'total_cameras': len(self.cameras),
            'active_cameras': active_cameras,
            'total_people': total_people,
            'max_risk': max_risk,
            'cameras': {
                cid: {
                    'people': f.people_count,
                    'risk': f.risk_score,
                    'level': f.risk_level,
                    'fps': f.fps
                } for cid, f in frames.items()
            }
        }
    
    def remove_camera(self, camera_id: str):
        """Remove a camera"""
        self.stop_camera(camera_id)
        with self._lock:
            if camera_id in self.cameras:
                del self.cameras[camera_id]
                print(f"[ParallelCameraManager] Removed camera: {camera_id}")
