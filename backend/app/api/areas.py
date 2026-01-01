"""
Area Management API
CRUD operations for areas
"""
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.area_config import AreaConfig, AreaMetrics, AreaCreateRequest
from app.core.area_risk_engine import area_risk_engine
from app.db.connection import get_database
from app.db.repositories import AreaRepository


router = APIRouter(prefix="/areas", tags=["areas"])


@router.post("/", response_model=AreaConfig)
async def create_area(request: AreaCreateRequest):
    """Create a new area"""
    # Check if area already exists
    if area_risk_engine.get_area(request.area_id):
        raise HTTPException(
            status_code=400,
            detail=f"Area '{request.area_id}' already exists"
        )
    
    # Create area config
    config = AreaConfig(
        area_id=request.area_id,
        name=request.name,
        description=request.description,
        camera_ids=request.camera_ids,
        context_type=request.context_type,
        warning_threshold=request.warning_threshold,
        critical_threshold=request.critical_threshold,
        max_capacity=request.max_capacity
    )
    
    # Register area
    area_risk_engine.add_area(config)
    
    # Persist to MongoDB (non-blocking, fails gracefully)
    try:
        db = get_database()
        if db is not None:
            repo = AreaRepository(db)
            await repo.create(config)
    except Exception as e:
        print(f"[Area API] Warning: Failed to persist to database: {e}")
        # Continue - area is registered
    
    return config


@router.get("/", response_model=List[AreaConfig])
async def list_areas():
    """List all areas"""
    return area_risk_engine.list_areas()


@router.get("/{area_id}", response_model=AreaConfig)
async def get_area(area_id: str):
    """Get area configuration"""
    area = area_risk_engine.get_area(area_id)
    if not area:
        raise HTTPException(status_code=404, detail=f"Area '{area_id}' not found")
    return area


@router.get("/{area_id}/metrics", response_model=AreaMetrics)
async def get_area_metrics(area_id: str):
    """Get real-time metrics for an area"""
    metrics = area_risk_engine.calculate_area_metrics(area_id)
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Area '{area_id}' not found or has no active cameras"
        )
    return metrics

    # Delete from MongoDB (non-blocking, fails gracefully)
    try:
        db = get_database()
        if db is not None:
            repo = AreaRepository(db)
            await repo.delete(area_id)
    except Exception as e:
        print(f"[Area API] Warning: Failed to delete from database: {e}")
    
    

@router.delete("/{area_id}")
async def delete_area(area_id: str):
    """Delete an area"""
    area = area_risk_engine.get_area(area_id)
    if not area:
        raise HTTPException(status_code=404, detail=f"Area '{area_id}' not found")
    
    area_risk_engine.remove_area(area_id)
    return {"status": "deleted", "area_id": area_id}
