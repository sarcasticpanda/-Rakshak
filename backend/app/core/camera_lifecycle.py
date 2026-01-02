"""
Camera Lifecycle Manager - Thread-based Camera Orchestration
Handles ONLY start/stop/restart - NO analytics
Note: Using threads instead of processes for simpler IPC on Windows
"""
from threading import Thread as Process, Event
import time
from typing import Dict, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.core.camera_pipeline import CameraPipeline, CameraConfig
from app.core.shared_store import shared_store


@dataclass
class CameraProcess:
    """Wrapper for camera process"""
    process: Process
    config: CameraConfig
    stop_event: Event
    started_at: float


def run_camera_pipeline(config: CameraConfig, stop_event: Event):
    """
    Run camera pipeline in isolated process
    
    Args:
        config: Camera configuration
        stop_event: Event to signal shutdown
    """
    try:
        # Update shared store status
        shared_store.update_status(config.camera_id, "starting")
        
        # Create and start pipeline
        pipeline = CameraPipeline(config)
        
        if not pipeline.connect():
            error_msg = f"Failed to connect to source: {config.source}"
            print(f"[ERROR] Camera {config.camera_id}: {error_msg}")
            shared_store.update_status(config.camera_id, "error", error_msg)
            return
        
        # Start processing
        pipeline.start()
        shared_store.update_status(config.camera_id, "running")
        
        # Wait for first frame (up to 15 seconds - YOLO loading is slow)
        print(f"[CameraLifecycle:{config.camera_id}] Waiting for first frame...")
        wait_start = time.time()
        while time.time() - wait_start < 15.0:
            if pipeline.get_frame() is not None:
                print(f"[CameraLifecycle:{config.camera_id}] ✅ First frame ready")
                break
            time.sleep(0.1)
        else:
            error_msg = "Timeout waiting for first frame"
            print(f"[ERROR] Camera {config.camera_id}: {error_msg}")
            shared_store.update_status(config.camera_id, "error", error_msg)
            return
        
        # Main loop - publish frames and metrics
        while not stop_event.is_set():
            try:
                # Get latest frame and metrics
                frame = pipeline.get_frame()
                metrics = pipeline.get_metrics()
                
                if frame is not None:
                    shared_store.update_frame(config.camera_id, frame)
                
                if metrics:
                    # Add observability metrics
                    metrics_dict = {
                        'camera_id': config.camera_id,
                        'people_count': metrics.people_count,
                        'density': metrics.density,
                        'density_normalized': metrics.density_normalized,  # Add normalized density
                        'risk_score': metrics.risk_score,
                        'risk_level': metrics.risk_level,
                        'compression': metrics.compression,
                        'velocity_variance': metrics.velocity_variance,
                        'flow_collision': metrics.flow_collision,
                        'panic_wave': metrics.panic_wave,
                        'prediction': metrics.prediction,
                        'trend': metrics.trend,
                        'timestamp': time.time(),
                        # Observability
                        'capture_fps': pipeline._fps,
                        'processing_fps': pipeline._fps,
                        'latency_ms': metrics.latency_ms,
                        'queue_depth': 0
                    }
                    shared_store.update_metrics(config.camera_id, metrics_dict)
                
                time.sleep(0.033)  # ~30 Hz update rate
                
            except Exception as e:
                print(f"[ERROR] Camera {config.camera_id} runtime error: {e}")
                shared_store.update_status(config.camera_id, "error", str(e))
                time.sleep(1.0)
        
        # Cleanup
        pipeline.stop()
        pipeline.disconnect()
        shared_store.update_status(config.camera_id, "stopped")
        
    except Exception as e:
        print(f"[ERROR] Camera {config.camera_id} startup failed: {e}")
        shared_store.update_status(config.camera_id, "error", str(e))


class CameraLifecycleManager:
    """
    Manages camera lifecycle - ONLY start/stop/restart
    
    Design:
    - One camera = one OS process
    - No analytics (that's MetricsAggregator's job)
    - Fault isolation (one crash won't affect others)
    """
    
    def __init__(self):
        self.processes: Dict[str, CameraProcess] = {}
        self.configs: Dict[str, CameraConfig] = {}
    
    def start_camera(self, config: CameraConfig) -> bool:
        """
        Start camera in isolated process
        
        Args:
            config: Camera configuration
            
        Returns:
            True if started successfully
        """
        camera_id = config.camera_id
        
        # Check if already running
        if camera_id in self.processes:
            if self.processes[camera_id].process.is_alive():
                print(f"[CameraLifecycle] Camera {camera_id} already running")
                return False
            else:
                # Process dead, clean up
                self.stop_camera(camera_id)
        
        # Create stop event and process
        stop_event = Event()
        process = Process(
            target=run_camera_pipeline,
            args=(config, stop_event),
            daemon=False,
            name=f"Camera-{camera_id}"
        )
        
        # Start process
        process.start()
        
        # Store process info
        self.processes[camera_id] = CameraProcess(
            process=process,
            config=config,
            stop_event=stop_event,
            started_at=time.time()
        )
        self.configs[camera_id] = config
        
        print(f"[CameraLifecycle] Started camera {camera_id} (Thread: {process.name})")
        return True
    
    def stop_camera(self, camera_id: str) -> bool:
        """
        Stop camera process
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            True if stopped successfully
        """
        if camera_id not in self.processes:
            print(f"[CameraLifecycle] Camera {camera_id} not found")
            return False
        
        cam_process = self.processes[camera_id]
        
        # Signal stop
        cam_process.stop_event.set()
        
        # Wait for graceful shutdown
        cam_process.process.join(timeout=5.0)
        
        # Force terminate if needed
        if cam_process.process.is_alive():
            print(f"[CameraLifecycle] Force terminating {camera_id}")
            cam_process.process.terminate()
            cam_process.process.join(timeout=2.0)
        
        # Cleanup
        shared_store.remove_camera(camera_id)
        del self.processes[camera_id]
        del self.configs[camera_id]
        
        print(f"[CameraLifecycle] Stopped camera {camera_id}")
        return True
    
    def restart_camera(self, camera_id: str) -> bool:
        """Restart camera"""
        if camera_id not in self.configs:
            return False
        
        config = self.configs[camera_id]
        self.stop_camera(camera_id)
        time.sleep(1.0)
        return self.start_camera(config)
    
    def get_camera_status(self, camera_id: str) -> Optional[Dict]:
        """Get camera status"""
        if camera_id not in self.processes:
            return None
        
        cam_process = self.processes[camera_id]
        state = shared_store.get_state(camera_id)
        
        return {
            'camera_id': camera_id,
            'status': state.status if state else 'unknown',
            'thread_id': cam_process.process.ident,
            'is_alive': cam_process.process.is_alive(),
            'uptime_seconds': time.time() - cam_process.started_at,
            'error': state.error if state else None
        }
    
    def list_cameras(self) -> list[Dict]:
        """List all cameras with status"""
        return [
            self.get_camera_status(cam_id)
            for cam_id in self.processes.keys()
        ]
    
    def stop_all(self) -> None:
        """Stop all cameras"""
        camera_ids = list(self.processes.keys())
        for camera_id in camera_ids:
            self.stop_camera(camera_id)


# Global singleton instance
camera_manager = CameraLifecycleManager()
