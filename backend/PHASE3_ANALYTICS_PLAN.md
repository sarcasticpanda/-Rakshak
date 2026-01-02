# Phase 3: Analytics & Insights - Implementation Plan

## 🎯 Core Objective
**Turn stored numbers into meaning** - Enable the system to answer:
- Is this crowd growing or shrinking?
- Is this normal for this time of day?
- Is this worse than yesterday?
- Will it get dangerous in the next 30 minutes?
- Is this spike abnormal or routine?

---

## 📊 System Analogy
- **Detection Pipeline** → Eyes (seeing)
- **MongoDB** → Memory (remembering)
- **Analytics (Phase 3)** → Brain (understanding & predicting)

---

## 🏗️ Architecture - Clean Data Flow

```
Live Cameras
   ↓
Detection + Tracking + Heatmap (UNCHANGED - 30 Hz)
   ↓
Risk Metrics (1 Hz to SharedStore)
   ↓
Metrics Aggregator (1 Hz collection)
   ↓
MongoDB (raw metrics @ 1 Hz)
   ↓
┌─────────────────────────────┐
│ NEW: Hourly Aggregation Job │ ← Runs every hour
│ (Background Task)            │
└─────────────────────────────┘
   ↓
MongoDB Collections:
  • camera_metrics (raw, 7-day TTL)
  • area_metrics (raw, 7-day TTL)
  • camera_hourly (NEW - aggregated, 90-day TTL)
  • area_hourly (NEW - aggregated, 90-day TTL)
   ↓
┌─────────────────────────────┐
│ NEW: Analytics Layer        │
│ (Read-only, no video touch) │
└─────────────────────────────┘
   ↓
/analytics/* REST APIs
   ↓
Frontend Charts & Insights
```

---

## 🔒 Hard Rules (DO NOT BREAK)

### ✅ What Analytics CAN Do
- Read from MongoDB (historical data only)
- Compute statistics, trends, patterns
- Return insights via REST APIs
- Cache results (5-15 min TTL)

### ❌ What Analytics CANNOT Do
- Touch live video pipelines
- Interfere with YOLO detection
- Modify SharedStore
- Block camera threads
- Access raw frames

**Reason:** Keep detection accuracy stable, avoid performance impact.

---

## 📦 Module Structure

```
backend/
  app/
    analytics/
      __init__.py
      time_series.py      # Trends, forecasting
      patterns.py         # Peak hours, recurring patterns
      anomalies.py        # Outlier detection
      comparisons.py      # Period-over-period analysis
      aggregator.py       # Hourly rollup background job
      cache.py            # In-memory TTL cache
    api/
      analytics.py        # NEW - Analytics REST endpoints
    db/
      repositories.py     # ADD - Analytics query methods
```

---

## 🧩 Component Breakdown

### 1. Hourly Aggregation Job (`analytics/aggregator.py`)

**Purpose:** Pre-compute hourly summaries to avoid expensive queries

**What it does:**
```python
# Every hour (e.g., at XX:00:00):
# 1. Query last hour's raw metrics
# 2. Compute:
#    - avg_people, max_people, min_people
#    - avg_risk, max_risk
#    - critical_minutes (count of minutes risk > 70)
#    - total_entries, total_exits
# 3. Insert into camera_hourly / area_hourly collections
# 4. Delete processed raw data older than 7 days
```

**Schema:**
```json
{
  "camera_id": "cam_stampede",
  "hour_start": ISODate("2026-01-02T10:00:00Z"),
  "hour_end": ISODate("2026-01-02T11:00:00Z"),
  "avg_people": 285.3,
  "max_people": 421,
  "min_people": 180,
  "avg_risk": 78.5,
  "max_risk": 100.0,
  "critical_minutes": 35,
  "total_entries": 520,
  "total_exits": 105,
  "data_points": 3600  // 1 Hz for 1 hour
}
```

**When it runs:**
- Background asyncio task
- Triggers at minute 5 of each hour (e.g., 10:05)
- Allows raw data to settle (5-min buffer)

---

### 2. Time Series Analysis (`analytics/time_series.py`)

**Answers:** "Is the crowd getting worse or better?"

**Functions:**

