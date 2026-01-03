"""
Anomaly Detection - Identify unusual patterns (spikes, abnormal values)
Real-time detection using z-scores and baseline comparison
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np

from app.db.connection import get_database


class AnomalyDetector:
    """Detect statistical anomalies in crowd metrics"""
    
    @staticmethod
    async def detect_anomalies(
        entity_id: str,
        entity_type: str,
        window_hours: int = 24,
        z_threshold: float = 2.5
    ) -> Dict[str, Any]:
        """
        Detect anomalies using z-score analysis
        
        Returns anomalies exceeding z_threshold standard deviations
        """
        db = get_database()
        if db is None:
            raise RuntimeError("Database not available")
        
        collection_name = f"{entity_type}_metrics_hourly"
        collection = db[collection_name]

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=window_hours)

        field_name = f"{entity_type}_id"
        # Support both 'hour_start' and 'hour' fields
        cursor = collection.find({
            field_name: entity_id,
            '$or': [
                {'hour_start': {'$gte': start_time, '$lte': end_time}},
                {'hour': {'$gte': start_time, '$lte': end_time}}
            ]
        })

        data = []
        async for doc in cursor:
            hour_time = doc.get('hour_start') or doc.get('hour')
            avg_people = doc.get('avg_people') or doc.get('avg_people_count')
            if hour_time is not None and avg_people is not None:
                data.append({
                    'timestamp': hour_time,
                    'people': avg_people
                })
        
        if len(data) < 3:
            return {"error": "Insufficient data (need at least 3 hours)"}
        
        # Calculate z-scores
        values = np.array([d['people'] for d in data])
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return {
                entity_type + "_id": entity_id,
                "anomalies": [],
                "summary": {"total": 0, "high": 0, "extreme": 0}
            }
        
        anomalies = []
        for d in data:
            z_score = (d['people'] - mean) / std
            if abs(z_score) > z_threshold:
                severity = "extreme" if abs(z_score) > 3.5 else "high"
                anomalies.append({
                    "timestamp": d['timestamp'].isoformat(),
                    "value": round(d['people'], 1),
                    "expected": round(mean, 1),
                    "z_score": round(z_score, 2),
                    "severity": severity
                })
        
        # Summary
        high_count = sum(1 for a in anomalies if a['severity'] == 'high')
        extreme_count = sum(1 for a in anomalies if a['severity'] == 'extreme')
        
        return {
            entity_type + "_id": entity_id,
            "window_hours": window_hours,
            "z_threshold": z_threshold,
            "anomalies": anomalies,
            "summary": {
                "total": len(anomalies),
                "high": high_count,
                "extreme": extreme_count
            },
            "baseline": {
                "mean": round(mean, 1),
                "std": round(std, 1)
            }
        }
    
    @staticmethod
    async def find_sudden_spikes(
        entity_id: str,
        entity_type: str,
        lookback_minutes: int = 30,
        spike_threshold_pct: float = 50.0
    ) -> Dict[str, Any]:
        """
        Find sudden spikes (>50% increase in short time)
        Uses raw metrics for recent data
        """
        db = get_database()
        if db is None:
            raise RuntimeError("Database not available")
        
        collection_name = f"{entity_type}_metrics"
        collection = db[collection_name]
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)
        
        field_name = f"{entity_type}_id"
        cursor = collection.find({
            field_name: entity_id,
            'timestamp': {'$gte': start_time, '$lte': end_time}
        }).sort('timestamp', 1)
        
        data = []
        async for doc in cursor:
            data.append({
                'timestamp': doc['timestamp'],
                'people': doc['people_count']
            })
        
        if len(data) < 10:
            return {"spikes": [], "summary": {"total": 0}}
        
        spikes = []
        for i in range(5, len(data)):
            baseline = np.mean([d['people'] for d in data[i-5:i]])
            current = data[i]['people']
            
            if baseline > 0:
                increase_pct = ((current - baseline) / baseline) * 100
                if increase_pct > spike_threshold_pct:
                    spikes.append({
                        "timestamp": data[i]['timestamp'].isoformat(),
                        "value": current,
                        "baseline": round(baseline, 1),
                        "increase_pct": round(increase_pct, 1)
                    })
        
        return {
            entity_type + "_id": entity_id,
            "lookback_minutes": lookback_minutes,
            "spike_threshold_pct": spike_threshold_pct,
            "spikes": spikes,
            "summary": {"total": len(spikes)}
        }
