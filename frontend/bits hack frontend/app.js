/**
 * जनRakshak - Backend Integration
 * Real-time connection to stampede detection system
 */

// Configuration
const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/metrics';

// State Management
const state = {
    cameras: [],
    areas: [],
    selectedCamera: null,
    metrics: {},
    alerts: [],
    ws: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    console.log('🚀 Initializing जनRakshak...');
    console.log('📡 Backend API:', API_BASE);
    console.log('🔌 WebSocket URL:', WS_URL);
    
    try {
        // Load cameras and areas
        await loadCameras();
        await loadAreas();
        
        console.log(`✅ Loaded ${state.cameras.length} cameras and ${state.areas.length} areas`);
        
        // Connect to WebSocket
        connectWebSocket();
        
        // Initialize UI immediately with loaded data
        updateDashboard();
        updateCameraFeeds();
        updateCameraManagement();
        
        // Set up periodic UI refresh
        setInterval(() => {
            if (state.cameras.length > 0) {
                updateLiveStats();
            }
        }, 1000);
        
        console.log('✅ Initialization complete');
        
        // Populate camera selector dropdown
        populateCameraSelector();
        
        // Wire camera selector change event
        const cameraSelector = document.getElementById('cameraSelector');
        if (cameraSelector) {
            cameraSelector.addEventListener('change', (e) => {
                const selectedValue = e.target.value;
                if (selectedValue === 'all') {
                    state.selectedCamera = null;
                } else {
                    state.selectedCamera = selectedValue;
                }
                updateDashboard();
                console.log('📹 Camera selector changed:', selectedValue);
            });
        }
        
        // Wire management UI buttons if present
        const addBtn = document.getElementById('addCameraBtn');
        const refreshBtn = document.getElementById('refreshCamerasBtn');
        if (addBtn) addBtn.addEventListener('click', addCamera);
        if (refreshBtn) refreshBtn.addEventListener('click', async () => {
            await loadCameras();
            updateCameraFeeds();
            updateCameraManagement();
        });
    } catch (error) {
        console.error('❌ Initialization failed:', error);
        showError('Failed to connect to backend. Is the server running at ' + API_BASE + '?');
    }
}

// ============================================
// API CALLS
// ============================================

async function loadCameras() {
    try {
        console.log('🔄 Fetching cameras from:', `${API_BASE}/cameras`);
        const response = await fetch(`${API_BASE}/cameras`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📦 Raw cameras response:', data);
        
        // Backend returns array directly, not {cameras: []}
        state.cameras = Array.isArray(data) ? data : [];
        console.log(`📹 Loaded ${state.cameras.length} cameras:`, state.cameras.map(c => c.camera_id));
        
        // Initialize metrics with latest data from cameras
        state.cameras.forEach(cam => {
            if (cam.latest_metrics) {
                state.metrics[cam.camera_id] = cam.latest_metrics;
                console.log(`  ✅ ${cam.camera_id}: ${cam.latest_metrics.people_count} people, risk ${(cam.latest_metrics.risk_level * 100).toFixed(0)}%`);
            } else {
                console.log(`  ⚠️ ${cam.camera_id}: No metrics yet`);
            }
        });
    } catch (error) {
        console.error('❌ Failed to load cameras:', error.message);
        console.error('   Is backend running at:', API_BASE);
        state.cameras = [];
    }
}

async function loadAreas() {
    try {
        const response = await fetch(`${API_BASE}/areas`);
        const data = await response.json();
        state.areas = data.areas || [];
        console.log(`🏢 Loaded ${state.areas.length} areas`);
    } catch (error) {
        console.error('Failed to load areas:', error);
        state.areas = [];
    }
}

// ============================================
// WEBSOCKET CONNECTION
// ============================================

function connectWebSocket() {
    if (state.ws) {
        state.ws.close();
    }
    
    console.log('🔌 Connecting to WebSocket:', WS_URL);
    
    try {
        state.ws = new WebSocket(WS_URL);
        
        state.ws.onopen = () => {
            console.log('✅ WebSocket connected successfully!');
            state.reconnectAttempts = 0;
            updateConnectionStatus(true);
        };
        
        state.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📨 WebSocket message received:', {
                    cameras: data.camera_metrics?.length || Object.keys(data.cameras || {}).length,
                    areas: data.area_metrics?.length || 0
                });
                handleMetricsUpdate(data);
            } catch (error) {
                console.error('❌ Error parsing WebSocket message:', error);
            }
        };
        
        state.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            console.error('WebSocket URL:', WS_URL);
            console.error('Make sure backend is running on port 8000');
            updateConnectionStatus(false);
        };
        
        state.ws.onclose = (event) => {
            console.log('🔌 WebSocket disconnected', {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });
            updateConnectionStatus(false);
            
            // Attempt reconnection
            if (state.reconnectAttempts < state.maxReconnectAttempts) {
                state.reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 30000);
                console.log(`🔄 Reconnecting in ${delay}ms... (attempt ${state.reconnectAttempts})`);
                setTimeout(connectWebSocket, delay);
            } else {
                console.error('❌ Max reconnection attempts reached. Please refresh the page.');
            }
        };
    } catch (error) {
        console.error('❌ Failed to create WebSocket:', error);
        updateConnectionStatus(false);
    }
}

