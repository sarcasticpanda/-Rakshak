"""
Trend Analysis - Detect growth/decline patterns and forecast short-term
Uses simple linear regression (no ML needed)
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from scipy import stats
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.connection import get_database


class TrendAnalyzer:
    """Analyze trends and forecast using hourly aggregates"""
    
    @staticmethod
    async def analyze_trend(
        entity_id: str,
        entity_type: str,  # "camera" or "area"
        period_hours: int = 168  # Default 7 days
    ) -> Dict[str, Any]:
        """
        Analyze trend over period
        
        Returns:
            {
                "trend": "increasing|decreasing|stable",
                "growth_rate_pct_per_day": float,
                "current_avg": float,
                "predicted_next_hour": float,
                "confidence": float (0-1),
                "basis": "linear_regression_on_hourly_avg"
            }
        """
        db = get_database()
        if db is None:
            raise RuntimeError("Database not available")
        
        # Fetch hourly aggregates
        collection_name = f"{entity_type}_metrics_hourly"
        collection = db[collection_name]

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=period_hours)

        field_name = f"{entity_type}_id"
        # Support both 'hour' (from injector) and 'hour_start' (from aggregator)
        cursor = collection.find({
            field_name: entity_id,
            '$or': [
                {'hour_start': {'$gte': start_time, '$lte': end_time}},
                {'hour': {'$gte': start_time, '$lte': end_time}}
            ]
        })

        data = []
        async for doc in cursor:
            # Support both field names and both avg fields
            hour_time = doc.get('hour_start') or doc.get('hour')
            avg_people = doc.get('avg_people') or doc.get('avg_people_count')
            if hour_time is not None and avg_people is not None:
                data.append({
                    'hour': hour_time,
                    'avg_people': avg_people
                })
        
        if len(data) < 2:
            return {
                "error": "Insufficient data for trend analysis (need at least 2 hours)",
                entity_type + "_id": entity_id,
                "data_points": len(data),
                "solution": "Wait for more data or run POST /analytics/aggregate/now"
            }
        
        # Prepare data for regression
        hours = np.array([(d['hour'] - data[0]['hour']).total_seconds() / 3600 for d in data])
        people = np.array([d['avg_people'] for d in data])
        
        # Check if all values are identical (can't do regression)
        if len(np.unique(people)) == 1:
            # All values identical - return stable trend
            return {
                entity_type + "_id": entity_id,
                "period_hours": period_hours,
                "trend": "stable",
                "growth_rate_pct_per_day": 0.0,
                "current_avg": round(people[0], 1),
                "predicted_next_hour": round(people[0], 1),
                "confidence": 1.0,
                "basis": "constant_values",
                "data_points": len(data),
                "note": "All values identical (likely looping video or stable crowd)"
            }
        
        # Linear regression
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(hours, people)
        except Exception as e:
            # Fallback for any regression error
            return {
                entity_type + "_id": entity_id,
                "period_hours": period_hours,
                "trend": "stable",
                "growth_rate_pct_per_day": 0.0,
                "current_avg": round(np.mean(people), 1),
                "predicted_next_hour": round(np.mean(people), 1),
                "confidence": 0.5,
                "basis": "fallback_mean",
                "data_points": len(data),
                "error": str(e)
            }
        
        # Determine trend direction
        if abs(slope) < 1.0:  # Less than 1 person/hour change
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Growth rate per day
        growth_per_day = slope * 24
        current_avg = people[-1]
        growth_rate_pct = (growth_per_day / current_avg * 100) if current_avg > 0 else 0
        
        # Forecast next hour
        next_hour_offset = hours[-1] + 1
        predicted = slope * next_hour_offset + intercept
        predicted = max(0, predicted)  # Can't have negative people
        
        # Confidence based on R² score
        r_squared = r_value ** 2
        confidence = min(r_squared, 0.95)  # Cap at 0.95 (never certainty!)
        
        return {
            entity_type + "_id": entity_id,
            "period_hours": period_hours,
            "trend": trend,
            "growth_rate_pct_per_day": round(growth_rate_pct, 2),
            "current_avg": round(current_avg, 1),
            "predicted_next_hour": round(predicted, 1),
            "confidence": round(confidence, 2),
            "basis": "linear_regression_on_hourly_avg",
            "data_points": len(data),
            "r_squared": round(r_squared, 3)
        }
    
    @staticmethod
    async def forecast_short_term(
        entity_id: str,
        entity_type: str,
        horizon_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Short-term forecast (30-60 minutes ahead)
        Based on last 3 hours of data
        
        Returns:
            {
                "forecast_time": datetime,
                "predicted_people": int,
                "confidence": float,
                "upper_bound": int,
                "lower_bound": int
            }
        """
        # Use last 3 hours for short-term forecast (or minimum 2)
        trend_data = await TrendAnalyzer.analyze_trend(
            entity_id, entity_type, period_hours=3
        )
        
        if "error" in trend_data:
            return {
                entity_type + "_id": entity_id,
                "error": "Insufficient data for forecasting",
                "solution": "Need at least 2 hours of aggregated data",
                **trend_data
            }
        
        # Extrapolate based on slope
        hours_ahead = horizon_minutes / 60.0
        current = trend_data["current_avg"]
        growth_per_hour = trend_data["growth_rate_pct_per_day"] / 24 / 100 * current
        
        predicted = current + (growth_per_hour * hours_ahead)
        predicted = max(0, predicted)
        
        # Confidence decreases with distance into future
        base_confidence = trend_data["confidence"]
        time_decay = max(0.5, 1.0 - (horizon_minutes / 120))  # 50% confidence at 2 hours
        confidence = base_confidence * time_decay
        
        # Bounds (±20%)
        margin = predicted * 0.2
        upper = predicted + margin
        lower = max(0, predicted - margin)
        
        forecast_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        
        return {
            entity_type + "_id": entity_id,
            "forecast_time": forecast_time.isoformat(),
            "horizon_minutes": horizon_minutes,
            "predicted_people": round(predicted),
            "confidence": round(confidence, 2),
            "upper_bound": round(upper),
            "lower_bound": round(lower),
            "basis": f"last_3_hours_linear_trend"
        }
