"""
Historical Data API - Query metrics history from MongoDB
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.connection import get_database
from app.db.repositories import MetricsRepository


router = APIRouter(prefix="/history", tags=["history"])


class MetricsHistoryResponse(BaseModel):
    """Response with metrics history"""
    camera_id: Optional[str] = None
    area_id: Optional[str] = None
    start_time: str
    end_time: str
    data_points: int
    metrics: List[Dict[str, Any]]


class StatisticsResponse(BaseModel):
    """Aggregated statistics response"""
    id: str
    type: str  # "camera" or "area"
    period_hours: int
    avg_people: float
    max_people: int
    avg_risk: float
    max_risk: float
    critical_events: int
    total_entries: Optional[int] = None
    total_exits: Optional[int] = None


@router.get("/cameras/{camera_id}", response_model=MetricsHistoryResponse)
async def get_camera_history(
    camera_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history (max 1 week)")
):
    """
    Get metrics history for a camera
    
    Args:
        camera_id: Camera identifier
        hours: Number of hours of history (default 24, max 168=1 week)
    """
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    repo = MetricsRepository(db)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    metrics = await repo.get_camera_history(
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No history found for camera '{camera_id}'")
    
    return MetricsHistoryResponse(
        camera_id=camera_id,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        data_points=len(metrics),
        metrics=metrics
    )


@router.get("/areas/{area_id}", response_model=MetricsHistoryResponse)
async def get_area_history(
    area_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history (max 1 week)")
):
    """
    Get metrics history for an area
    
    Args:
        area_id: Area identifier
        hours: Number of hours of history
    """
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    repo = MetricsRepository(db)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    metrics = await repo.get_area_history(
        area_id=area_id,
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No history found for area '{area_id}'")
    
    return MetricsHistoryResponse(
        area_id=area_id,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        data_points=len(metrics),
        metrics=metrics
    )


@router.get("/cameras/{camera_id}/stats", response_model=StatisticsResponse)
async def get_camera_statistics(
    camera_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Statistical period in hours")
):
    """Get aggregated statistics for a camera"""
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    repo = MetricsRepository(db)
    
    stats = await repo.get_statistics(camera_id=camera_id, hours=hours)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"No statistics available for camera '{camera_id}'")
    
    return StatisticsResponse(
        id=camera_id,
        type="camera",
        period_hours=hours,
        avg_people=stats.get("avg_people", 0),
        max_people=int(stats.get("max_people", 0)),
        avg_risk=stats.get("avg_risk", 0),
        max_risk=stats.get("max_risk", 0),
        critical_events=stats.get("critical_events", 0)
    )


@router.get("/areas/{area_id}/stats", response_model=StatisticsResponse)
async def get_area_statistics(
    area_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Statistical period in hours")
):
    """Get aggregated statistics for an area"""
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    repo = MetricsRepository(db)
    
    stats = await repo.get_statistics(area_id=area_id, hours=hours)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"No statistics available for area '{area_id}'")
    
    return StatisticsResponse(
        id=area_id,
        type="area",
        period_hours=hours,
        avg_people=stats.get("avg_people", 0),
        max_people=int(stats.get("max_people", 0)),
        avg_risk=stats.get("avg_risk", 0),
        max_risk=stats.get("max_risk", 0),
        critical_events=stats.get("critical_events", 0),
        total_entries=stats.get("total_entries"),
        total_exits=stats.get("total_exits")
    )