function handleMetricsUpdate(data) {
    console.log('📡 WebSocket data received:', data);
    
    // Handle NEW FORMAT: data.cameras is an object {cam_id: metrics}
    if (data.cameras && typeof data.cameras === 'object' && !Array.isArray(data.cameras)) {
        Object.entries(data.cameras).forEach(([cameraId, metric]) => {
            state.metrics[cameraId] = metric;
            
            // Debug - show both risk_score and risk_level
            console.log(`  📹 ${cameraId}:`, {
                people: metric.people_count || 0,
                risk_score: metric.risk_score,
                risk_level: metric.risk_level,
                density: metric.density
            });
        });
        console.log(`📊 Updated metrics for ${Object.keys(data.cameras).length} cameras`);
    }
    // Handle OLD FORMAT: data.camera_metrics is an array
    else if (data.camera_metrics && Array.isArray(data.camera_metrics)) {
        data.camera_metrics.forEach(metric => {
            state.metrics[metric.camera_id] = metric;
            console.log(`  📹 ${metric.camera_id}: ${metric.people_count} people, risk ${(metric.risk_level * 100).toFixed(0)}%`);
        });
        console.log(`📊 Updated metrics for ${data.camera_metrics.length} cameras`);
    }
    
    // Handle area metrics (both formats)
    if (data.areas && typeof data.areas === 'object' && !Array.isArray(data.areas)) {
        Object.entries(data.areas).forEach(([areaId, metric]) => {
            state.metrics[areaId] = metric;
        });
        console.log(`📊 Updated metrics for ${Object.keys(data.areas).length} areas`);
    } else if (data.area_metrics && Array.isArray(data.area_metrics)) {
        data.area_metrics.forEach(metric => {
            state.metrics[metric.area_id] = metric;
        });
        console.log(`📊 Updated metrics for ${data.area_metrics.length} areas`);
    }
    
    // DEBUG: Show what we have in state.metrics
    console.log('🗂️ Current state.metrics:', state.metrics);
    
    // Check for critical alerts
    checkForAlerts(data);
    
    // Update UI
    updateDashboard();
    
    // Update camera feed stats (without recreating video streams)
    updateCameraFeedStats();
}

// ============================================
// ALERT SYSTEM
// ============================================

