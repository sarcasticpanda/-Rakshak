"""
Hourly Aggregation - Pre-compute summaries to avoid expensive queries
Background job that runs every hour
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.connection import get_database


class HourlyAggregator:
    """
    Aggregates raw 1Hz metrics into hourly summaries
    Reduces query load by 3600x
    """
    
    def __init__(self, interval_seconds: int = 3600):
        """
        Args:
            interval_seconds: How often to run aggregation (default 1 hour)
        """
        self.interval_seconds = interval_seconds
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the aggregation task"""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._aggregation_loop())
            print("[HourlyAggregator] Started")
    
    async def stop(self):
        """Stop the aggregation task"""
        self.running = False
        if self.task:
            await self.task
        print("[HourlyAggregator] Stopped")
    
    async def _aggregation_loop(self):
        """Main loop - aggregates data every hour"""
        # Wait for initial data to accumulate (10 minutes)
        await asyncio.sleep(600)
        
        while self.running:
            try:
                print("[HourlyAggregator] Running aggregation...")
                
                db = get_database()
                if db is None:
                    print("[HourlyAggregator] Database not available, skipping")
                    await asyncio.sleep(60)
                    continue
                
                # Aggregate previous hour
                hour_end = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                hour_start = hour_end - timedelta(hours=1)
                
                # Aggregate camera metrics
                camera_summary = await self._aggregate_camera_metrics(
                    db, hour_start, hour_end
                )
                print(f"[HourlyAggregator] Aggregated {len(camera_summary)} camera hours")
                
                # Aggregate area metrics
                area_summary = await self._aggregate_area_metrics(
                    db, hour_start, hour_end
                )
                print(f"[HourlyAggregator] Aggregated {len(area_summary)} area hours")
                
                # Sleep until next hour
                await asyncio.sleep(self.interval_seconds)
                
            except Exception as e:
                print(f"[HourlyAggregator] Error: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    async def _aggregate_camera_metrics(
        self, 
        db: AsyncIOMotorDatabase,
        hour_start: datetime,
        hour_end: datetime
    ) -> list:
        """
        Aggregate camera metrics for one hour
        
        Returns:
            List of aggregated documents
        """
        pipeline = [
            {
                '$match': {
                    'timestamp': {
                        '$gte': hour_start.timestamp(),
                        '$lt': hour_end.timestamp()
                    }
                }
            },
            {
                '$group': {
                    '_id': '$camera_id',
                    'avg_people': {'$avg': '$people_count'},
                    'max_people': {'$max': '$people_count'},
                    'min_people': {'$min': '$people_count'},
                    'avg_risk': {'$avg': '$risk_score'},
                    'max_risk': {'$max': '$risk_score'},
                    'avg_density': {'$avg': '$density'},
                    'critical_seconds': {
                        '$sum': {
                            '$cond': [
                                {'$eq': ['$risk_level', 'CRITICAL']},
                                1,
                                0
                            ]
                        }
                    },
                    'data_points': {'$sum': 1}
                }
            }
        ]
        
        results = []
        async for doc in db.camera_metrics.aggregate(pipeline):
            summary = {
                'camera_id': doc['_id'],
                'hour_start': hour_start,
                'hour_end': hour_end,
                'avg_people': round(doc['avg_people'], 1),
                'max_people': int(doc['max_people']),
                'min_people': int(doc['min_people']),
                'avg_risk': round(doc['avg_risk'], 1),
                'max_risk': round(doc['max_risk'], 1),
                'avg_density': round(doc['avg_density'], 2),
                'critical_seconds': doc['critical_seconds'],
                'data_points': doc['data_points'],
                'created_at': datetime.utcnow()
            }
            results.append(summary)
        
        # Insert into hourly collection
        if results:
            await db.camera_metrics_hourly.insert_many(results)
        
        return results
    
    async def _aggregate_area_metrics(
        self,
        db: AsyncIOMotorDatabase,
        hour_start: datetime,
        hour_end: datetime
    ) -> list:
        """
        Aggregate area metrics for one hour
        
        Returns:
            List of aggregated documents
        """
        pipeline = [
            {
                '$match': {
                    'timestamp': {
                        '$gte': hour_start.timestamp(),
                        '$lt': hour_end.timestamp()
                    }
                }
            },
            {
                '$group': {
                    '_id': '$area_id',
                    'avg_people': {'$avg': '$total_people'},
                    'max_people': {'$max': '$total_people'},
                    'min_people': {'$min': '$total_people'},
                    'avg_risk': {'$avg': '$avg_risk_score'},
                    'max_risk': {'$max': '$max_risk_score'},
                    'avg_density': {'$avg': '$avg_density'},
                    'max_density': {'$max': '$max_density'},
                    'total_entries': {'$sum': '$total_entries'},
                    'total_exits': {'$sum': '$total_exits'},
                    'critical_seconds': {
                        '$sum': {
                            '$cond': [
                                {'$eq': ['$area_risk_level', 'CRITICAL']},
                                1,
                                0
                            ]
                        }
                    },
                    'data_points': {'$sum': 1}
                }
            }
        ]
        
        results = []
        async for doc in db.area_metrics.aggregate(pipeline):
            summary = {
                'area_id': doc['_id'],
                'hour_start': hour_start,
                'hour_end': hour_end,
                'avg_people': round(doc['avg_people'], 1),
                'max_people': int(doc['max_people']),
                'min_people': int(doc['min_people']),
                'avg_risk': round(doc['avg_risk'], 1),
                'max_risk': round(doc['max_risk'], 1),
                'avg_density': round(doc['avg_density'], 2),
                'max_density': round(doc['max_density'], 2),
                'total_entries': doc['total_entries'],
                'total_exits': doc['total_exits'],
                'critical_seconds': doc['critical_seconds'],
                'data_points': doc['data_points'],
                'created_at': datetime.utcnow()
            }
            results.append(summary)
        
        # Insert into hourly collection
        if results:
            await db.area_metrics_hourly.insert_many(results)
        
        return results
    
    async def aggregate_now(self, hours_back: int = 2):
        """
        Manually trigger aggregation (for testing/backfill)
        
        Args:
            hours_back: Number of hours to aggregate (default 1)
        """
        db = get_database()
        if db is None:
            raise RuntimeError("Database not available")
        
        all_results = []
        
        for i in range(hours_back):
            hour_end = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
            hour_start = hour_end - timedelta(hours=1)
            
            camera_summary = await self._aggregate_camera_metrics(db, hour_start, hour_end)
            area_summary = await self._aggregate_area_metrics(db, hour_start, hour_end)
            
            all_results.extend(camera_summary + area_summary)
        
        return all_results


# Global singleton
hourly_aggregator = HourlyAggregator(interval_seconds=3600)