#### `calculate_trend(camera_id, hours=3)`
```python
# Uses hourly aggregates (not raw data)
# Returns:
{
  "direction": "increasing",  # up/down/stable
  "rate_per_hour": 12.5,      # % change
  "confidence": 0.78,          # 0-1 (based on R²)
  "basis": "linear_regression_3h"
}
```

#### `forecast_simple(area_id, horizon_minutes=30)`
```python
# Extrapolates next 30-60 min based on last 3 hours
# Returns:
{
  "current_people": 350,
  "forecast_people": 395,
  "confidence": 0.63,  # NEVER > 0.85 for simple model
  "lower_bound": 360,
  "upper_bound": 430,
  "method": "linear_extrapolation",
  "warning": "Confidence low - use with caution"
}
```

**Important:** Always include confidence, never claim certainty.

---

### 3. Pattern Detection (`analytics/patterns.py`)

**Answers:** "Is this normal for this time?"

**Functions:**

#### `find_peak_hours(area_id, days=7)`
```python
# Aggregates hourly data by hour-of-day
# Returns:
{
  "peak_hours": [10, 11, 17, 18],  # 10AM, 11AM, 5PM, 6PM
  "off_peak_hours": [2, 3, 4],
  "busiest_hour": 17,
  "avg_by_hour": {
    "0": 45, "1": 32, ..., "23": 78
  }
}
```

#### `detect_weekly_patterns(area_id, weeks=4)`
```python
# Returns day-of-week patterns
{
  "busiest_day": "Friday",
  "quietest_day": "Tuesday",
  "avg_by_day": {
    "Monday": 320,
    "Tuesday": 180,
    ...
  }
}
```

#### `classify_current_period(area_id, current_people)`
```python
# Compares current to historical percentiles
{
  "classification": "critical",  # normal/busy/critical
  "percentile": 95,              # 95th percentile
  "threshold_normal": 250,
  "threshold_busy": 400,
  "threshold_critical": 600
}
```