function checkForAlerts(data) {
    const now = Date.now();
    
    // Check camera metrics for high risk
    if (data.camera_metrics) {
        data.camera_metrics.forEach(metric => {
            // Generate alert for high risk (>= 0.6)
            if (metric.risk_level >= 0.6) {
                const severity = metric.risk_level >= 0.9 ? 'high' : 
                               metric.risk_level >= 0.7 ? 'high' : 'medium';
                
                addAlert({
                    type: severity,
                    title: metric.risk_level >= 0.9 ? '🚨 CRITICAL: Stampede Risk!' : 
                           metric.risk_level >= 0.7 ? '⚠️ High Crowd Density' : 
                           'ℹ️ Elevated Risk Level',
                    location: getCameraName(metric.camera_id),
                    cameraId: metric.camera_id,
                    people: metric.people_count,
                    density: metric.density || 0,
                    risk: metric.risk_level,
                    timestamp: now
                });
            }
        });
    }
    
    // Check area metrics
    if (data.area_metrics) {
        data.area_metrics.forEach(metric => {
            if (metric.risk_level >= 0.7) {
                addAlert({
                    type: 'high',
                    title: metric.risk_level >= 0.9 ? '🚨 AREA CRITICAL' : '⚠️ Area Overcrowding',
                    location: getAreaName(metric.area_id),
                    areaId: metric.area_id,
                    people: metric.total_people,
                    risk: metric.risk_level,
                    timestamp: now
                });
            }
        });
    }
}

function addAlert(alert) {
    // Check if similar alert already exists (avoid duplicates within 30 seconds)
    const exists = state.alerts.some(a => 
        a.cameraId === alert.cameraId && 
        a.type === alert.type &&
        (Date.now() - a.timestamp) < 30000 // Within last 30 seconds
    );
    
    if (!exists) {
        state.alerts.unshift(alert);
        
        // Keep only last 100 alerts
        if (state.alerts.length > 100) {
            state.alerts = state.alerts.slice(0, 100);
        }
        
        // Update alerts UI
        updateAlertsDisplay();
        
        // Play alert sound for high priority alerts
        if (alert.type === 'high' && alert.risk >= 0.8) {
            playAlertSound();
        }
        
        console.log(`🚨 Alert: ${alert.title} at ${alert.location} (Risk: ${(alert.risk * 100).toFixed(0)}%)`);
    }
}

function playAlertSound() {
    // Simple beep using Web Audio API
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.warn('Could not play alert sound:', error);
    }
}

// ============================================
// UI UPDATES
// ============================================

function updateDashboard() {
    // Update camera selector dropdown
    populateCameraSelector();
    
    // Calculate stats
    const stats = calculateAggregateStats();
    
    // Get selected camera metrics
    const selectedCameraId = state.selectedCamera;
    const selectedMetric = selectedCameraId ? (state.metrics[selectedCameraId] || {}) : null;
    
    // Update SELECTED CAMERA VISITORS card
    if (selectedCameraId && selectedMetric) {
        const camera = state.cameras.find(c => c.camera_id === selectedCameraId);
        updateElement('#selectedCameraCount', (selectedMetric.people_count || 0).toLocaleString());
        updateElement('#selectedCameraLabel', camera ? camera.name : 'Unknown Camera');
    } else {
        updateElement('#selectedCameraCount', stats.totalPeople.toLocaleString());
        updateElement('#selectedCameraLabel', 'All Cameras Combined');
    }
    
    // Update CURRENT DENSITY card (selected camera or average)
    if (selectedCameraId && selectedMetric) {
        const density = selectedMetric.density ? Math.round(selectedMetric.density * 100) : 0;
        updateElement('#selectedCameraDensity', `${density}%`);
        updateElement('#densityTagLabel', getDensityLabel(density));
    } else {
        updateElement('#selectedCameraDensity', `${stats.avgDensity}%`);
        updateElement('#densityTagLabel', getDensityLabel(stats.avgDensity));
    }
    
    // Update ACTIVE ALERTS card (cameras with risk > 90%)
    const criticalCameras = Object.values(state.metrics).filter(m => (m.risk_score || 0) > 90).length;
    updateElement('#activeAlertsCount', criticalCameras);
    
    // Update ACTIVE CAMERAS card
    updateElement('.stat-card:nth-child(4) .stat-value', `${stats.activeCameras}/${state.cameras.length}`);
    
    // Update TOTAL VISITORS (always show sum of all cameras)
    updateElement('.total-visitors-all', stats.totalPeople.toLocaleString());
    
    // Update last update time
    updateElement('#lastUpdate', new Date().toLocaleTimeString());
    
    // Update progress ring
    const processingScore = stats.activeCameras > 0 ? 
        Math.min(95, 85 + (stats.activeCameras * 2)) : 0;
    setProgress(processingScore);
}

