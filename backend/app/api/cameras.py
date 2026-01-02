"""
Camera Management API - CRUD Operations
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.camera_lifecycle import camera_manager
from app.core.camera_pipeline import CameraConfig
from app.db.connection import get_database
from app.db.repositories import CameraRepository
from app.core.shared_store import shared_store  # CRITICAL FIX: Access to latest metrics


router = APIRouter(prefix="/cameras", tags=["cameras"])


class CameraCreateRequest(BaseModel):
    """Request model for creating a camera"""
    camera_id: str
    name: str
    source: str  # RTSP URL, file path, or webcam index
    location: str = "Unknown"
    context: str = "general"
    enabled: bool = True
    target_fps: int = 15
    resolution: Optional[tuple[int, int]] = None


class CameraResponse(BaseModel):
    """Response model for camera info"""
    camera_id: str
    name: str
    source: str
    location: str
    status: str
    thread_id: Optional[int] = None
    is_alive: bool = False
    uptime_seconds: float = 0.0
    error: Optional[str] = None
    latest_metrics: Optional[dict] = None  # CRITICAL FIX: Include latest metrics from SharedStore


@router.post("/", response_model=CameraResponse)
async def create_camera(request: CameraCreateRequest):
    """
    Create and start a new camera
    
    Args:
        request: Camera configuration
        
    Returns:
        Camera status
    """
    # Check if camera already exists
    if request.camera_id in camera_manager.processes:
        raise HTTPException(
            status_code=400, 
            detail=f"Camera '{request.camera_id}' already exists. Use a different camera_id or delete the existing one first."
        )
    
    # Create config
    try:
        config = CameraConfig(
            camera_id=request.camera_id,
            name=request.name,
            source=request.source,
            location=request.location,
            context=request.context,
            enabled=request.enabled,
            target_fps=request.target_fps,
            resolution=request.resolution
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
    
    # Start camera
    success = camera_manager.start_camera(config)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Failed to start camera. Check if the video source exists and is accessible."
        )
    
    # Persist to MongoDB (non-blocking, fails gracefully)
    try:
        db = get_database()
        if db is not None:
            repo = CameraRepository(db)
            await repo.create(config)
    except Exception as e:
        print(f"[Camera API] Warning: Failed to persist to database: {e}")
        # Continue - camera is running
    
    # Get status
    status = camera_manager.get_camera_status(request.camera_id)
    
    if not status:
        raise HTTPException(status_code=500, detail="Camera started but status unavailable")
    
    # CRITICAL FIX: Get latest metrics from SharedStore
    latest_metrics = shared_store.get_metrics(request.camera_id)
    
    return CameraResponse(
        camera_id=status['camera_id'],
        name=request.name,
        source=request.source,
        location=request.location,
        status=status.get('status', 'unknown'),
        thread_id=status.get('thread_id'),
        is_alive=status.get('is_alive', False),
        uptime_seconds=status.get('uptime_seconds', 0.0),
        error=status.get('error'),
        latest_metrics=latest_metrics
    )


@router.get("/", response_model=List[CameraResponse])
async def list_cameras():
    """
    List all cameras
    
    Returns:
        List of camera statuses
    """
    cameras = camera_manager.list_cameras()
    
    result = []
    for cam in cameras:
        try:
            cam_id = cam.get('camera_id')
            if not cam_id:
                continue
            
            # Get config safely
            config = camera_manager.configs.get(cam_id)
            if not config:
                print(f"[API] Warning: Config missing for camera {cam_id}")
                continue
                
            # CRITICAL FIX: Get latest metrics from SharedStore
            latest_metrics = shared_store.get_metrics(cam_id)
            
            result.append(CameraResponse(
                camera_id=cam_id,
                name=config.name,
                source=config.source,
                location=config.location,
                status=cam.get('status', 'unknown'),
                thread_id=cam.get('thread_id'),
                is_alive=cam.get('is_alive', False),
                uptime_seconds=cam.get('uptime_seconds', 0.0),
                error=cam.get('error'),
                latest_metrics=latest_metrics
            ))
        except Exception as e:
            print(f"[API] Error processing camera {cam.get('camera_id', 'unknown')}: {e}")
            continue
    
    return result


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: str):
    """
    Get camera by ID
    
    Args:
        camera_id: Camera identifier
        
    Returns:
        Camera status
    """
    status = camera_manager.get_camera_status(camera_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    
    # Get config safely
    config = camera_manager.configs.get(camera_id)
    if not config:
        raise HTTPException(status_code=500, detail=f"Camera '{camera_id}' exists but config is missing")
    
    # CRITICAL FIX: Get latest metrics from SharedStore
    latest_metrics = shared_store.get_metrics(camera_id)
    
    return CameraResponse(
        camera_id=status['camera_id'],
        name=config.name,
        source=config.source,
        location=config.location,
        status=status.get('status', 'unknown'),
        thread_id=status.get('thread_id'),
        is_alive=status.get('is_alive', False),
        uptime_seconds=status.get('uptime_seconds', 0.0),
        error=status.get('error'),
        latest_metrics=latest_metrics
    )


@router.post("/{camera_id}/start")
async def start_camera(camera_id: str):
    """Start a stopped camera"""
    config = camera_manager.configs.get(camera_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    
    success = camera_manager.start_camera(config)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start camera")
    
    return {"status": "started", "camera_id": camera_id}


@router.post("/{camera_id}/stop")
async def stop_camera(camera_id: str):
    """Stop a running camera"""
    success = camera_manager.stop_camera(camera_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    
    return {"status": "stopped", "camera_id": camera_id}


@router.post("/{camera_id}/restart")
async def restart_camera(camera_id: str):
    """Restart a camera"""
    success = camera_manager.restart_camera(camera_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    
    return {"status": "restarted", "camera_id": camera_id}


@router.delete("/{camera_id}")
async def delete_camera(camera_id: str):
    """Delete a camera"""
    success = camera_manager.stop_camera(camera_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    
    # Remove from configs
    if camera_id in camera_manager.configs:
        del camera_manager.configs[camera_id]
    
    # Delete from MongoDB (non-blocking, fails gracefully)
    try:
        db = get_database()
        if db is not None:
            repo = CameraRepository(db)
            await repo.delete(camera_id)
    except Exception as e:
        print(f"[Camera API] Warning: Failed to delete from database: {e}")
    
    return {"status": "deleted", "camera_id": camera_id}


@router.get("/{camera_id}/metrics/latest")
async def get_latest_metrics(camera_id: str):
    """
    Get latest metrics for a camera (FALLBACK ENDPOINT)
    
    Use this endpoint when WebSocket connection fails.
    Frontend can poll this every 2 seconds as fallback.
    
    Args:
        camera_id: Camera identifier
        
    Returns:
        Latest metrics from SharedStore
    """
    metrics = shared_store.get_metrics(camera_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics available for camera '{camera_id}'")
    
    return {
        "camera_id": camera_id,
        "metrics": metrics,
        "timestamp": metrics.get('timestamp', 0)
    }


@router.get("/metrics/latest")
async def get_all_latest_metrics():
    """
    Get latest metrics for ALL cameras (FALLBACK ENDPOINT)
    
    Use this endpoint when WebSocket connection fails.
    Frontend can poll this every 2 seconds as fallback.
    
    Returns:
        All camera metrics from SharedStore
    """
    all_metrics = shared_store.get_all_metrics()
    
    # Format to match WebSocket message format
    cameras_data = {}
    for cam_id, metrics in all_metrics.items():
        if metrics:  # Only include cameras with metrics
            cameras_data[cam_id] = metrics
    
    return {
        "timestamp": __import__('time').time(),
        "cameras": cameras_data
    }
