"""
Pattern Detection - Find recurring patterns (peak hours, busy days)
Uses hourly aggregates for performance
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict
import numpy as np

from app.db.connection import get_database


class PatternDetector:
    """Detect recurring temporal patterns"""
    
    @staticmethod
    async def analyze_patterns(
        entity_id: str,
        entity_type: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Find hourly and daily patterns
        
        Returns patterns including peak hours and thresholds
        """
        db = get_database()
        if db is None:
            raise RuntimeError("Database not available")
        
        collection_name = f"{entity_type}_metrics_hourly"
        collection = db[collection_name]
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        field_name = f"{entity_type}_id"
        cursor = collection.find({
            field_name: entity_id,
            'hour_start': {'$gte': start_time, '$lte': end_time}
        })
        
        # Collect data
        by_hour = defaultdict(list)  # hour-of-day -> [people counts]
        by_day = defaultdict(list)   # day-of-week -> [people counts]
        all_values = []
        
        async for doc in cursor:
            hour_start = doc['hour_start']
            avg_people = doc['avg_people']
            
            hour_of_day = hour_start.hour
            day_of_week = hour_start.strftime('%A')
            
            by_hour[hour_of_day].append(avg_people)
            by_day[day_of_week].append(avg_people)
            all_values.append(avg_people)
        
        if len(all_values) < 24:
            return {"error": "Insufficient data (need at least 24 hours)"}
        
        # Calculate averages
        avg_by_hour = {h: round(np.mean(vals), 1) for h, vals in by_hour.items()}
        avg_by_day = {d: round(np.mean(vals), 1) for d, vals in by_day.items()}
        
        # Find peak hours (top 25% busiest)
        sorted_hours = sorted(avg_by_hour.items(), key=lambda x: x[1], reverse=True)
        num_peaks = max(3, len(sorted_hours) // 4)
        peak_hours = sorted([h for h, _ in sorted_hours[:num_peaks]])
        
        # Find busiest day
        busiest_day = max(avg_by_day.items(), key=lambda x: x[1])[0] if avg_by_day else None
        
        # Calculate percentile thresholds
        p50 = np.percentile(all_values, 50)
        p75 = np.percentile(all_values, 75)
        p95 = np.percentile(all_values, 95)
        
        return {
            entity_type + "_id": entity_id,
            "analysis_period_days": days,
            "peak_hours": peak_hours,
            "busiest_day": busiest_day,
            "avg_by_hour": avg_by_hour,
            "avg_by_day": avg_by_day,
            "classification": {
                "normal_threshold": round(p50),
                "busy_threshold": round(p75),
                "critical_threshold": round(p95)
            },
            "data_points": len(all_values)
        }