function updateDashboardForAllCameras() {
    // Legacy function - now handled by updateDashboard()
    updateDashboard();
}

function updateDashboardForCamera(cameraId) {
    // Legacy function - now handled by updateDashboard()
    state.selectedCamera = cameraId;
    updateDashboard();
}

function updateLiveStats() {
    // Update dashboard in real-time
    updateDashboard();
    
    // Update chart with real-time data from WebSocket
    if (window.densityChart && state.cameras.length > 0) {
        const stats = calculateAggregateStats();
        const totalPeople = stats.totalPeople;
        const avgDensity = stats.avgDensity;
        
        // Add time label
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        // Update chart data
        if (!window.densityChart.data.labels) {
            window.densityChart.data.labels = [];
        }
        
        window.densityChart.data.labels.push(timeLabel);
        window.densityChart.data.datasets[0].data.push(totalPeople);
        window.densityChart.data.datasets[1].data.push(avgDensity);
        
        // Keep only last 60 points (1 minute of data at 1Hz)
        if (window.densityChart.data.labels.length > 60) {
            window.densityChart.data.labels.shift();
            window.densityChart.data.datasets[0].data.shift();
            window.densityChart.data.datasets[1].data.shift();
        }
        
        window.densityChart.update('none'); // Update without animation for performance
    }
}

function updateCameraFeeds() {
    const cameraGrid = document.querySelector('#live-feeds .camera-grid');
    if (!cameraGrid) return;
    
    cameraGrid.innerHTML = '';
    
    state.cameras.forEach(camera => {
        const feedDiv = document.createElement('div');
        feedDiv.className = 'camera-feed';
        feedDiv.setAttribute('data-camera-id', camera.camera_id);
        feedDiv.setAttribute('data-camera-name', camera.name);
        feedDiv.style.cursor = 'pointer';
        
        // Add click handler for camera selection
        feedDiv.addEventListener('click', () => {
            selectCamera(camera.camera_id);
            // Switch to dashboard to see the stats
            navigateToPage('dashboard');
        });
        
        const metric = state.metrics[camera.camera_id] || {};
        const statusClass = camera.status === 'running' ? 'online' : 'offline';
        
        feedDiv.innerHTML = `
            <div class="feed-header">
                <h3>${camera.name}</h3>
                <span class="status ${statusClass}">${camera.status || 'offline'}</span>
            </div>
            <img src="${API_BASE}/stream/${camera.camera_id}" 
                 alt="${camera.name}" 
                 class="feed-image"
                 onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100\\' height=\\'100\\'%3E%3Ctext x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\'%3ENo Signal%3C/text%3E%3C/svg%3E'">
            <div class="feed-stats">
                <span>👥 ${metric.people_count || 0} people</span>
                <span class="risk-badge risk-${getRiskClass(metric.risk_level || 0)}">
                    Risk: ${((metric.risk_level || 0) * 100).toFixed(0)}%
                </span>
            </div>
        `;
        
        feedDiv.addEventListener('click', () => selectCamera(camera.camera_id));
        cameraGrid.appendChild(feedDiv);
    });
}

