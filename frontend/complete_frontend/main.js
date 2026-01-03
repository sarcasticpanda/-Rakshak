// Page Navigation
const navLinks = document.querySelectorAll('.nav-links li');
const pages = document.querySelectorAll('.page');
const cameraItems = document.querySelectorAll('.camera-item');

// Add camera feed click handlers
const cameraFeeds = document.querySelectorAll('.camera-feed');

function navigateToPage(pageId) {
    pages.forEach(page => page.classList.remove('active'));
    navLinks.forEach(link => link.classList.remove('active'));

    const selectedPage = document.getElementById(pageId);
    const selectedLink = document.querySelector(`[data-page="${pageId}"]`);

    if (selectedPage && selectedLink) {
        selectedPage.classList.add('active');
        selectedLink.classList.add('active');

        if (pageId === 'dashboard') {
            resetDashboardToOverview();
        }
        
        // Initialize analytics when user navigates to Analytics tab
        if (pageId === 'analytics') {
            console.log('[Navigation] User navigated to Analytics tab');
            
            // Give the page time to become visible
            setTimeout(() => {
                // Try force-init first (from analytics-force-init.js)
                if (window.analyticsChartsForced) {
                    console.log('[Navigation] Charts already initialized by force-init');
                    return;
                }
                
                // Fallback to regular initialization
                if (window.analyticsChartsInstance && window.analyticsChartsInstance.initialize) {
                    console.log('[Navigation] Re-initializing analytics with current data');
                    window.analyticsChartsInstance.initialize();
                } else if (window.AnalyticsCharts) {
                    console.log('[Navigation] Creating new analytics instance');
                    window.analyticsChartsInstance = new AnalyticsCharts();
                    window.analyticsChartsInstance.initialize();
                } else {
                    console.warn('[Navigation] AnalyticsCharts class not loaded yet');
                }
            }, 100);
        }
    }
}

navLinks.forEach(link => {
    link.addEventListener('click', () => {
        const pageId = link.getAttribute('data-page');
        navigateToPage(pageId);
    });
});

cameraItems.forEach(item => {
    item.addEventListener('click', () => {
        const pageId = item.getAttribute('data-page');
        navigateToPage(pageId);
    });
});

cameraFeeds.forEach(feed => {
    feed.addEventListener('click', () => {
        const cameraId = feed.getAttribute('data-camera-id');
        const cameraName = feed.getAttribute('data-camera-name');

        navigateToPage('dashboard');
        updateDashboardForCamera(cameraId, cameraName);
    });
});

// Update time
function updateTime() {
    const now = new Date();
    document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
}
setInterval(updateTime, 1000);
updateTime(); // Initialize immediately

// Density Chart
const ctx = document.getElementById('densityChart').getContext('2d');
let labels = [];
let countData = [];
let densityData = [];
const maxPoints = 24 * 60 * 60; // 24 hours, 1 point per second = 86,400 points
let lastDensity = 0.2; // Start density at a reasonable value

const densityChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: []  // Will be populated dynamically per camera
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: { 
                    color: 'rgba(255, 255, 255, 0.7)',
                    font: { size: 11 },
                    padding: 10
                }
            },
            title: {
                display: true,
                text: 'Crowd Density Over Time\nAI-enhanced real-time monitoring',
                color: 'rgba(255, 255, 255, 0.7)',
                font: { size: 16 }
            },
            zoom: {
                pan: { enabled: true, mode: 'x' },
                zoom: {
                    wheel: { enabled: true },
                    pinch: { enabled: true },
                    mode: 'x'
                }
            }
        },
        scales: {
            y: {
                type: 'linear',
                position: 'left',
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                ticks: { 
                    color: 'rgba(255, 255, 255, 0.7)',
                    callback: function(value) {
                        return value + '%';
                    }
                },
                title: {
                    display: true,
                    text: 'Density (%)',
                    color: 'rgba(255, 255, 255, 0.7)'
                }
            },
            x: {
                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                ticks: { color: 'rgba(255, 255, 255, 0.7)', maxTicksLimit: 12 }
            }
        },
        animation: { duration: 0 }
    }
});

// Chart updates are now handled by app.js updateLiveStats() using real WebSocket data
// No need for simulated data anymore - real metrics come from backend

// Export chart globally for app.js to access
window.densityChart = densityChart;

console.log('✅ Chart initialized and exported to window.densityChart');

