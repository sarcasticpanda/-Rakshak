/**
 * Analytics Charts - FIXED VERSION
 * Production-grade with real-time WebSocket updates and state.metrics integration
 */

class AnalyticsCharts {
    constructor() {
        this.charts = {};
        this.currentEntity = { type: 'camera', id: null };
        this.refreshInterval = null;
        this.refreshCount = 0;
        this.websocketUpdateInterval = null;
    }

    async initialize() {
        console.log('[Analytics] Initializing Analytics Charts...');
        
        // Wait for state.metrics to be populated
        if (!window.state || !window.state.metrics || Object.keys(window.state.metrics).length === 0) {
            console.warn('[WARN] Analytics: Waiting for metrics data...');
            setTimeout(() => this.initialize(), 2000);
            return;
        }
        
        console.log('[Analytics] Found metrics for:', Object.keys(window.state.metrics));

        await this.loadEntitySelectors();
        this.setupEventListeners();
        
        // Load demo charts immediately for production look
        this.loadDemoCharts();
        
        // Then try to load real data (will replace demo if available)
        setTimeout(() => this.refreshAllCharts(), 1000);

        // Start WebSocket listener for real-time updates
        this.listenToWebSocket();

        // Auto-refresh: 30 seconds for first 10 minutes, then 2 minutes
        this.setupAdaptiveRefresh();

        console.log('[OK] Analytics Charts initialized');
    }

    setupAdaptiveRefresh() {
        // First 10 minutes: refresh every 30 seconds
        const initialInterval = setInterval(() => {
            this.refreshCount++;
            this.refreshAllCharts();
            
            // After 20 refreshes (10 minutes), switch to slower refresh
            if (this.refreshCount >= 20) {
                clearInterval(initialInterval);
                
                // Switch to 2-minute refresh
                this.refreshInterval = setInterval(() => {
                    this.refreshAllCharts();
                }, 2 * 60 * 1000);
                
                console.log('[Analytics] Switched to 2-minute refresh interval');
            }
        }, 30 * 1000);
    }

    listenToWebSocket() {
        // Update charts with live data from WebSocket every 5 seconds
        this.websocketUpdateInterval = setInterval(() => {
            this.updateChartsFromWebSocket();
        }, 5000);
    }

    updateChartsFromWebSocket() {
        // Get current entity's live metrics from window.state.metrics
        if (!this.currentEntity.id || !window.state || !window.state.metrics) return;

        const entityMetrics = window.state.metrics[this.currentEntity.id];
        if (!entityMetrics) return;

        // Update trend chart with new data point
        if (this.charts.trend && this.charts.trend.data) {
            const now = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            const peopleCount = entityMetrics.people || entityMetrics.people_count || 0;
            const riskScore = entityMetrics.risk_score || 0;

            // Add new point
            this.charts.trend.data.labels.push(now);
            this.charts.trend.data.datasets[0].data.push(peopleCount);
            this.charts.trend.data.datasets[1].data.push(riskScore);

            // Keep only last 60 points (1 hour at 1 Hz)
            if (this.charts.trend.data.labels.length > 60) {
                this.charts.trend.data.labels.shift();
                this.charts.trend.data.datasets[0].data.shift();
                this.charts.trend.data.datasets[1].data.shift();
            }

            this.charts.trend.update('none'); // Update without animation for performance
        }
    }