**Cache:** 15-minute TTL (patterns don't change quickly)

---

### 4. Anomaly Detection (`analytics/anomalies.py`)

**Answers:** "Is something strange happening?"

**Functions:**

#### `detect_anomalies(area_id, window_minutes=60, threshold=2.5)`
```python
# Uses raw data for recent window (last 60 min)
# Detects using z-score (>2.5σ = anomaly)
# Returns:
{
  "anomalies": [
    {
      "timestamp": "2026-01-02T14:35:23Z",
      "people_count": 800,
      "expected_range": [280, 380],
      "z_score": 3.2,
      "severity": "high"  # moderate/high/critical
    }
  ],
  "total_anomalies": 1,
  "detection_rate": 0.016  # 1/60 minutes
}
```

#### `find_sudden_spikes(area_id, minutes=5, threshold_percent=50)`
```python
# Detects >50% increase in 5 minutes
{
  "spikes": [
    {
      "start_time": "2026-01-02T14:30:00Z",
      "start_count": 200,
      "end_count": 350,
      "increase_percent": 75.0,
      "duration_minutes": 5
    }
  ]
}
```

#### `compare_to_baseline(area_id, baseline_days=7)`
```python
# Compares current to same-time-of-day average
{
  "current_people": 450,
  "baseline_avg": 280,
  "deviation_percent": 60.7,
  "is_anomalous": true,
  "baseline_period": "7_day_avg_at_same_hour"
}
```

**Cache:** None (needs real-time data)

---

### 5. Comparative Analysis (`analytics/comparisons.py`)

**Answers:** "Is this worse than before?"

**Functions:**

#### `compare_periods(area_id, period1, period2)`
```python
# Example: Today vs Yesterday
{
  "period1": {
    "label": "today",
    "avg_people": 320,
    "max_people": 450,
    "critical_hours": 2
  },
  "period2": {
    "label": "yesterday",
    "avg_people": 280,
    "max_people": 380,
    "critical_hours": 1
  },
  "change": {
    "avg_people_change": 14.3,      # % increase
    "max_people_change": 18.4,
    "worse": true
  }
}
```

#### `compare_cameras(area_id)`
```python
# Compare cameras within same area
{
  "cameras": [
    {"camera_id": "cam_stampede", "avg_people": 315, "rank": 1},
    {"camera_id": "cam_test3", "avg_people": 61, "rank": 2},
    {"camera_id": "cam_test2", "avg_people": 25, "rank": 3}
  ],
  "highest_risk_camera": "cam_stampede",
  "recommendation": "Focus monitoring on cam_stampede"
}
```

**Cache:** 5-minute TTL

---

### 6. Cache Layer (`analytics/cache.py`)

**Simple in-memory TTL cache:**
```python
class AnalyticsCache:
    """
    In-memory cache with TTL
    
    Usage:
        cache.set("trends_cam1_3h", result, ttl=900)  # 15 min
        cached = cache.get("trends_cam1_3h")
    """
    def __init__(self):
        self._cache = {}  # key: (value, expiry_time)
    
    def get(self, key):
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None
    
    def set(self, key, value, ttl=300):
        self._cache[key] = (value, time.time() + ttl)
```

**TTL Guidelines:**
- Trends: 15 minutes
- Patterns: 15 minutes
- Anomalies: No cache (real-time)
- Comparisons: 5 minutes

---

## 🔌 REST API Endpoints

### `GET /analytics/cameras/{camera_id}/trends`
**Query params:** `?hours=3` (default: 3, max: 168)

**Returns:**
```json
{
  "camera_id": "cam_stampede",
  "period_hours": 3,
  "trend": {
    "direction": "increasing",
    "rate_per_hour": 12.5,
    "confidence": 0.78
  },
  "forecast_30min": {
    "people": 395,
    "confidence": 0.63,
    "lower": 360,
    "upper": 430
  },
  "cached": false,
  "generated_at": "2026-01-02T15:23:45Z"
}
```

---

### `GET /analytics/areas/{area_id}/patterns`
**Query params:** `?days=7` (default: 7, max: 30)

**Returns:**
```json
{
  "area_id": "test_area_main",
  "analysis_period_days": 7,
  "peak_hours": [10, 11, 17, 18],
  "busiest_day": "Friday",
  "avg_by_hour": {...},
  "avg_by_day": {...},
  "current_classification": "critical",
  "cached": true
}
```

---

### `GET /analytics/areas/{area_id}/anomalies`
**Query params:** `?window_minutes=60&threshold=2.5`

**Returns:**
```json
{
  "area_id": "test_area_main",
  "window_minutes": 60,
  "anomalies": [
    {
      "timestamp": "2026-01-02T14:35:23Z",
      "people_count": 800,
      "expected_range": [280, 380],
      "z_score": 3.2,
      "severity": "high"
    }
  ],
  "total_anomalies": 1
}
```

---

### `GET /analytics/areas/{area_id}/forecast`
**Query params:** `?horizon_minutes=30`

**Returns:**
```json
{
  "area_id": "test_area_main",
  "current_people": 350,
  "forecast_people": 395,
  "horizon_minutes": 30,
  "confidence": 0.63,
  "lower_bound": 360,
  "upper_bound": 430,
  "method": "linear_extrapolation",
  "warning": "Confidence moderate - verify with operators"
}
```

---

### `GET /analytics/compare`
**Query params:** `?area_id=X&period1=today&period2=yesterday`

**Returns:**
```json
{
  "area_id": "test_area_main",
  "period1": {...},
  "period2": {...},
  "change": {
    "avg_people_change": 14.3,
    "worse": true
  }
}
```

---

## 📈 Visualization Format (Frontend-Ready)

**All time-series endpoints return bucketed data:**

```json
{
  "buckets": [
    {
      "timestamp": "2026-01-02T10:00:00Z",
      "hour_label": "10:00",
      "avg_people": 285,
      "max_people": 320,
      "avg_risk": 65.3
    },
    ...
  ],
  "bucket_size": "1h",  // or "5min" for shorter periods
  "total_buckets": 24
}
```

**Bucketing rules:**
- Period < 6 hours → 5-minute buckets
- Period 6-24 hours → 1-hour buckets
- Period > 24 hours → 1-hour buckets (aggregated)

---

## 🧪 Testing Strategy (10-15 Min Data)

### Problem
Videos loop, so we can't wait days for real patterns.

### Solution: Data Simulation Mode

**Option 1: Time-Compressed Testing**
```python
# In metrics_writer.py, add test mode:
class MetricsWriter:
    def __init__(self, ..., test_mode=False, time_multiplier=60):
        self.test_mode = test_mode
        self.time_multiplier = time_multiplier  # 1 min = 60 min
        
    async def _write_with_retry(self, metrics):
        if self.test_mode:
            # Adjust timestamp to simulate hours passing
            metrics['timestamp'] = time.time() + (elapsed * time_multiplier)
```

**Usage:**
1. Start server with `TEST_MODE=true`
2. Let it run for 15 real minutes
3. System thinks 15 hours passed (60x speed)
4. Analytics has enough data to compute trends

**Option 2: Historical Data Injection**
```python
# Script: tests/inject_test_data.py
# Injects 7 days of synthetic data based on patterns:
# - Morning ramp-up (6AM-10AM)
# - Peak (10AM-12PM)
# - Lunch dip (12PM-2PM)
# - Evening peak (5PM-8PM)
# - Night quiet (10PM-6AM)
```

Run before testing:
```bash
python tests/inject_test_data.py --days=7 --area=test_area_main
```

**Option 3: Clone Real Data** (Recommended)
```python
# Script: tests/clone_metrics_data.py
# 1. Run system for 10 minutes
# 2. Capture pattern (high/medium/low)
# 3. Replicate pattern across 7 days with variations
# 4. Insert into MongoDB with adjusted timestamps
```

This gives realistic data with actual detection quality.

---

## 🎯 Implementation Order

### Phase 3A: Foundation (Week 1)
1. ✅ Create analytics module structure
2. ✅ Add hourly aggregation collections to MongoDB
3. ✅ Implement background aggregation job
4. ✅ Add cache layer
5. ✅ Test hourly aggregation with 10-min real data

### Phase 3B: Core Analytics (Week 2)
6. ✅ Implement time_series.py (trends, forecast)
7. ✅ Implement patterns.py (peak hours, classification)
8. ✅ Implement anomalies.py (z-score, spikes)
9. ✅ Test each module with synthetic data

### Phase 3C: APIs (Week 3)
10. ✅ Create analytics.py router
11. ✅ Add all 5 main endpoints
12. ✅ Integrate caching
13. ✅ Add Swagger docs
14. ✅ Test all endpoints

### Phase 3D: Testing & Validation (Week 4)
15. ✅ Run data injection script
16. ✅ Validate analytics accuracy
17. ✅ Performance test (query times < 500ms)
18. ✅ Frontend integration prep

---

## ⚠️ Critical Decisions Locked

| Topic | Decision | Reason |
|-------|----------|--------|
| Analytics data source | Hourly aggregates | Avoid expensive queries |
| Anomaly detection source | Raw recent data only | Need real-time precision |
| Forecasting method | Linear + confidence | Simple, honest, fast |
| Caching strategy | In-memory TTL | No Redis yet, keep simple |
| GeoJSON usage | Defer to Phase 4 | Spatial ≠ temporal |
| Frontend format | Bucketed time-series | Frontend can't aggregate |
| ML models | Not needed yet | Simple math sufficient |
| Detection changes | ZERO changes | Analytics reads only |

---

## 📊 Success Metrics

After Phase 3 implementation:
- ✅ Operators can see if crowd is growing/shrinking
- ✅ System knows "normal" vs "abnormal" for each hour
- ✅ 30-min forecasts help with proactive response
- ✅ Historical comparisons provide context
- ✅ All analytics queries < 500ms (with cache)
- ✅ Detection accuracy unchanged (still 30 Hz, no lag)
- ✅ MongoDB storage optimized (hourly rollups)

---

## 🚫 Out of Scope (Phase 4+)

- Spatial analysis (GeoJSON, spillover, heatmaps)
- Machine learning models (LSTM, ARIMA)
- Redis caching
- Multi-event correlation
- Evacuation routing
- Police deployment optimization

**One sentence to remember:**
> Phase 3 is about understanding TIME, not SPACE.

---

## 🔄 Next Steps

1. Review this plan
2. Confirm testing strategy (which option?)
3. Start with Phase 3A (foundation)
4. Validate each component before moving forward

**Ready to implement?** Let's start with the hourly aggregation job.
