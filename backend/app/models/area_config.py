"""
Area Configuration Models
Groups cameras by physical location and applies context
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class AreaConfig(BaseModel):
    """Configuration for a physical area"""
    area_id: str
    name: str
    description: str = "Monitored area"
    camera_ids: List[str] = []
    
    # Context
    context_type: str = "general"  # temple, mall, station, event, street
    
    # Thresholds
    warning_threshold: float = 40.0
    critical_threshold: float = 70.0
    
    # Capacity
    max_capacity: Optional[int] = None
    
    # State
    enabled: bool = True


class AreaMetrics(BaseModel):
    """Aggregated metrics for an area"""
    area_id: str
    timestamp: float
    
    # Aggregated from cameras
    total_people: int = 0
    avg_density: float = 0.0
    max_density: float = 0.0
    avg_risk_score: float = 0.0
    max_risk_score: float = 0.0
    area_risk_level: str = "NORMAL"
    
    # Visit tracking
    current_occupancy: int = 0
    total_visits_today: int = 0
    total_entries: int = 0
    total_exits: int = 0
    
    # Per-camera breakdown
    camera_metrics: Dict[str, Dict] = {}
    
    # Status
    status: str = "active"
    active_cameras: int = 0
    total_cameras: int = 0


class AreaCreateRequest(BaseModel):
    """Request to create a new area"""
    area_id: str
    name: str
    description: str = "Monitored area"
    camera_ids: List[str] = []
    context_type: str = "general"
    warning_threshold: float = 40.0
    critical_threshold: float = 70.0
    max_capacity: Optional[int] = None
