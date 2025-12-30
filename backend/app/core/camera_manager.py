"""
Camera Manager - Manages multiple camera pipelines in parallel

Each camera runs in its own process for true parallelism.
No shared state between cameras.

Features:
- Add/remove cameras dynamically
- Independent processing per camera
- Centralized metrics collection
- Alert aggregation
"""
import multiprocessing as mp
from multiprocessing import Process, Queue, Event
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.core.camera_pipeline import CameraPipeline, CameraConfig, CameraMetrics, CameraStatus


@dataclass
class CameraInfo:
    """Info about a managed camera"""
    config: CameraConfig
    process: Optional[Process] = None
    status: str = "stopped"
    last_metrics: Optional[Dict] = None
    last_update: float = 0


def camera_worker(config_dict: dict, metrics_queue: Queue, control_queue: Queue, stop_event: Event):
    """
    Worker function that runs in a separate process.
    Each camera has its own YOLO model instance.
    
    Args:
        config_dict: Camera configuration as dict
        metrics_queue: Queue to send metrics back to manager
        control_queue: Queue to receive control commands
        stop_event: Event to signal shutdown
    """
    import cv2
    import numpy as np
    
    # Recreate config from dict
    config = CameraConfig(**config_dict)
    
    print(f"[Worker:{config.camera_id}] Starting...")
    
    # Create pipeline in this process
    pipeline = CameraPipeline(config)
    
    if not pipeline.connect():
        metrics_queue.put({
            "camera_id": config.camera_id,
            "status": "error",
            "error": pipeline.error_message
        })
        return
    
    # Processing loop
    frame_time = 1.0 / config.target_fps
    
    while not stop_event.is_set():
        loop_start = time.time()
        
        try:
            # Check for control commands
            try:
                cmd = control_queue.get_nowait()
                if cmd == "stop":
                    break
                elif cmd == "reset":
                    pipeline.tracker.reset()
            except:
                pass
            
            # Read and process frame
            ret, frame = pipeline.cap.read()
            if not ret:
                if pipeline.source_type.value == "video_file":
                    pipeline.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.1)
                continue
            
            # Process
            metrics = pipeline._process_frame(frame)
            
            # Send metrics to manager
            metrics_queue.put(metrics.to_dict())
            
            # Rate limiting
            elapsed = time.time() - loop_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
                
        except Exception as e:
            metrics_queue.put({
                "camera_id": config.camera_id,
                "status": "error",
                "error": str(e)
            })
            time.sleep(0.5)
    
    # Cleanup
    pipeline.disconnect()
    print(f"[Worker:{config.camera_id}] Stopped")


