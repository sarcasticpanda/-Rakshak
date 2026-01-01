"""
FastAPI Main Server - Control Plane
Handles HTTP/WebSocket/MJPEG - NO AI processing
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import multiprocessing

from app.api import cameras, streams, websocket, health, areas, history
from app.core.metrics_aggregator import metrics_aggregator
from app.core.camera_lifecycle import camera_manager
from app.core.area_risk_engine import area_risk_engine
from app.core.metrics_writer import metrics_writer
from app.db.connection import init_db, close_db, get_database
from app.db.repositories import CameraRepository, AreaRepository
from app.core.camera_pipeline import CameraConfig
from app.models.area_config import AreaConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager - startup and shutdown events
    """
    # Startup
    print("=" * 60)
    print("🚀 STAMPEDE DETECTION SYSTEM - CONTROL PLANE")
    print("=" * 60)
    
    # Initialize MongoDB
    print("\n[Startup] Connecting to MongoDB...")
    await init_db()
    
    # Restore cameras from database
    print("[Startup] Restoring cameras from database...")
    await restore_cameras()
    
    # Restore areas from database
    print("[Startup] Restoring areas from database...")
    await restore_areas()
    
    # Start metrics writer
    print("[Startup] Starting metrics writer...")
    await metrics_writer.start()
    print("[Startup] ✅ Metrics writer running")
    
    print("[Startup] Starting metrics aggregator...")
    await metrics_aggregator.start()
    print("[Startup] ✅ Metrics aggregator running @ 1Hz")
    
    print("\n" + "=" * 60)
    print("✅ Server ready!")
    print("=" * 60)
    print("\n📡 Endpoints:")
    print("  • REST API: http://localhost:8000/docs")
    print("  • Cameras: http://localhost:8000/cameras")
    print("  • Areas: http://localhost:8000/areas")
    print("  • History: http://localhost:8000/history/cameras/{id}")
    print("  • MJPEG Stream: http://localhost:8000/stream/{camera_id}")
    print("  • WebSocket: ws://localhost:8000/ws/metrics")
    print("  • Health: http://localhost:8000/health")
    print("\n💡 Add cameras via: POST /cameras")
    print("💡 Create areas via: POST /areas")
    print("\n" + "=" * 60 + "\n")
    
    yield
    
    # Shutdown
    print("\n[Shutdown] Stopping metrics writer...")
    await metrics_writer.stop()
    print("[Shutdown] Stopping metrics aggregator...")
    await metrics_aggregator.stop()
    print("[Shutdown] Stopping all cameras...")
    camera_manager.stop_all()
    print("[Shutdown] Closing MongoDB...")
    await close_db()
    print("[Shutdown] ✅ Clean shutdown complete")
    print("[Shutdown] ✅ Clean shutdown complete")


async def restore_cameras():
    """Restore cameras from MongoDB on startup"""
    try:
        db = get_database()
        if db is None:
            print("[Startup] MongoDB not available - skipping camera restoration")
            return
        
        repo = CameraRepository(db)
        cameras = await repo.list(enabled_only=True)
        
        if not cameras:
            print("[Startup] No cameras found in database")
            return
        
        print(f"[Startup] Found {len(cameras)} cameras in database")
        
        for cam_doc in cameras:
            try:
                config = CameraConfig(
                    camera_id=cam_doc['camera_id'],
                    name=cam_doc['name'],
                    source=cam_doc['source'],
                    location=cam_doc['location'],
                    context=cam_doc.get('context', 'general'),
                    enabled=cam_doc.get('enabled', True),
                    target_fps=cam_doc.get('target_fps', 15),
                    resolution=tuple(cam_doc['resolution']) if cam_doc.get('resolution') else None,
                    warning_threshold=cam_doc.get('warning_threshold', 40.0),
                    critical_threshold=cam_doc.get('critical_threshold', 70.0)
                )
                
                success = camera_manager.start_camera(config)
                if success:
                    print(f"  ✅ Restored: {config.name}")
                else:
                    print(f"  ❌ Failed to restore: {config.name}")
            except Exception as e:
                print(f"  ❌ Error restoring camera {cam_doc.get('camera_id', 'unknown')}: {e}")
    
    except Exception as e:
        print(f"[Startup] Error restoring cameras: {e}")


async def restore_areas():
    """Restore areas from MongoDB on startup"""
    try:
        db = get_database()
        if db is None:
            print("[Startup] MongoDB not available - skipping area restoration")
            return
        
        repo = AreaRepository(db)
        areas = await repo.list(enabled_only=False)  # Get all areas, filter by enabled field below
        
        if not areas:
            print("[Startup] No areas found in database")
            return
        
        print(f"[Startup] Found {len(areas)} areas in database")
        
        for area_doc in areas:
            try:
                config = AreaConfig(
                    area_id=area_doc['area_id'],
                    name=area_doc['name'],
                    description=area_doc.get('description', ''),
                    camera_ids=area_doc['camera_ids'],
                    context_type=area_doc.get('context_type', 'general'),
                    warning_threshold=area_doc.get('warning_threshold', 40.0),
                    critical_threshold=area_doc.get('critical_threshold', 70.0),
                    max_capacity=area_doc.get('max_capacity'),
                    enabled=area_doc.get('enabled', True)
                )
                
                area_risk_engine.add_area(config)
                print(f"  ✅ Restored: {config.name}")
            except Exception as e:
                print(f"  ❌ Error restoring area {area_doc.get('area_id', 'unknown')}: {e}")
    
    except Exception as e:
        print(f"[Startup] Error restoring areas: {e}")


# Create FastAPI app
app = FastAPI(
    title="Stampede Detection System",
    description="Real-time multi-camera crowd risk monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cameras.router)
app.include_router(areas.router)
app.include_router(history.router)
app.include_router(streams.router)
app.include_router(websocket.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Stampede Detection System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "cameras": "/cameras",
            "areas": "/areas",
            "stream": "/stream/{camera_id}",
            "websocket": "/ws/metrics",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable in production
        log_level="info"
    )
