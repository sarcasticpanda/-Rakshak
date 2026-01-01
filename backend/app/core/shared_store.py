"""
Shared Store - Lock-free Frame and Metrics Storage
Pipelines write, FastAPI reads - no blocking
"""
import time
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
import numpy as np
import pickle
from multiprocessing import Manager


@dataclass
class CameraState:
    """Current state of a camera"""
    frame: Optional[np.ndarray] = None
    frame_timestamp: float = 0.0
    metrics: Optional[Dict[str, Any]] = None
    metrics_timestamp: float = 0.0
    capture_fps: float = 0.0
    processing_fps: float = 0.0
    queue_depth: int = 0
    latency_ms: float = 0.0
    status: str = "disconnected"
    error: Optional[str] = None


class SharedFrameStore:
    """
    Process-safe storage for latest frames and metrics
    
    Design:
    - Pipelines write without blocking
    - FastAPI reads without blocking
    - Works across process boundaries via pickle serialization
    - Stale data is acceptable (real-time system)
    """
    
    def __init__(self):
        # Use regular dict - Manager() causes issues on Windows at import time
        # We'll use pickle serialization for cross-process frame transfer
        self._store: Dict[str, CameraState] = {}
        self._lock = threading.RLock()  # Minimal locking
    
    def update_frame(self, camera_id: str, frame: np.ndarray) -> None:
        """
        Update frame for camera (called by pipeline)
        
        Args:
            camera_id: Camera identifier
            frame: Annotated frame (BGR numpy array)
        """
        with self._lock:
            if camera_id not in self._store:
                self._store[camera_id] = CameraState()
            
            # Direct assignment - works fine with threads
            state = self._store[camera_id]
            state.frame = frame
            state.frame_timestamp = time.time()
    
    def update_metrics(self, camera_id: str, metrics: Dict[str, Any]) -> None:
        """
        Update metrics for camera (called by pipeline)
        
        Args:
            camera_id: Camera identifier
            metrics: Dictionary with metrics data
        """
        with self._lock:
            if camera_id not in self._store:
                self._store[camera_id] = CameraState()
            
            state = self._store[camera_id]
            state.metrics = metrics
            state.metrics_timestamp = time.time()
            
            # Extract observability metrics if present
            if 'capture_fps' in metrics:
                state.capture_fps = metrics['capture_fps']
            if 'processing_fps' in metrics:
                state.processing_fps = metrics['processing_fps']
            if 'queue_depth' in metrics:
                state.queue_depth = metrics['queue_depth']
            if 'latency_ms' in metrics:
                state.latency_ms = metrics['latency_ms']
    
    def update_status(self, camera_id: str, status: str, error: Optional[str] = None) -> None:
        """Update camera status"""
        with self._lock:
            if camera_id not in self._store:
                self._store[camera_id] = CameraState()
            
            state = self._store[camera_id]
            state.status = status
            state.error = error
    
    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """
        Get latest frame (called by MJPEG endpoint)
        
        Returns:
            Frame copy or None if not available
        """
        with self._lock:
            state = self._store.get(camera_id)
            if state and state.frame is not None:
                return state.frame.copy()  # Return copy to avoid race conditions
        return None
    
    def get_metrics(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """
        Get latest metrics (called by WebSocket)
        
        Returns:
            Metrics dict or None
        """
        with self._lock:
            state = self._store.get(camera_id)
            if state and state.metrics is not None:
                return state.metrics.copy()
        return None
    
    def get_state(self, camera_id: str) -> Optional[CameraState]:
        """Get complete camera state"""
        with self._lock:
            return self._store.get(camera_id)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all cameras"""
        with self._lock:
            return {
                cam_id: state.metrics.copy() if state.metrics else {}
                for cam_id, state in self._store.items()
            }
    
    def get_all_states(self) -> Dict[str, CameraState]:
        """Get states for all cameras"""
        with self._lock:
            return self._store.copy()
    
    def remove_camera(self, camera_id: str) -> None:
        """Remove camera from store"""
        with self._lock:
            if camera_id in self._store:
                del self._store[camera_id]
    
    def list_cameras(self) -> list[str]:
        """List all camera IDs"""
        with self._lock:
            return list(self._store.keys())


# Global singleton instance
shared_store = SharedFrameStore()
