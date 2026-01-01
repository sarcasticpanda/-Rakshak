"""
Area Risk Engine
Aggregates metrics from multiple cameras in an area
Tracks visits and calculates area-level risk
"""
import time
from typing import Dict, List, Optional
from datetime import datetime, date
from app.models.area_config import AreaConfig, AreaMetrics
from app.core.shared_store import shared_store


class VisitTracker:
    """Tracks unique visitors and entry/exit counts"""
    
    def __init__(self):
        self.daily_visitors = {}  # {area_id: {date: set(track_ids)}}
        self.entries = {}  # {area_id: count}
        self.exits = {}  # {area_id: count}
        self.current_occupancy = {}  # {area_id: count}
    
    def update(self, area_id: str, people_count: int):
        """Update visitor counts"""
        today = date.today().isoformat()
        
        if area_id not in self.daily_visitors:
            self.daily_visitors[area_id] = {}
            self.entries[area_id] = 0
            self.exits[area_id] = 0
        
        if today not in self.daily_visitors[area_id]:
            self.daily_visitors[area_id][today] = set()
            self.entries[area_id] = 0
            self.exits[area_id] = 0
        
        # Update current occupancy
        prev_count = self.current_occupancy.get(area_id, 0)
        self.current_occupancy[area_id] = people_count
        
        # Track entries/exits
        if people_count > prev_count:
            self.entries[area_id] += (people_count - prev_count)
        elif people_count < prev_count:
            self.exits[area_id] += (prev_count - people_count)
    
    def get_stats(self, area_id: str) -> Dict:
        """Get visit statistics"""
        today = date.today().isoformat()
        
        return {
            'current_occupancy': self.current_occupancy.get(area_id, 0),
            'total_visits_today': len(self.daily_visitors.get(area_id, {}).get(today, set())),
            'total_entries': self.entries.get(area_id, 0),
            'total_exits': self.exits.get(area_id, 0)
        }


class AreaRiskEngine:
    """
    Calculates area-level risk by aggregating camera metrics
    """
    
    def __init__(self):
        self.areas: Dict[str, AreaConfig] = {}
        self.visit_tracker = VisitTracker()
    
    def add_area(self, config: AreaConfig):
        """Register a new area"""
        self.areas[config.area_id] = config
        print(f"[AreaRiskEngine] Registered area: {config.name} ({config.area_id})")
    
    def remove_area(self, area_id: str):
        """Remove an area"""
        if area_id in self.areas:
            del self.areas[area_id]
    
    def get_area(self, area_id: str) -> Optional[AreaConfig]:
        """Get area configuration"""
        return self.areas.get(area_id)
    
    def list_areas(self) -> List[AreaConfig]:
        """List all areas"""
        return list(self.areas.values())
    
    def calculate_area_metrics(self, area_id: str) -> Optional[AreaMetrics]:
        """
        Aggregate metrics from all cameras in an area
        """
        area = self.areas.get(area_id)
        if not area or not area.enabled:
            return None
        
        # Get metrics from all cameras in this area
        camera_metrics = {}
        total_people = 0
        densities = []
        risk_scores = []
        velocity_variances = []
        active_cameras = 0
        
        for cam_id in area.camera_ids:
            state = shared_store.get_state(cam_id)
            if state and state.metrics:
                m = state.metrics
                camera_metrics[cam_id] = {
                    'people_count': m.get('people_count', 0),
                    'density': m.get('density', 0.0),
                    'risk_score': m.get('risk_score', 0.0),
                    'risk_level': m.get('risk_level', 'NORMAL'),
                    'status': state.status
                }
                
                total_people += m.get('people_count', 0)
                densities.append(m.get('density', 0.0))
                risk_scores.append(m.get('risk_score', 0.0))
                velocity_variances.append(m.get('velocity_variance', 0.0))
                active_cameras += 1
        
        if not camera_metrics:
            return None
        
        # Calculate aggregates
        avg_density = sum(densities) / len(densities) if densities else 0.0
        max_density = max(densities) if densities else 0.0
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
        max_risk = max(risk_scores) if risk_scores else 0.0
        avg_velocity_var = sum(velocity_variances) / len(velocity_variances) if velocity_variances else 0.0
        
        # Update visit tracking
        self.visit_tracker.update(area_id, total_people)
        visit_stats = self.visit_tracker.get_stats(area_id)
        
        # Determine area risk level
        if max_risk >= area.critical_threshold:
            area_risk_level = "CRITICAL"
            status = "critical"
        elif max_risk >= area.warning_threshold:
            area_risk_level = "WARNING"
            status = "warning"
        else:
            area_risk_level = "NORMAL"
            status = "active"
        
        return AreaMetrics(
            area_id=area_id,
            timestamp=time.time(),
            total_people=total_people,
            avg_density=avg_density,
            max_density=max_density,
            avg_risk_score=avg_risk,
            max_risk_score=max_risk,
            area_risk_level=area_risk_level,
            current_occupancy=visit_stats['current_occupancy'],
            total_visits_today=visit_stats['total_visits_today'],
            total_entries=visit_stats['total_entries'],
            total_exits=visit_stats['total_exits'],
            camera_metrics=camera_metrics,
            status=status,
            active_cameras=active_cameras,
            total_cameras=len(area.camera_ids)
        )
    
    def get_all_area_metrics(self) -> Dict[str, AreaMetrics]:
        """Get metrics for all areas"""
        metrics = {}
        for area_id in self.areas.keys():
            area_metrics = self.calculate_area_metrics(area_id)
            if area_metrics:
                metrics[area_id] = area_metrics
        return metrics


# Global singleton
area_risk_engine = AreaRiskEngine()
