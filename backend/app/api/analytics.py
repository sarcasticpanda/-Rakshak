"""
Analytics API Router - Endpoints for trends, patterns, anomalies
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Literal

from app.analytics.aggregator import hourly_aggregator
from app.analytics.time_series import TrendAnalyzer
from app.analytics.patterns import PatternDetector
from app.analytics.anomalies import AnomalyDetector


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/")
async def analytics_info():
    """Analytics API Information and Available Endpoints"""
    return {
        "service": "Stampede Analytics Engine",
        "version": "1.0.0",
        "status": "operational",
        "description": "Time-series analytics for crowd monitoring",
        "available_endpoints": {
            "aggregate": "POST /analytics/aggregate/now - Trigger manual hourly aggregation",
            "trends": "GET /analytics/{camera|area}/{id}/trends - Analyze growth trends",
            "forecast": "GET /analytics/{camera|area}/{id}/forecast - Short-term predictions",
            "patterns": "GET /analytics/{camera|area}/{id}/patterns - Find peak hours & busy days",
            "anomalies": "GET /analytics/{camera|area}/{id}/anomalies - Detect statistical anomalies",
            "spikes": "GET /analytics/{camera|area}/{id}/spikes - Find sudden crowd spikes"
        },
        "getting_started": {
            "step_1": "Run POST /analytics/aggregate/now to create hourly summaries",
            "step_2": "Use trends/patterns endpoints with your camera_id or area_id",
            "step_3": "Check real-time spikes and anomalies for alerts"
        },
        "example_ids": {
            "cameras": ["cam_stampede", "cam_test2", "cam_test3"],
            "areas": ["test_area_main"]
        }
    }


@router.post("/aggregate/now")
async def trigger_aggregation(hours_back: int = Query(1, ge=1, le=168)):
    """Manually trigger hourly aggregation (for testing/backfill)"""
    try:
        await hourly_aggregator.aggregate_now(hours_back=hours_back)
        return {"status": "success", "hours_aggregated": hours_back}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/trends")
async def get_trends(
    entity_type: Literal["camera", "area"],
    entity_id: str,
    period_hours: int = Query(24, ge=1, le=720)
):
    """Get trend analysis (growth rate, forecast)"""
    try:
        trend = await TrendAnalyzer.analyze_trend(entity_id, entity_type, period_hours)
        return trend
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/forecast")
async def get_forecast(
    entity_type: Literal["camera", "area"],
    entity_id: str,
    horizon_minutes: int = Query(30, ge=15, le=120)
):
    """Get short-term forecast (next 15-120 minutes)"""
    try:
        forecast = await TrendAnalyzer.forecast_short_term(entity_id, entity_type, horizon_minutes)
        return forecast
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/patterns")
async def get_patterns(
    entity_type: Literal["camera", "area"],
    entity_id: str,
    days: int = Query(7, ge=1, le=30)
):
    """Get recurring patterns (peak hours, busy days)"""
    try:
        patterns = await PatternDetector.analyze_patterns(entity_id, entity_type, days)
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/anomalies")
async def get_anomalies(
    entity_type: Literal["camera", "area"],
    entity_id: str,
    window_hours: int = Query(24, ge=3, le=168),
    z_threshold: float = Query(2.5, ge=1.5, le=5.0)
):
    """Detect statistical anomalies using z-scores"""
    try:
        anomalies = await AnomalyDetector.detect_anomalies(
            entity_id, entity_type, window_hours, z_threshold
        )
        return anomalies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/spikes")
async def get_spikes(
    entity_type: Literal["camera", "area"],
    entity_id: str,
    lookback_minutes: int = Query(30, ge=10, le=120),
    spike_threshold_pct: float = Query(50.0, ge=20.0, le=200.0)
):
    """Find sudden spikes in crowd levels"""
    try:
        spikes = await AnomalyDetector.find_sudden_spikes(
            entity_id, entity_type, lookback_minutes, spike_threshold_pct
        )
        return spikes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
