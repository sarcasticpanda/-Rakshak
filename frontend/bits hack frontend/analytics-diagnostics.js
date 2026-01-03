/**
 * Analytics Quick Diagnostics
 * Run this in browser console to check analytics status
 */

function runAnalyticsDiagnostics() {
    console.log('='.repeat(60));
    console.log('📊 ANALYTICS DIAGNOSTICS');
    console.log('='.repeat(60));
    
    const results = [];
    
    // 1. Check DOM Elements
    console.log('\n1️⃣ DOM ELEMENTS:');
    const analyticsPage = document.getElementById('analytics');
    const trendChart = document.getElementById('trendChart');
    const peakHoursChart = document.getElementById('peakHoursChart');
    const riskForecastChart = document.getElementById('riskForecastChart');
    
    results.push({ test: 'Analytics page', pass: !!analyticsPage });
    results.push({ test: 'Trend chart canvas', pass: !!trendChart });
    results.push({ test: 'Peak hours canvas', pass: !!peakHoursChart });
    results.push({ test: 'Risk forecast canvas', pass: !!riskForecastChart });
    
    console.log('   Analytics Page:', analyticsPage ? '✅ Found' : '❌ Missing');
    console.log('   Trend Chart:', trendChart ? '✅ Found' : '❌ Missing');
    console.log('   Peak Hours:', peakHoursChart ? '✅ Found' : '❌ Missing');
    console.log('   Risk Forecast:', riskForecastChart ? '✅ Found' : '❌ Missing');
    
    // 2. Check Libraries
    console.log('\n2️⃣ LIBRARIES:');
    const chartjsLoaded = typeof Chart !== 'undefined';
    const analyticsClassLoaded = typeof AnalyticsCharts !== 'undefined';
    const analyticsServiceLoaded = typeof window.analyticsService !== 'undefined';
    
    results.push({ test: 'Chart.js loaded', pass: chartjsLoaded });
    results.push({ test: 'AnalyticsCharts class', pass: analyticsClassLoaded });
    results.push({ test: 'Analytics service', pass: analyticsServiceLoaded });
    
    console.log('   Chart.js:', chartjsLoaded ? '✅ Loaded' : '❌ Not loaded');
    console.log('   AnalyticsCharts:', analyticsClassLoaded ? '✅ Loaded' : '❌ Not loaded');
    console.log('   AnalyticsService:', analyticsServiceLoaded ? '✅ Loaded' : '❌ Not loaded');
    
    // 3. Check State
    console.log('\n3️⃣ APPLICATION STATE:');
    const stateExists = typeof window.state !== 'undefined';
    const metricsExists = stateExists && window.state.metrics;
    const metricsCount = metricsExists ? Object.keys(window.state.metrics).length : 0;
    const camerasCount = stateExists && window.state.cameras ? window.state.cameras.length : 0;
    
    results.push({ test: 'State exists', pass: stateExists });
    results.push({ test: 'Metrics exists', pass: metricsExists });
    results.push({ test: 'Has metrics data', pass: metricsCount > 0 });
    
    console.log('   State:', stateExists ? '✅ Exists' : '❌ Missing');
    console.log('   Metrics:', metricsExists ? `✅ ${metricsCount} entities` : '❌ Missing');
    console.log('   Cameras:', camerasCount > 0 ? `✅ ${camerasCount} cameras` : '⚠️ No cameras');
    
    // 4. Check Charts Instance
    console.log('\n4️⃣ ANALYTICS INSTANCE:');
    const instanceExists = typeof window.analyticsChartsInstance !== 'undefined';
    const hasCharts = instanceExists && window.analyticsChartsInstance.charts;
    const trendCreated = hasCharts && window.analyticsChartsInstance.charts.trend;
    const peakCreated = hasCharts && window.analyticsChartsInstance.charts.peakHours;
    const riskCreated = hasCharts && window.analyticsChartsInstance.charts.riskForecast;
    
    results.push({ test: 'Analytics instance', pass: instanceExists });
    results.push({ test: 'Trend chart created', pass: !!trendCreated });
    results.push({ test: 'Peak chart created', pass: !!peakCreated });
    results.push({ test: 'Risk chart created', pass: !!riskCreated });
    
    console.log('   Instance:', instanceExists ? '✅ Created' : '❌ Not created');
    console.log('   Trend Chart:', trendCreated ? '✅ Rendered' : '⚠️ Not rendered');
    console.log('   Peak Chart:', peakCreated ? '✅ Rendered' : '⚠️ Not rendered');
    console.log('   Risk Chart:', riskCreated ? '✅ Rendered' : '⚠️ Not rendered');
    
    // 5. Check Visibility
    console.log('\n5️⃣ VISIBILITY:');
    const pageVisible = analyticsPage && analyticsPage.classList.contains('active');
    const canvasVisible = trendChart && window.getComputedStyle(trendChart).display !== 'none';
    const parentVisible = analyticsPage && window.getComputedStyle(analyticsPage).display !== 'none';
    
    results.push({ test: 'Analytics page active', pass: pageVisible });
    results.push({ test: 'Canvas visible', pass: !!canvasVisible });
    
    console.log('   Page Active:', pageVisible ? '✅ Yes' : '⚠️ Navigate to Analytics tab');
    console.log('   Canvas Display:', canvasVisible ? '✅ Visible' : '❌ Hidden');
    console.log('   Parent Display:', parentVisible ? '✅ Block' : '❌ None');
    
    // 6. Summary
    console.log('\n' + '='.repeat(60));
    const totalTests = results.length;
    const passedTests = results.filter(r => r.pass).length;
    const percentage = Math.round((passedTests / totalTests) * 100);
    
    console.log(`📊 SUMMARY: ${passedTests}/${totalTests} checks passed (${percentage}%)`);
    
    if (percentage === 100) {
        console.log('✅ ALL SYSTEMS GO! Analytics should be working perfectly.');
    } else if (percentage >= 75) {
        console.log('⚠️ MOSTLY WORKING. Some minor issues detected.');
    } else if (percentage >= 50) {
        console.log('⚠️ PARTIAL FUNCTIONALITY. Some components missing.');
    } else {
        console.log('❌ CRITICAL ISSUES. Analytics may not work properly.');
    }
    
    console.log('='.repeat(60));
    
    // 7. Action Items
    console.log('\n📋 ACTION ITEMS:');
    const failedTests = results.filter(r => !r.pass);
    
    if (failedTests.length === 0) {
        console.log('✅ No issues found!');
    } else {
        failedTests.forEach((test, index) => {
            console.log(`   ${index + 1}. Fix: ${test.test}`);
        });
    }
    
    // 8. Quick Fixes
    console.log('\n🔧 QUICK FIXES:');
    
    if (!pageVisible && analyticsPage) {
        console.log('   Run: document.getElementById("analytics").classList.add("active")');
        console.log('   Or: Click "Analytics" in the sidebar');
    }
    
    if (chartjsLoaded && analyticsClassLoaded && !instanceExists) {
        console.log('   Run: window.analyticsChartsInstance = new AnalyticsCharts(); window.analyticsChartsInstance.initialize();');
    }
    
    if (!chartjsLoaded) {
        console.log('   ❌ Chart.js not loaded - check CDN link in index.html');
    }
    
    if (!analyticsClassLoaded) {
        console.log('   ❌ analytics-charts.js not loaded - check script tag in index.html');
    }
    
    console.log('\n' + '='.repeat(60));
    
    return {
        passed: passedTests,
        total: totalTests,
        percentage: percentage,
        status: percentage >= 75 ? 'OK' : percentage >= 50 ? 'WARNING' : 'ERROR'
    };
}

// Auto-run if in browser
if (typeof window !== 'undefined') {
    console.log('📊 Analytics Diagnostics Tool Loaded');
    console.log('Run: runAnalyticsDiagnostics()');
    
    // Auto-run after 2 seconds
    setTimeout(() => {
        console.log('\n🤖 Auto-running diagnostics in 2 seconds...\n');
        runAnalyticsDiagnostics();
    }, 2000);
}
