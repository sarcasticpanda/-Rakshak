## 🔍 DATA FLOW DIAGNOSIS

### Problem Analysis

**Issue:** Backend is connected and running, but frontend shows **NO DATA** - all values remain at 0.

---

### Root Cause Investigation

Based on the backend logs and code review, here's what's happening:

#### 1. **Backend is Processing Data ✅**
- Metrics aggregator is running
- Cameras are detecting people
- density_normalized = 1.0 (indicating 100% density)
- Backend shows processing is working

#### 2. **Backend Structure Issue ❌**
The main.py file is at `backend/main.py` **BUT** the code imports assume `backend/app/main.py` structure.

**Current Structure:**
```
backend/
  main.py  ← HERE (wrong location)
  app/
    api/
      cameras.py
```

**Expected Structure:**
```
backend/
  app/
    main.py  ← SHOULD BE HERE
    api/
      cameras.py
```

#### 3. **WebSocket Data Format Issue** 🔍
Backend sends `density` field, but needs `density_normalized`.
Backend metrics object structure needs verification.

---

### Why Data Isn't Showing

**Critical Issues Found:**

1. **Backend imports failing** - The startup script uses `uvicorn app.main:app` but main.py is at wrong location
2. **SharedStore might not have metrics** - The `get_metrics()` might be returning `None` or empty data
3. **WebSocket format mismatch** - Frontend expects specific field names that backend might not be sending
4. **Startup script uses WRONG path** - It tries `uvicorn app.main:app` when it should use `uvicorn main:app`

---

### Immediate Fixes Needed

**Priority 1 - Fix Backend Path:**
1. Fix START_INTEGRATED_SYSTEM.bat to use `uvicorn main:app` instead of `uvicorn app.main:app`
2. OR move main.py into app/ folder

**Priority 2 - Verify WebSocket Data:**
1. Check if WebSocket is sending `risk_score` or `risk_level`
2. Check if `density` field exists
3. Verify `people_count` is being sent

**Priority 3 - Check SharedStore:**
1. Verify `shared_store.get_metrics()` returns data
2. Check if metrics are being written to SharedStore correctly

**Priority 4 - Frontend Data Handling:**
1. Verify `handleMetricsUpdate()` is processing WebSocket messages
2. Check if `state.metrics` is being populated
3. Verify DOM update functions are being called

---

### Step-by-Step Fix Plan

#### Step 1: Fix Startup Script ✅ URGENT
The batch file at line 83 has:
```bat
start "जनRakshak Backend" cmd /k "cd /d %cd% && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
```

**FIX:** Change to:
```bat
start "जनRakshak Backend" cmd /k "cd /d %cd% && venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
```

#### Step 2: Test Backend API Endpoint
Run this to check if backend returns data:
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8000/cameras"
$response[0].latest_metrics
```

**Expected:** Should show metrics object with people_count, risk_score, density

**If null:** SharedStore isn't being populated correctly

#### Step 3: Test WebSocket Data
Open browser console and check:
```javascript
// Should see this in console:
📨 WebSocket message received: {cameras: 3}
📹 cam_stampede: {people: X, risk_score: Y, density: Z}
```

**If missing:** WebSocket isn't sending data correctly

#### Step 4: Check Frontend State
In browser console, run:
```javascript
console.log('Cameras:', state.cameras.length);
console.log('Metrics:', Object.keys(state.metrics).length);
console.log('First metric:', state.metrics[state.cameras[0]?.camera_id]);
```

**Expected:** Should show camera count and metrics data

**If 0:** Frontend isn't storing WebSocket data

---

### Quick Diagnostic Commands

Run these in PowerShell to diagnose:

```powershell
# Test 1: Check if backend is responding
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Test 2: Get cameras with metrics
$cams = Invoke-RestMethod -Uri "http://localhost:8000/cameras"
Write-Host "Cameras returned: $($cams.Count)"
$cams[0] | ConvertTo-Json -Depth 3

# Test 3: Check fallback endpoint
$metrics = Invoke-RestMethod -Uri "http://localhost:8000/cameras/metrics/latest"
$metrics | ConvertTo-Json -Depth 3
```

---

### Expected vs Actual

#### Backend Should Send (WebSocket):
```json
{
  "timestamp": 1735948800.123,
  "cameras": {
    "cam_stampede": {
      "camera_id": "cam_stampede",
      "people_count": 452,
      "density": 0.65,
      "risk_score": 85.3,
      "timestamp": 1735948800.123
    }
  }
}
```

#### Frontend Expects:
- `metric.people_count` - Number
- `metric.risk_score` - Number (0-100)
- `metric.density` - Number (0-1)

#### Frontend Updates These Elements:
- `#selectedCameraCount` - Shows people count
- `#selectedCameraDensity` - Shows density %
- `#activeAlertsCount` - Shows cameras with risk > 90
- `.total-visitors-all` - Shows total visitors
- Chart data points

---

### Next Action

**IMMEDIATE:** Fix the startup script path issue first, then restart backend.

**THEN:** Check browser console for WebSocket messages.

**FINALLY:** Verify data is flowing through the complete pipeline.