// Initialize analytics chart with Django API fetch
const analyticsCtx = document.getElementById('analyticsChart');
if (analyticsCtx) {
    // Removed old Django API call - will integrate with new backend analytics
    /*
    fetch('http://127.0.0.1:8000/base/getinfo')
        .then(response => response.json())
        .then(data => {
            const analyticsChart = new Chart(analyticsCtx, {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: 'rgba(255, 255, 255, 0.7)' }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        },
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        }
                    }
                }
            });
        })
        .catch(error => console.log('Analytics chart will be populated with real data'));
    */
    // Placeholder chart until analytics integration
    const analyticsChart = new Chart(analyticsCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Weekly Visitors',
                data: [1200, 1900, 1500, 2100, 1800, 2400, 2000],
                borderColor: '#00ffcc',
                backgroundColor: 'rgba(0, 255, 204, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: 'rgba(255, 255, 255, 0.7)' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                }
            }
        }
    });
}

// Simulate real-time updates (disabled when using real backend)
function updateRandomData() {
    // Skip if real backend is connected
    if (window.rakshakApp && window.rakshakApp.state.ws && window.rakshakApp.state.ws.readyState === WebSocket.OPEN) {
        return;
    }
    
    const newCount = Math.floor(Math.random() * 1000) + 2000;
    const element = document.querySelector('.stat-value');
    if (element) element.textContent = newCount.toLocaleString();

    const newDensity = Math.floor(Math.random() * 30) + 50;
    const densityElements = document.querySelectorAll('.stat-value');
    if (densityElements[1]) densityElements[1].textContent = newDensity + '%';

    if (densityChart && densityChart.data.datasets[0]) {
        const newData = densityChart.data.datasets[0].data.slice(1);
        newData.push(Math.floor(Math.random() * 400) + 200);
        densityChart.data.datasets[0].data = newData;

        const newDensityData = densityChart.data.datasets[1].data.slice(1);
        newDensityData.push(Math.random() * 0.6 + 0.2);
        densityChart.data.datasets[1].data = newDensityData;

        densityChart.update();
    }
}
setInterval(updateRandomData, 5000);

// Theme toggle
const themeToggle = document.querySelector('.theme-toggle');
themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light-theme');
    themeToggle.textContent = document.body.classList.contains('light-theme') ? '🌙' : '☀';
});

// Initialize progress ring animation
const circle = document.querySelector('.progress-ring-circle');
const percentageText = document.querySelector('.progress-content .percentage');
const radius = circle.r.baseVal.value;
const circumference = radius * 2 * Math.PI;

circle.style.strokeDasharray = `${circumference} ${circumference}`;

function setProgress(percent) {
    const offset = circumference * (1 - percent / 100);
    circle.style.strokeDashoffset = offset;
    percentageText.textContent = `${Math.round(percent)}%`;
}

function getRandomPercentage() {
    return Math.random() * (97 - 85) + 85;
}

function updateProgress() {
    const newPercentage = getRandomPercentage();
    setProgress(newPercentage);
}

setProgress(89);
setInterval(updateProgress, 3000);

// Alert Filter Buttons
const filterButtons = document.querySelectorAll('#alerts .filter-btn');
const alertItems = document.querySelectorAll('#alerts .alert-item');