function updateCameraFeedStats() {
    // Update camera feed stats without recreating video streams
    // This prevents video reloading while keeping counts updated
    const cameraFeeds = document.querySelectorAll('.camera-feed');
    
    if (cameraFeeds.length === 0) {
        console.log('⚠️ No camera feeds found in DOM');
        return;
    }
    
    cameraFeeds.forEach(feedDiv => {
        const cameraId = feedDiv.getAttribute('data-camera-id');
        const metric = state.metrics[cameraId] || {};
        
        if (metric.people_count !== undefined) {
            console.log(`📊 Updating ${cameraId}: ${metric.people_count} people, risk ${((metric.risk_level || 0) * 100).toFixed(0)}%`);
        }
        
        // Update people count
        const peopleSpan = feedDiv.querySelector('.feed-stats span:first-child');
        if (peopleSpan) {
            const peopleCount = metric.people_count || 0;
            peopleSpan.textContent = `👥 ${peopleCount} people`;
        } else {
            console.warn(`⚠️ No people span found for ${cameraId}`);
        }
        
        // Update risk badge with risk_score (0-100 range from backend)
        const riskBadge = feedDiv.querySelector('.risk-badge');
        if (riskBadge) {
            // Backend sends risk_score as 0-100, not 0-1
            let riskScore = metric.risk_score;
            
            // Validate it's a number
            if (typeof riskScore !== 'number' || isNaN(riskScore)) {
                riskScore = 0;
                console.warn(`⚠️ Invalid risk_score for ${cameraId}:`, metric.risk_score);
            }
            
            const riskPercent = Math.round(riskScore);
            riskBadge.textContent = `Risk: ${riskPercent}%`;
            
            // Update risk class for color (convert 0-100 to 0-1 for getRiskClass)
            riskBadge.className = `risk-badge risk-${getRiskClass(riskScore / 100)}`;
        }
        
        // DEBUG: Add visible overlay text on video showing risk_score
        let debugOverlay = feedDiv.querySelector('.debug-overlay');
        if (!debugOverlay) {
            debugOverlay = document.createElement('div');
            debugOverlay.className = 'debug-overlay';
            debugOverlay.style.cssText = 'position: absolute; top: 60px; left: 10px; background: rgba(0,0,0,0.8); color: #0f0; padding: 10px; font-size: 18px; font-weight: bold; z-index: 1000; border: 2px solid #0f0; border-radius: 5px;';
            feedDiv.style.position = 'relative';
            feedDiv.appendChild(debugOverlay);
        }
        
        // Use risk_score (0-100) from backend
        let riskScore = metric.risk_score;
        if (typeof riskScore !== 'number' || isNaN(riskScore)) {
            riskScore = 0;
        }
        const riskPercent = Math.round(riskScore);
        
        debugOverlay.textContent = `COUNT: ${metric.people_count || 0}\nRISK: ${riskPercent}%`;
        debugOverlay.style.whiteSpace = 'pre-line';
    });
}

function updateCameraManagement() {
    const cameraList = document.querySelector('#camera-management .camera-list');
    if (!cameraList) return;
    
    cameraList.innerHTML = '';
    
    state.cameras.forEach(camera => {
        const metric = state.metrics[camera.camera_id] || {};
        const itemDiv = document.createElement('div');
        itemDiv.className = 'camera-item';
        
        // Use risk_score (0-100) instead of risk_level (0-1)
        const riskScore = metric.risk_score || 0;
        const riskClass = riskScore >= 90 ? 'critical' : riskScore >= 70 ? 'high' : riskScore >= 50 ? 'medium' : 'low';
        
        itemDiv.innerHTML = `
            <div class="camera-item-head">
                <h3>${camera.name} <small style="font-size:12px;color:#aaa;">(${camera.camera_id})</small></h3>
                <button class="delete-camera-btn" data-camera-id="${camera.camera_id}" style="float:right;background:#ff5555;color:#fff;border:none;padding:6px 10px;border-radius:6px;cursor:pointer;">Delete</button>
            </div>
            <p>Status: <span class="status-${camera.status}">${camera.status || 'offline'}</span></p>
            <p>Location: ${camera.location || 'Unknown'}</p>
            <p>Current Count: ${metric.people_count || 0} people</p>
            <p>Risk Score: <span class="risk-${riskClass}">${riskScore.toFixed(0)}%</span></p>
        `;
        
        itemDiv.addEventListener('click', () => {
            navigateToPage('live-feeds');
            selectCamera(camera.camera_id);
        });
        
        cameraList.appendChild(itemDiv);
        // wire delete button
        const delBtn = itemDiv.querySelector('.delete-camera-btn');
        if (delBtn) {
            delBtn.addEventListener('click', (ev) => {
                ev.stopPropagation();
                const id = delBtn.getAttribute('data-camera-id');
                deleteCamera(id);
            });
        }
    });
}

