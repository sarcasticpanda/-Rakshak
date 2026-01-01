"""
Health & Observability API
"""
from fastapi import APIRouter
from app.core.shared_store import shared_store
from app.core.camera_lifecycle import camera_manager
from app.core.metrics_writer import metrics_writer
from app.db.connection import is_db_connected
import psutil
import time


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def get_health():
    """
    Get system health status
    
    Returns:
        System-wide health metrics
    """
    all_states = shared_store.get_all_states()
    
    # Per-camera health
    cameras_health = {}
    for camera_id, state in all_states.items():
        cameras_health[camera_id] = {
            'status': state.status,
            'capture_fps': state.capture_fps,
            'processing_fps': state.processing_fps,
            'queue_depth': state.queue_depth,
            'latency_ms': state.latency_ms,
            'last_frame_age': time.time() - state.frame_timestamp if state.frame_timestamp else None,
            'last_metrics_age': time.time() - state.metrics_timestamp if state.metrics_timestamp else None,
            'error': state.error
        }
    
    # System health
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    system_health = {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_used_gb': memory.used / (1024**3),
        'memory_total_gb': memory.total / (1024**3)
    }
    
    # Try to get GPU info
    try:
        import torch
        if torch.cuda.is_available():
            system_health['gpu_available'] = True
            system_health['gpu_memory_allocated_gb'] = torch.cuda.memory_allocated() / (1024**3)
            system_health['gpu_memory_reserved_gb'] = torch.cuda.memory_reserved() / (1024**3)
    except:
        system_health['gpu_available'] = False
    
    # MongoDB health
    mongodb_health = metrics_writer.get_health()
    
    # Overall status determination
    overall_status = 'healthy'
    if len(cameras_health) == 0:
        overall_status = 'idle'
    elif mongodb_health['mongo_status'] == 'critical':
        overall_status = 'degraded'
    elif any(cam.get('status') == 'error' for cam in cameras_health.values()):
        overall_status = 'degraded'
    
    return {
        'status': overall_status,
        'total_cameras': len(cameras_health),
        'cameras': cameras_health,
        'system': system_health,
        'mongodb': mongodb_health,
        'timestamp': time.time()
    }


@router.get("/cameras")
async def get_cameras_health():
    """Get detailed health for all cameras"""
    return {
        'cameras': [
            {
                'camera_id': cam['camera_id'],
                'status': cam['status'],
                'is_alive': cam['is_alive'],
                'uptime_seconds': cam['uptime_seconds'],
                'error': cam['error']
            }
            for cam in camera_manager.list_cameras()
        ]
    }