class CameraManager:
    """
    Manages multiple camera pipelines.
    
    Each camera runs in its own process for:
    - True parallelism (bypasses GIL)
    - Isolated memory (no state sharing)
    - Independent crash recovery
    """
    
    def __init__(self):
        self.cameras: Dict[str, CameraInfo] = {}
        self._metrics_queue = mp.Queue()
        self._running = False
        self._collector_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._on_metrics: Optional[Callable] = None
        self._on_alert: Optional[Callable] = None
        
        # Aggregated state
        self._all_metrics: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
        print("[CameraManager] Initialized")
    
    def add_camera(self, config: CameraConfig) -> bool:
        """
        Add a camera to the manager.
        
        Args:
            config: Camera configuration
            
        Returns:
            True if added successfully
        """
        if config.camera_id in self.cameras:
            print(f"[CameraManager] Camera {config.camera_id} already exists")
            return False
        
        self.cameras[config.camera_id] = CameraInfo(
            config=config,
            status="added"
        )
        
        print(f"[CameraManager] Added camera: {config.camera_id} ({config.name})")
        return True
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera from the manager"""
        if camera_id not in self.cameras:
            return False
        
        self.stop_camera(camera_id)
        del self.cameras[camera_id]
        
        with self._lock:
            if camera_id in self._all_metrics:
                del self._all_metrics[camera_id]
        
        print(f"[CameraManager] Removed camera: {camera_id}")
        return True
    
    def start_camera(self, camera_id: str) -> bool:
        """Start processing for a specific camera"""
        if camera_id not in self.cameras:
            return False
        
        cam_info = self.cameras[camera_id]
        if cam_info.process and cam_info.process.is_alive():
            return True  # Already running
        
        # Create control queue and stop event for this camera
        control_queue = mp.Queue()
        stop_event = mp.Event()
        
        # Store for later control
        cam_info.control_queue = control_queue
        cam_info.stop_event = stop_event
        
        # Convert config to dict for pickling
        config_dict = {
            "camera_id": cam_info.config.camera_id,
            "name": cam_info.config.name,
            "source": cam_info.config.source,
            "location": cam_info.config.location,
            "context": cam_info.config.context,
            "enabled": cam_info.config.enabled,
            "target_fps": cam_info.config.target_fps,
            "warning_threshold": cam_info.config.warning_threshold,
            "critical_threshold": cam_info.config.critical_threshold,
        }
        
        # Start process
        process = Process(
            target=camera_worker,
            args=(config_dict, self._metrics_queue, control_queue, stop_event),
            daemon=True
        )
        process.start()
        
        cam_info.process = process
        cam_info.status = "running"
        
        print(f"[CameraManager] Started camera: {camera_id}")
        return True
    
    def stop_camera(self, camera_id: str) -> bool:
        """Stop processing for a specific camera"""
        if camera_id not in self.cameras:
            return False
        
        cam_info = self.cameras[camera_id]
        
        if hasattr(cam_info, 'stop_event'):
            cam_info.stop_event.set()
        
        if cam_info.process and cam_info.process.is_alive():
            cam_info.process.join(timeout=3.0)
            if cam_info.process.is_alive():
                cam_info.process.terminate()
        
        cam_info.status = "stopped"
        print(f"[CameraManager] Stopped camera: {camera_id}")
        return True
    
    def start_all(self):
        """Start all cameras"""
        self._running = True
        
        # Start metrics collector thread
        self._collector_thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self._collector_thread.start()
        
        # Start each camera
        for camera_id in self.cameras:
            if self.cameras[camera_id].config.enabled:
                self.start_camera(camera_id)
        
        print(f"[CameraManager] Started {len(self.cameras)} cameras")
    
    def stop_all(self):
        """Stop all cameras"""
        self._running = False
        
        for camera_id in list(self.cameras.keys()):
            self.stop_camera(camera_id)
        
        if self._collector_thread:
            self._collector_thread.join(timeout=2.0)
        
        print("[CameraManager] All cameras stopped")
    
    def _collect_metrics(self):
        """Background thread to collect metrics from all camera processes"""
        while self._running:
            try:
                # Get metrics from queue (with timeout)
                metrics = self._metrics_queue.get(timeout=0.1)
                
                camera_id = metrics.get("camera_id")
                if camera_id:
                    # Update stored metrics
                    with self._lock:
                        self._all_metrics[camera_id] = metrics
                    
                    # Update camera info
                    if camera_id in self.cameras:
                        self.cameras[camera_id].last_metrics = metrics
                        self.cameras[camera_id].last_update = time.time()
                        self.cameras[camera_id].status = metrics.get("status", "running")
                    
                    # Callback
                    if self._on_metrics:
                        self._on_metrics(metrics)
                    
                    # Alert check
                    if self._on_alert and metrics.get("risk_level") == "CRITICAL":
                        self._on_alert(camera_id, metrics)
                        
            except:
                pass  # Queue timeout, continue
    
    def get_metrics(self, camera_id: str = None) -> Dict:
        """Get current metrics for one or all cameras"""
        with self._lock:
            if camera_id:
                return self._all_metrics.get(camera_id, {})
            return dict(self._all_metrics)
    
    def get_all_status(self) -> List[Dict]:
        """Get status of all cameras"""
        statuses = []
        for camera_id, cam_info in self.cameras.items():
            statuses.append({
                "camera_id": camera_id,
                "name": cam_info.config.name,
                "location": cam_info.config.location,
                "source_type": "unknown",  # Would need to detect
                "status": cam_info.status,
                "last_update": cam_info.last_update,
                "people_count": cam_info.last_metrics.get("people_count", 0) if cam_info.last_metrics else 0,
                "risk_level": cam_info.last_metrics.get("risk_level", "UNKNOWN") if cam_info.last_metrics else "UNKNOWN"
            })
        return statuses
    
    def get_global_stats(self) -> Dict:
        """Get aggregated stats across all cameras"""
        with self._lock:
            total_people = sum(m.get("people_count", 0) for m in self._all_metrics.values())
            max_risk = max((m.get("risk_score", 0) for m in self._all_metrics.values()), default=0)
            critical_cameras = sum(1 for m in self._all_metrics.values() if m.get("risk_level") == "CRITICAL")
            warning_cameras = sum(1 for m in self._all_metrics.values() if m.get("risk_level") == "WARNING")
            
            return {
                "total_cameras": len(self.cameras),
                "active_cameras": len(self._all_metrics),
                "total_people": total_people,
                "max_risk_score": max_risk,
                "critical_cameras": critical_cameras,
                "warning_cameras": warning_cameras,
                "timestamp": time.time()
            }
    
    def set_metrics_callback(self, callback: Callable):
        """Set callback for metrics updates"""
        self._on_metrics = callback
    
    def set_alert_callback(self, callback: Callable):
        """Set callback for critical alerts"""
        self._on_alert = callback


# ============================================================
# QUICK TEST - Multi Camera
# ============================================================
if __name__ == "__main__":
    import cv2
    
    print("="*60)
    print("CAMERA MANAGER TEST - Multi Camera")
    print("="*60)
    
    manager = CameraManager()
    
    # Add cameras (mix of sources)
    # Camera 1: IP Webcam (your phone)
    manager.add_camera(CameraConfig(
        camera_id="cam_phone",
        name="Phone Camera",
        source="http://100.115.33.220:8080/video",
        location="Mobile",
        target_fps=8
    ))
    
    # Camera 2: Video file (stampede)
    manager.add_camera(CameraConfig(
        camera_id="cam_stampede",
        name="Stampede Video",
        source="../check_vids/stampede.mp4",
        location="Test Video",
        target_fps=10
    ))
    
    # Camera 3: Another video
    manager.add_camera(CameraConfig(
        camera_id="cam_test2",
        name="Test Video 2",
        source="../check_vids/test2.mp4",
        location="Test Video",
        target_fps=10
    ))
    
    def on_metrics(metrics):
        print(f"\r[{metrics['camera_id']}] People: {metrics['people_count']} | Risk: {metrics['risk_score']:.1f} | {metrics['risk_level']}", end="")
    
    def on_alert(camera_id, metrics):
        print(f"\n🚨 ALERT from {camera_id}: Risk={metrics['risk_score']:.1f}")
    
    manager.set_metrics_callback(on_metrics)
    manager.set_alert_callback(on_alert)
    
    print("\nStarting all cameras...")
    manager.start_all()
    
    print("\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(5)
            stats = manager.get_global_stats()
            print(f"\n\n📊 Global: {stats['total_people']} people | Max Risk: {stats['max_risk_score']:.1f} | Critical: {stats['critical_cameras']}\n")
    except KeyboardInterrupt:
        pass
    
    print("\n\nStopping...")
    manager.stop_all()
    print("Done!")