// Add a new camera via backend POST /cameras
async function addCamera() {
    const id = document.getElementById('new_camera_id').value.trim();
    const name = document.getElementById('new_camera_name').value.trim();
    const source = document.getElementById('new_camera_source').value.trim();
    const location = document.getElementById('new_camera_location').value.trim();

    if (!id || !name || !source) {
        alert('Please fill camera id, name and source');
        return;
    }

    const payload = {
        camera_id: id,
        name,
        source,
        location
    };

    try {
        const res = await fetch(`${API_BASE}/cameras`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text}`);
        }

        // Reload cameras and UI
        await loadCameras();
        updateCameraFeeds();
        updateCameraManagement();
        alert('Camera added successfully');
    } catch (err) {
        console.error('Failed to add camera:', err);
        alert('Failed to add camera: ' + err.message);
    }
}

// Delete camera by ID via DELETE /cameras/{id}
async function deleteCamera(cameraId) {
    if (!confirm('Delete camera ' + cameraId + '?')) return;
    try {
        const res = await fetch(`${API_BASE}/cameras/${cameraId}`, { method: 'DELETE' });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text}`);
        }
        await loadCameras();
        updateCameraFeeds();
        updateCameraManagement();
        alert('Camera deleted');
    } catch (err) {
        console.error('Failed to delete camera:', err);
        alert('Failed to delete camera: ' + err.message);
    }
}

