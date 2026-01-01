"""
Data Access Layer - Repository pattern for MongoDB operations
Handles CRUD for cameras, areas, and metrics history
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import time

from app.models.area_config import AreaConfig, AreaMetrics
from app.core.camera_pipeline import CameraConfig


class CameraRepository:
    """Repository for camera CRUD operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.cameras
    
    async def create(self, config: CameraConfig) -> bool:
        """Create a new camera"""
        doc = {
            "camera_id": config.camera_id,
            "name": config.name,
            "source": config.source,
            "location": config.location,
            "context": config.context,
            "enabled": config.enabled,
            "target_fps": config.target_fps,
            "resolution": list(config.resolution) if config.resolution else None,
            "warning_threshold": config.warning_threshold,
            "critical_threshold": config.critical_threshold,
            # Phase 3 placeholders
            "floor_level": 0,
            "adjacent_cameras": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            result = await self.collection.insert_one(doc)
            return result.inserted_id is not None
        except Exception as e:
            print(f"[CameraRepository] Create failed: {e}")
            return False
    
    async def get(self, camera_id: str) -> Optional[Dict]:
        """Get camera by ID"""
        try:
            return await self.collection.find_one({"camera_id": camera_id})
        except Exception as e:
            print(f"[CameraRepository] Get failed: {e}")
            return None
    
    async def list(self, enabled_only: bool = False) -> List[Dict]:
        """List all cameras"""
        try:
            query = {"enabled": True} if enabled_only else {}
            cursor = self.collection.find(query)
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"[CameraRepository] List failed: {e}")
            return []
    
    async def update(self, camera_id: str, updates: Dict) -> bool:
        """Update camera configuration"""
        try:
            updates["updated_at"] = datetime.utcnow()
            result = await self.collection.update_one(
                {"camera_id": camera_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[CameraRepository] Update failed: {e}")
            return False
    
    async def delete(self, camera_id: str) -> bool:
        """Delete camera"""
        try:
            result = await self.collection.delete_one({"camera_id": camera_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[CameraRepository] Delete failed: {e}")
            return False


class AreaRepository:
    """Repository for area CRUD operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.areas
    
    async def create(self, config: AreaConfig) -> bool:
        """Create a new area"""
        doc = config.model_dump()
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        # Phase 3 placeholders
        doc["geometry"] = None  # Future: GeoJSON polygon
        doc["floor_level"] = 0
        doc["adjacent_areas"] = []
        
        try:
            result = await self.collection.insert_one(doc)
            return result.inserted_id is not None
        except Exception as e:
            print(f"[AreaRepository] Create failed: {e}")
            return False
    
    async def get(self, area_id: str) -> Optional[Dict]:
        """Get area by ID"""
        try:
            return await self.collection.find_one({"area_id": area_id})
        except Exception as e:
            print(f"[AreaRepository] Get failed: {e}")
            return None
    
    async def list(self, enabled_only: bool = False) -> List[Dict]:
        """List all areas"""
        try:
            query = {"enabled": True} if enabled_only else {}
            cursor = self.collection.find(query)
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"[AreaRepository] List failed: {e}")
            return []
    
    async def update(self, area_id: str, updates: Dict) -> bool:
        """Update area configuration"""
        try:
            updates["updated_at"] = datetime.utcnow()
            result = await self.collection.update_one(
                {"area_id": area_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[AreaRepository] Update failed: {e}")
            return False
    
    async def delete(self, area_id: str) -> bool:
        """Delete area"""
        try:
            result = await self.collection.delete_one({"area_id": area_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[AreaRepository] Delete failed: {e}")
            return False


class MetricsRepository:
    """Repository for metrics history"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.camera_metrics = db.camera_metrics
        self.area_metrics = db.area_metrics
    
    async def bulk_insert_camera_metrics(self, metrics_list: List[Dict]):
        """Bulk insert camera metrics (called at 1Hz by writer)"""
        if not metrics_list:
            return
        
        try:
            # Add timestamp for MongoDB
            for m in metrics_list:
                if 'logged_at' not in m:
                    m['logged_at'] = datetime.utcnow()
            
            await self.camera_metrics.insert_many(metrics_list, ordered=False)
        except Exception as e:
            print(f"[MetricsRepository] Camera bulk insert failed: {e}")
    
    async def bulk_insert_area_metrics(self, metrics_list: List[Dict]):
        """Bulk insert area metrics (called at 1Hz by writer)"""
        if not metrics_list:
            return
        
        try:
            # Add timestamp for MongoDB
            for m in metrics_list:
                if 'logged_at' not in m:
                    m['logged_at'] = datetime.utcnow()
            
            await self.area_metrics.insert_many(metrics_list, ordered=False)
        except Exception as e:
            print(f"[MetricsRepository] Area bulk insert failed: {e}")
    
    async def get_camera_history(
        self, 
        camera_id: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Get camera metrics history"""
        try:
            query = {"camera_id": camera_id}
            
            if start_time or end_time:
                query["timestamp"] = {}
                if start_time:
                    query["timestamp"]["$gte"] = start_time.timestamp()
                if end_time:
                    query["timestamp"]["$lte"] = end_time.timestamp()
            
            cursor = self.camera_metrics.find(query).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"[MetricsRepository] Get camera history failed: {e}")
            return []
    
    async def get_area_history(
        self, 
        area_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Get area metrics history"""
        try:
            query = {"area_id": area_id}
            
            if start_time or end_time:
                query["timestamp"] = {}
                if start_time:
                    query["timestamp"]["$gte"] = start_time.timestamp()
                if end_time:
                    query["timestamp"]["$lte"] = end_time.timestamp()
            
            cursor = self.area_metrics.find(query).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"[MetricsRepository] Get area history failed: {e}")
            return []
    
    async def get_statistics(
        self,
        camera_id: Optional[str] = None,
        area_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get aggregated statistics"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            if camera_id:
                # Camera statistics
                pipeline = [
                    {"$match": {
                        "camera_id": camera_id,
                        "timestamp": {"$gte": start_time.timestamp()}
                    }},
                    {"$group": {
                        "_id": None,
                        "avg_people": {"$avg": "$people_count"},
                        "max_people": {"$max": "$people_count"},
                        "avg_risk": {"$avg": "$risk_score"},
                        "max_risk": {"$max": "$risk_score"},
                        "critical_events": {
                            "$sum": {"$cond": [{"$eq": ["$risk_level", "CRITICAL"]}, 1, 0]}
                        }
                    }}
                ]
                cursor = self.camera_metrics.aggregate(pipeline)
            elif area_id:
                # Area statistics
                pipeline = [
                    {"$match": {
                        "area_id": area_id,
                        "timestamp": {"$gte": start_time.timestamp()}
                    }},
                    {"$group": {
                        "_id": None,
                        "avg_people": {"$avg": "$total_people"},
                        "max_people": {"$max": "$total_people"},
                        "avg_risk": {"$avg": "$avg_risk_score"},
                        "max_risk": {"$max": "$max_risk_score"},
                        "total_entries": {"$max": "$total_entries"},
                        "total_exits": {"$max": "$total_exits"},
                        "critical_events": {
                            "$sum": {"$cond": [{"$eq": ["$area_risk_level", "CRITICAL"]}, 1, 0]}
                        }
                    }}
                ]
                cursor = self.area_metrics.aggregate(pipeline)
            else:
                return {}
            
            results = await cursor.to_list(length=1)
            return results[0] if results else {}
        except Exception as e:
            print(f"[MetricsRepository] Get statistics failed: {e}")
            return {}