function filterAlerts(filter) {
    alertItems.forEach(item => {
        const priority = item.getAttribute('data-priority');
        if (filter === 'all' || priority === filter) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

filterButtons.forEach(button => {
    button.addEventListener('click', () => {
        filterButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        const filter = button.getAttribute('data-filter');
        filterAlerts(filter);
    });
});

filterAlerts('all');

// Function to update dashboard for a specific camera
function updateDashboardForCamera(cameraId, cameraName) {
    document.querySelector('#dashboard .top-bar h1').textContent =
        `AI-Powered Crowd Monitoring - ${cameraName}`;

    const cameraData = {
        '1': { visitors: 850, density: 75, alerts: 1 },
        '2': { visitors: 620, density: 60, alerts: 1 },
        '3': { visitors: 340, density: 45, alerts: 0 },
        '4': { visitors: 450, density: 55, alerts: 0 },
        '5': { visitors: 280, density: 40, alerts: 0 },
        '6': { visitors: 150, density: 30, alerts: 0 }
    };

    const totalVisitorsAllCameras = Object.values(cameraData).reduce((sum, data) => sum + data.visitors, 0);
    const data = cameraData[cameraId] || { visitors: 0, density: 0, alerts: 0 };

    const statValues = document.querySelectorAll('#dashboard .stat-value');
    statValues[0].textContent = data.visitors.toLocaleString();
    statValues[1].textContent = `${data.density}%`;
    statValues[2].textContent = data.alerts;
    statValues[3].textContent = '1/1';

    document.querySelector('.total-visitors-all').textContent = totalVisitorsAllCameras.toLocaleString();

    const densityTag = document.querySelector('#dashboard .density-tag');
    densityTag.textContent = data.density > 80 ? 'High' :
                             data.density > 60 ? 'Moderate' : 'Low';

    const alertsList = document.querySelector('#dashboard .alerts-list');
    alertsList.innerHTML = '';

    switch(cameraId) {
        case '1':
            alertsList.innerHTML = `
                <div class="alert-item high">
                    <span class="alert-icon">⚠️</span>
                    <div class="alert-content">
                        <h4>Overcrowding Detected</h4>
                        <p>${cameraName}</p>
                    </div>
                    <span class="alert-time">2 minutes ago</span>
                    <span class="alert-priority">high</span>
                </div>
            `;
            break;
        case '2':
            alertsList.innerHTML = `
                <div class="alert-item medium">
                    <span class="alert-icon">⚠️</span>
                    <div class="alert-content">
                        <h4>Unusual Movement Pattern</h4>
                        <p>${cameraName}</p>
                    </div>
                    <span class="alert-time">15 minutes ago</span>
                    <span class="alert-priority">medium</span>
                </div>
            `;
            break;
        default:
            alertsList.innerHTML = '<p>No active alerts for this camera</p>';
    }

    densityChart.data.datasets[0].data = getCameraChartData(cameraId);
    densityChart.data.datasets[1].data = getCameraDensityData(cameraId);
    densityChart.update();
}

// Sample chart data functions
function getCameraChartData(cameraId) {
    const data = {
        '1': [250, 300, 400, 500, 350],
        '2': [150, 200, 250, 300, 220],
        '3': [100, 120, 150, 180, 140],
        '4': [120, 150, 200, 250, 180],
        '5': [80, 100, 140, 180, 120],
        '6': [50, 70, 90, 110, 80]
    };
    return data[cameraId] || [0, 0, 0, 0, 0];
}

function getCameraDensityData(cameraId) {
    const data = {
        '1': [0.3, 0.4, 0.5, 0.6, 0.45],
        '2': [0.2, 0.25, 0.3, 0.35, 0.28],
        '3': [0.15, 0.18, 0.22, 0.25, 0.2],
        '4': [0.18, 0.22, 0.28, 0.32, 0.25],
        '5': [0.12, 0.15, 0.2, 0.25, 0.18],
        '6': [0.1, 0.12, 0.15, 0.18, 0.13]
    };
    return data[cameraId] || [0, 0, 0, 0, 0];
}

// Reset dashboard to overview
function resetDashboardToOverview() {
    document.querySelector('#dashboard .top-bar h1').textContent =
        'AI-Powered Crowd Monitoring';

    const cameraData = {
        '1': { visitors: 850, density: 75, alerts: 1 },
        '2': { visitors: 620, density: 60, alerts: 1 },
        '3': { visitors: 340, density: 45, alerts: 0 },
        '4': { visitors: 450, density: 55, alerts: 0 },
        '5': { visitors: 280, density: 40, alerts: 0 },
        '6': { visitors: 150, density: 30, alerts: 0 }
    };
    const totalVisitorsAllCameras = Object.values(cameraData).reduce((sum, data) => sum + data.visitors, 0);

    const statValues = document.querySelectorAll('#dashboard .stat-value');
    statValues[0].textContent = '2,810';
    statValues[1].textContent = '66%';
    statValues[2].textContent = '2';
    statValues[3].textContent = '12/14';

    document.querySelector('.total-visitors-all').textContent = totalVisitorsAllCameras.toLocaleString();

    document.querySelector('#dashboard .density-tag').textContent = 'Moderate';

    const alertsList = document.querySelector('#dashboard .alerts-list');
    alertsList.innerHTML = `
        <div class="alert-item high">
            <span class="alert-icon">⚠️</span>
            <div class="alert-content">
                <h4>Overcrowding Detected</h4>
                <p>Main Entrance</p>
            </div>
            <span class="alert-time">2 minutes ago</span>
            <span class="alert-priority">high</span>
        </div>
        <div class="alert-item medium">
            <span class="alert-icon">⚠️</span>
            <div class="alert-content">
                <h4>Unusual Movement Pattern</h4>
                <p>Food Court</p>
            </div>
            <span class="alert-time">15 minutes ago</span>
            <span class="alert-priority">medium</span>
        </div>
    `;

    densityChart.data.datasets[0].data = [200, 400, 500, 600, 400];
    densityChart.data.datasets[1].data = [0.2, 0.4, 0.6, 0.8, 0.5];
    densityChart.update();
}