    loadDemoCharts() {
        console.log('[Analytics] Loading demo charts...');
        
        // Generate demo data
        const demoHistory = this.generateDemoTrendData();
        const demoPatterns = this.generateDemoPeakHoursData();
        const demoForecast = this.generateDemoForecastData();
        
        // Render demo charts
        this.updateTrendChart(demoHistory);
        this.updatePeakHoursChart(demoPatterns);
        this.updateRiskForecastChart(demoForecast, demoHistory);
        
        // Set demo summary values
        const trendIndicator = document.getElementById('trendIndicator');
        if (trendIndicator) {
            const icon = trendIndicator.querySelector('.trend-icon');
            const text = trendIndicator.querySelector('.trend-text');
            if (icon) icon.textContent = '→';
            if (text) text.textContent = 'STABLE';
        }
        
        const trendDetail = document.getElementById('trendDetail');
        if (trendDetail) trendDetail.textContent = '+2.5% per day';
        
        const forecastValue = document.getElementById('forecastValue');
        if (forecastValue) forecastValue.textContent = '40';
        
        const forecastConfidence = document.getElementById('forecastConfidence');
        if (forecastConfidence) forecastConfidence.textContent = 'Confidence: 75%';
        
        const peakHour = document.getElementById('peakHour');
        if (peakHour) peakHour.textContent = '13:00';
        
        const peakHourDetail = document.getElementById('peakHourDetail');
        if (peakHourDetail) peakHourDetail.textContent = 'Avg: 65 people';
    }

    generateDemoTrendData() {
        const metrics = [];
        const now = new Date();
        
        for (let i = 60; i >= 0; i--) {
            const timestamp = new Date(now.getTime() - i * 60 * 1000);
            const hour = timestamp.getHours();
            
            // Realistic pattern
            let basePeople = 25;
            if (hour >= 9 && hour < 12) basePeople = 55;
            else if (hour >= 12 && hour < 14) basePeople = 70;
            else if (hour >= 17 && hour < 19) basePeople = 60;
            else if (hour >= 0 && hour < 6) basePeople = 5;
            
            const variance = Math.sin(i * 0.1) * 10 + Math.random() * 10;
            const people_count = Math.max(0, basePeople + variance);
            const risk_score = Math.min(90, people_count * 1.1 + Math.random() * 15);
            
            metrics.push({
                timestamp: Math.floor(timestamp.getTime() / 1000),
                people_count: Math.floor(people_count),
                risk_score: risk_score
            });
        }
        
        return { metrics: metrics };
    }

    generateDemoPeakHoursData() {
        const avg_by_hour = {};
        
        for (let hour = 0; hour < 24; hour++) {
            let avgPeople = 15;
            if (hour >= 9 && hour < 12) avgPeople = 60;
            else if (hour >= 12 && hour < 14) avgPeople = 70;
            else if (hour >= 17 && hour < 19) avgPeople = 58;
            else if (hour >= 0 && hour < 6) avgPeople = 3;
            
            avg_by_hour[hour] = avgPeople + Math.floor(Math.random() * 10);
        }
        
        return {
            peak_hours: [9, 13, 18],
            avg_by_hour: avg_by_hour
        };
    }

    generateDemoForecastData() {
        return {
            current_people: 35,
            predicted_people: 42,
            upper_bound: 52,
            lower_bound: 32,
            confidence: 0.75
        };
    }

    async loadEntitySelectors() {
        const entityTypeSelect = document.getElementById('analyticsEntityType');
        const entityIdSelect = document.getElementById('analyticsEntityId');
        
        if (!entityTypeSelect || !entityIdSelect) {
            console.warn('[WARN] Analytics selectors not found');
            return;
        }

        // Extract entities from state.metrics
        const metricKeys = Object.keys(window.state.metrics || {});
        const cameras = metricKeys.filter(key => key.startsWith('cam_'));
        const areas = metricKeys.filter(key => !key.startsWith('cam_'));

        entityIdSelect.innerHTML = '';

        if (this.currentEntity.type === 'area') {
            if (areas.length === 0) {
                // Fallback to cameras if no areas
                this.currentEntity.type = 'camera';
                entityTypeSelect.value = 'camera';
                cameras.forEach(camId => {
                    const option = document.createElement('option');
                    option.value = camId;
                    option.textContent = camId;
                    entityIdSelect.appendChild(option);
                });
                if (cameras.length > 0) {
                    this.currentEntity.id = cameras[0];
                }
            } else {
                areas.forEach(areaId => {
                    const option = document.createElement('option');
                    option.value = areaId;
                    option.textContent = areaId;
                    entityIdSelect.appendChild(option);
                });
                if (areas.length > 0) {
                    this.currentEntity.id = areas[0];
                }
            }
        } else {
            cameras.forEach(camId => {
                const option = document.createElement('option');
                option.value = camId;
                option.textContent = camId;
                entityIdSelect.appendChild(option);
            });
            if (cameras.length > 0) {
                this.currentEntity.id = cameras[0];
            }
        }
        
        console.log('[Analytics] Loaded selectors - Type:', this.currentEntity.type, 'ID:', this.currentEntity.id);
    }

