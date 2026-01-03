// Test Analytics Initialization
console.log('=== ANALYTICS DEBUG TEST ===');

setTimeout(() => {
    console.log('1. Chart.js loaded:', typeof Chart !== 'undefined');
    console.log('2. AnalyticsCharts class loaded:', typeof AnalyticsCharts !== 'undefined');
    console.log('3. analyticsService loaded:', typeof window.analyticsService !== 'undefined');
    console.log('4. State populated:', window.state ? {
        cameras: window.state.cameras.length,
        areas: window.state.areas.length
    } : 'NO STATE');
    console.log('5. Analytics DOM elements:');
    console.log('   - analytics page:', !!document.getElementById('analytics'));
    console.log('   - trendChart canvas:', !!document.getElementById('trendChart'));
    console.log('   - peakHoursChart canvas:', !!document.getElementById('peakHoursChart'));
    console.log('   - riskForecastChart canvas:', !!document.getElementById('riskForecastChart'));
    
    if (window.analyticsChartsInstance) {
        console.log('6. Analytics instance:', window.analyticsChartsInstance);
    } else {
        console.log('6. NO ANALYTICS INSTANCE - Manually initializing...');
        if (typeof AnalyticsCharts !== 'undefined') {
            window.analyticsChartsInstance = new AnalyticsCharts();
            window.analyticsChartsInstance.initialize();
        }
    }
}, 5000);