function updateAlertsDisplay() {
    const alertsLists = document.querySelectorAll('.alerts-list');
    
    alertsLists.forEach(alertsList => {
        alertsList.innerHTML = '';
        
        // Show latest 10 alerts
        const displayAlerts = state.alerts.slice(0, 10);
        
        if (displayAlerts.length === 0) {
            alertsList.innerHTML = '<p style="color: #33cc88; padding: 20px; text-align: center;">✅ No active alerts - All systems normal</p>';
            return;
        }
        
        displayAlerts.forEach(alert => {
            const timeAgo = formatTimeAgo(alert.timestamp);
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert-item ${alert.type}`;
            alertDiv.setAttribute('data-priority', alert.type);
            
            const densityInfo = alert.density ? ` • Density: ${(alert.density * 100).toFixed(0)}%` : '';
            
            alertDiv.innerHTML = `
                <span class="alert-icon">${alert.risk >= 0.9 ? '🚨' : alert.risk >= 0.7 ? '⚠️' : 'ℹ️'}</span>
                <div class="alert-content">
                    <h4>${alert.title}</h4>
                    <p>${alert.location}</p>
                    <small>${alert.people} people • Risk: ${(alert.risk * 100).toFixed(0)}%${densityInfo}</small>
                </div>
                <span class="alert-time">${timeAgo}</span>
                <span class="alert-priority">${alert.type}</span>
            `;
            
            alertsList.appendChild(alertDiv);
        });
    });
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function calculateAggregateStats() {
    let totalPeople = 0;
    let totalDensity = 0;
    let totalRisk = 0;
    let activeCameras = 0;
    let camerasWithMetrics = 0;
    
    state.cameras.forEach(camera => {
        const metric = state.metrics[camera.camera_id];
        if (metric) {
            totalPeople += metric.people_count || 0;
            totalDensity += (metric.density || 0) * 100;
            totalRisk += metric.risk_level || 0;
            camerasWithMetrics++;
        }
        if (camera.status === 'running') {
            activeCameras++;
        }
    });
    
    const count = camerasWithMetrics || 1;
    
    const stats = {
        totalPeople,
        avgDensity: Math.round(totalDensity / count),
        avgRisk: totalRisk / count,
        activeCameras
    };
    
    return stats;
}

function populateCameraSelector() {
    const selector = document.getElementById('cameraSelector');
    if (!selector) return;
    
    // Save current selection
    const currentSelection = selector.value;
    
    // Clear all except first option ("all")
    while (selector.options.length > 1) {
        selector.remove(1);
    }
    
    // Add camera options
    state.cameras.forEach(camera => {
        const option = document.createElement('option');
        option.value = camera.camera_id;
        option.textContent = camera.name || camera.camera_id;
        selector.appendChild(option);
    });
    
    // Restore selection if it still exists
    if (currentSelection && Array.from(selector.options).some(opt => opt.value === currentSelection)) {
        selector.value = currentSelection;
    }
}

function getDensityLabel(density) {
    if (density >= 80) return 'Critical';
    if (density >= 60) return 'High';
    if (density >= 40) return 'Medium';
    if (density >= 20) return 'Low';
    return 'Very Low';
}

function calculateAverageDensity() {
    let total = 0;
    let count = 0;
    
    state.cameras.forEach(camera => {
        const metric = state.metrics[camera.camera_id];
        if (metric && metric.density) {
            total += metric.density;
            count++;
        }
    });
    
    return count > 0 ? total / count : 0;
}

function getCameraName(cameraId) {
    const camera = state.cameras.find(c => c.camera_id === cameraId);
    return camera ? camera.name : cameraId;
}

function getAreaName(areaId) {
    const area = state.areas.find(a => a.area_id === areaId);
    return area ? area.name : areaId;
}

function getDensityLabel(density) {
    if (density >= 80) return 'Critical';
    if (density >= 60) return 'High';
    if (density >= 40) return 'Moderate';
    return 'Low';
}

function getRiskClass(risk) {
    if (risk >= 0.8) return 'critical';
    if (risk >= 0.6) return 'high';
    if (risk >= 0.4) return 'medium';
    return 'low';
}

function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function updateElement(selector, value) {
    const element = document.querySelector(selector);
    if (element) {
        element.textContent = value;
    }
}

function updateConnectionStatus(connected) {
    const statusIndicator = document.querySelector('.connection-status');
    if (statusIndicator) {
        statusIndicator.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
        statusIndicator.textContent = connected ? '● Connected' : '● Disconnected';
    }
}

function showError(message) {
    // Could implement a toast notification system
    console.error(message);
    alert(message);
}

function selectCamera(cameraId) {
    console.log('🎥 Selecting camera:', cameraId);
    state.selectedCamera = cameraId;
    
    // Update dashboard to show selected camera stats
    updateDashboard();
    
    // Add visual feedback - highlight selected camera feed
    document.querySelectorAll('.camera-feed').forEach(feed => {
        if (feed.getAttribute('data-camera-id') === cameraId) {
            feed.style.border = '3px solid #00ffaa';
            feed.style.boxShadow = '0 0 20px rgba(0, 255, 170, 0.5)';
        } else {
            feed.style.border = '1px solid rgba(255,255,255,0.1)';
            feed.style.boxShadow = 'none';
        }
    });
    
    // Show "Show All" button in header
    showClearSelectionButton();
}

function clearCameraSelection() {
    console.log('🎥 Clearing camera selection - showing all cameras');
    state.selectedCamera = null;
    
    // Update dashboard to show aggregate stats
    updateDashboard();
    
    // Remove visual feedback from all camera feeds
    document.querySelectorAll('.camera-feed').forEach(feed => {
        feed.style.border = '1px solid rgba(255,255,255,0.1)';
        feed.style.boxShadow = 'none';
    });
    
    // Hide "Show All" button
    hideClearSelectionButton();
}

function showClearSelectionButton() {
    let btn = document.getElementById('clearSelectionBtn');
    if (!btn) {
        // Create button if it doesn't exist
        const header = document.querySelector('.dashboard-header');
        if (header) {
            btn = document.createElement('button');
            btn.id = 'clearSelectionBtn';
            btn.className = 'clear-selection-btn';
            btn.innerHTML = '🔄 Show All Cameras';
            btn.onclick = clearCameraSelection;
            header.appendChild(btn);
        }
    }
    if (btn) btn.style.display = 'inline-block';
}

function hideClearSelectionButton() {
    const btn = document.getElementById('clearSelectionBtn');
    if (btn) btn.style.display = 'none';
}

// Export for main.js compatibility
window.rakshakApp = {
    state,
    loadCameras,
    loadAreas,
    updateDashboard,
    updateCameraFeeds,
    selectCamera,
    clearCameraSelection
};