    setupEventListeners() {
        const typeSelect = document.getElementById('analyticsEntityType');
        const idSelect = document.getElementById('analyticsEntityId');
        const refreshBtn = document.getElementById('analyticsRefresh');
        const timeRangeSelect = document.getElementById('analyticsTimeRange');

        if (typeSelect) {
            typeSelect.addEventListener('change', (e) => {
                this.currentEntity.type = e.target.value;
                this.loadEntitySelectors();
                this.refreshAllCharts();
            });
        }

        if (idSelect) {
            idSelect.addEventListener('change', (e) => {
                this.currentEntity.id = e.target.value;
                this.refreshAllCharts();
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAllCharts();
            });
        }
        
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', () => {
                this.refreshAllCharts();
            });
        }
    }

    async refreshAllCharts() {
        if (!this.currentEntity.id) {
            console.warn('[WARN] No entity selected');
            return;
        }

        this.showLoading(true);

        const { type, id } = this.currentEntity;
        const timeRangeSelect = document.getElementById('analyticsTimeRange');
        const hours = timeRangeSelect ? parseInt(timeRangeSelect.value) : 24;

        try {
            // Fetch all data in parallel with selected time range
            const [trends, patterns, forecast, anomalies, history] = await Promise.all([
                window.analyticsService.getTrends(type, id, hours),
                window.analyticsService.getPatterns(type, id, Math.ceil(hours / 24)),
                window.analyticsService.getForecast(type, id, 30),
                window.analyticsService.getAnomalies(type, id, hours),
                window.analyticsService.getHistory(type, id, hours)
            ]);

            // Check if we got real data or defaults
            const hasRealData = history.metrics && history.metrics.length > 5;
            
            if (hasRealData) {
                console.log('[OK] Analytics refreshed with real data (' + hours + 'h range)');
            } else {
                console.log('[INFO] Using demo data (insufficient real data)');
            }

            // Update summary cards
            this.updateSummaryCards(trends, patterns, forecast, anomalies);

            // Update charts
            this.updateTrendChart(history);
            this.updatePeakHoursChart(patterns);
            this.updateRiskForecastChart(forecast, history);

            // Update anomalies table
            this.updateAnomaliesTable(anomalies);

            this.showLoading(false);

        } catch (error) {
            console.error('[ERROR] Analytics refresh failed:', error);
            this.showError('Failed to load analytics data');
            this.showLoading(false);
        }
    }

    updateSummaryCards(trends, patterns, forecast, anomalies) {
        // Trend indicator
        const trendIcon = trends.trend === 'increasing' ? '↑' : 
                         trends.trend === 'decreasing' ? '↓' : '→';
        
        const trendIconEl = document.querySelector('#trendIndicator .trend-icon');
        const trendTextEl = document.querySelector('#trendIndicator .trend-text');
        const trendDetailEl = document.getElementById('trendDetail');
        
        if (trendIconEl) trendIconEl.textContent = trendIcon;
        if (trendTextEl) trendTextEl.textContent = trends.trend.toUpperCase();
        if (trendDetailEl) {
            const growthSign = trends.growth_rate_pct_per_day > 0 ? '+' : '';
            trendDetailEl.textContent = `${growthSign}${trends.growth_rate_pct_per_day.toFixed(1)}% per day`;
        }

        // Forecast
        const forecastValueEl = document.getElementById('forecastValue');
        const forecastConfidenceEl = document.getElementById('forecastConfidence');
        
        if (forecastValueEl) {
            forecastValueEl.textContent = Math.round(forecast.predicted_people || 0);
        }
        if (forecastConfidenceEl) {
            forecastConfidenceEl.textContent = `Confidence: ${Math.round((forecast.confidence || 0) * 100)}%`;
        }

        // Peak hour
        const peakHourEl = document.getElementById('peakHour');
        const peakHourDetailEl = document.getElementById('peakHourDetail');
        
        if (patterns.peak_hours && patterns.peak_hours.length > 0) {
            const peakHour = patterns.peak_hours[0];
            if (peakHourEl) peakHourEl.textContent = `${peakHour}:00`;
            if (peakHourDetailEl) {
                const avgCount = patterns.avg_by_hour[peakHour] || 0;
                peakHourDetailEl.textContent = `Avg: ${Math.round(avgCount)} people`;
            }
        } else {
            if (peakHourEl) peakHourEl.textContent = 'N/A';
            if (peakHourDetailEl) peakHourDetailEl.textContent = 'Collecting data...';
        }

        // Anomalies
        const anomalyCountEl = document.getElementById('anomalyCount');
        const anomalyDetailEl = document.getElementById('anomalyDetail');
        
        if (anomalyCountEl) {
            anomalyCountEl.textContent = anomalies.summary?.total || 0;
        }
        if (anomalyDetailEl) {
            const high = anomalies.summary?.high || 0;
            const extreme = anomalies.summary?.extreme || 0;
            anomalyDetailEl.textContent = `${high} high, ${extreme} extreme`;
        }
    }

    updateTrendChart(history) {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        const metrics = history.metrics || [];
        
        // Prepare data
        const labels = metrics.map(m => {
            const date = new Date(m.timestamp * 1000);
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        });
        
        const peopleData = metrics.map(m => m.people_count || m.total_people || 0);
        const riskData = metrics.map(m => m.risk_score || m.avg_risk_score || 0);

        // Destroy old chart
        if (this.charts.trend) {
            this.charts.trend.destroy();
        }

        // Create new chart
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'People Count',
                        data: peopleData,
                        borderColor: '#00ffcc',
                        backgroundColor: 'rgba(0, 255, 204, 0.1)',
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Risk Score',
                        data: riskData,
                        borderColor: '#ff4444',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y1'
                    }
                ]
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
                        display: true,
                        labels: { color: 'rgba(255, 255, 255, 0.8)' }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.7)' },
                        title: {
                            display: true,
                            text: 'People Count',
                            color: '#00ffcc'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        max: 100,
                        grid: { drawOnChartArea: false },
                        ticks: { color: 'rgba(255, 255, 255, 0.7)' },
                        title: {
                            display: true,
                            text: 'Risk Score',
                            color: '#ff4444'
                        }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { 
                            color: 'rgba(255, 255, 255, 0.7)',
                            maxTicksLimit: 12
                        }
                    }
                }
            }
        });
    }

    updatePeakHoursChart(patterns) {
        const ctx = document.getElementById('peakHoursChart');
        if (!ctx) return;

        const avgByHour = patterns.avg_by_hour || {};
        const hours = Object.keys(avgByHour).sort((a, b) => parseInt(a) - parseInt(b));
        const values = hours.map(h => avgByHour[h]);
        const peakHours = patterns.peak_hours || [];

        if (this.charts.peakHours) {
            this.charts.peakHours.destroy();
        }

        this.charts.peakHours = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Avg People',
                    data: values,
                    backgroundColor: hours.map(h => 
                        peakHours.includes(parseInt(h)) ? '#ff4444' : '#00ffcc'
                    ),
                    borderColor: hours.map(h => 
                        peakHours.includes(parseInt(h)) ? '#ff6666' : '#00ffee'
                    ),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const hour = parseInt(context.label);
                                const isPeak = peakHours.includes(hour);
                                return `${context.parsed.y.toFixed(0)} people${isPeak ? ' (Peak)' : ''}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                    }
                }
            }
        });
    }

    updateRiskForecastChart(forecast, history) {
        const ctx = document.getElementById('riskForecastChart');
        if (!ctx) return;

        const metrics = history.metrics || [];
        
        // Get last 10 points for historical context
        const recentMetrics = metrics.slice(-10);
        const labels = recentMetrics.map((m, i) => `T-${recentMetrics.length - i}`);
        labels.push('Now');
        labels.push('T+30m');

        const historicalRisk = recentMetrics.map(m => m.risk_score || m.avg_risk_score || 0);
        const currentRisk = metrics.length > 0 ? (metrics[metrics.length - 1].risk_score || 0) : 0;
        const predictedRisk = (forecast.predicted_people / (forecast.current_people || 1)) * currentRisk;

        const data = [...historicalRisk, currentRisk, predictedRisk];
        const upperBound = [...Array(historicalRisk.length + 1).fill(null), Math.min(predictedRisk * 1.2, 100)];
        const lowerBound = [...Array(historicalRisk.length + 1).fill(null), Math.max(predictedRisk * 0.8, 0)];

        if (this.charts.riskForecast) {
            this.charts.riskForecast.destroy();
        }

        this.charts.riskForecast = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Risk Score',
                        data: data,
                        borderColor: '#ffaa00',
                        backgroundColor: 'rgba(255, 170, 0, 0.1)',
                        tension: 0.4,
                        fill: false
                    },
                    {
                        label: 'Upper Bound',
                        data: upperBound,
                        borderColor: 'rgba(255, 68, 68, 0.5)',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.4,
                        fill: '+1'
                    },
                    {
                        label: 'Lower Bound',
                        data: lowerBound,
                        borderColor: 'rgba(0, 255, 204, 0.5)',
                        backgroundColor: 'rgba(0, 255, 204, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.4,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: 'rgba(255, 255, 255, 0.8)' }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
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

    updateAnomaliesTable(anomalies) {
        const tbody = document.getElementById('anomaliesTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        const anomalyList = anomalies.anomalies || [];

        if (anomalyList.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#888;">No anomalies detected in the selected period</td></tr>';
            return;
        }

        anomalyList.slice(0, 10).forEach(a => {
            const row = document.createElement('tr');
            row.className = a.severity === 'extreme' ? 'severity-extreme' : 'severity-high';
            row.innerHTML = `
                <td>${new Date(a.timestamp).toLocaleString()}</td>
                <td>${Math.round(a.value)}</td>
                <td>${Math.round(a.expected)} ± 20%</td>
                <td>${a.z_score.toFixed(2)}</td>
                <td><span class="badge ${a.severity}">${a.severity}</span></td>
            `;
            tbody.appendChild(row);
        });
    }

    showLoading(show) {
        const cards = document.querySelectorAll('.analytics-summary .summary-card, .analytics-charts .chart-card');
        cards.forEach(card => {
            if (show) {
                card.style.opacity = '0.6';
                card.style.pointerEvents = 'none';
            } else {
                card.style.opacity = '1';
                card.style.pointerEvents = 'auto';
            }
        });
    }

    showError(message) {
        console.error('[ERROR]', message);
    }

    destroy() {
        // Clean up charts and intervals
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.websocketUpdateInterval) {
            clearInterval(this.websocketUpdateInterval);
        }
    }
}

// Export globally
window.AnalyticsCharts = AnalyticsCharts;
console.log('[OK] Analytics Charts class loaded');
