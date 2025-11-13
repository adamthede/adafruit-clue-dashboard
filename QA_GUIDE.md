# QA Testing Guide - Backend Analysis Engine

**Feature:** Backend Analysis Engine
**Branch:** `claude/implement-feature-011CV52DNvkhFAMnoqrypV2A`
**Version:** 1.0
**Last Updated:** 2024

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Automated Testing](#automated-testing)
4. [Manual Testing](#manual-testing)
5. [Integration Testing](#integration-testing)
6. [Performance Testing](#performance-testing)
7. [Edge Case Testing](#edge-case-testing)
8. [Regression Testing](#regression-testing)
9. [Troubleshooting](#troubleshooting)
10. [Success Criteria](#success-criteria)

---

## Overview

This guide provides comprehensive QA testing procedures for the Backend Analysis Engine implementation. The analysis engine processes CSV sensor data to compute statistics, detect patterns, and identify anomalies.

**What's Being Tested:**
- Analysis engine initialization and integration
- Statistical analysis methods
- Correlation calculations
- Anomaly detection
- Pattern analysis (daily/weekly)
- Performance and caching
- Error handling
- Integration with existing application

---

## Prerequisites

### 1. Environment Setup

```bash
# Pull the feature branch
git checkout claude/implement-feature-011CV52DNvkhFAMnoqrypV2A
git pull origin claude/implement-feature-011CV52DNvkhFAMnoqrypV2A

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import pandas, numpy; print(f'✅ pandas {pandas.__version__}, numpy {numpy.__version__}')"
```

### 2. Data Requirements

**Option A: Use Existing Data**
- Existing CSV file at: `~/Library/Application Support/ClueGatewayWebview/sensor_data.csv`
- Should contain columns: `gw_timestamp`, `temperature_sht`, `humidity`, `pressure`, `light`, `sound_level`, `color_hex`

**Option B: Generate Test Data**
```bash
# Automated test script can create test data
python3 qa_automated_test.py --create-data
```

---

## Automated Testing

### Quick Automated Test

The fastest way to validate the implementation:

```bash
# Run automated QA test suite
python3 qa_automated_test.py --verbose
```

**Expected Output:**
```
============================================================
AUTOMATED QA TEST SUITE - Analysis Engine Integration
============================================================
[HH:MM:SS] PASS  | ✅ Engine instantiation
[HH:MM:SS] PASS  | ✅ get_data_summary() no error
...
============================================================
TEST SUMMARY
============================================================
Tests run:  50+
Passed:     50+ ✅
Failed:     0 ❌
Warnings:   X ⚠️
============================================================
🎉 ALL TESTS PASSED!
```

### Automated Test Coverage

The automated test script validates:

1. **Engine Initialization** - Instance creation, CSV loading
2. **Data Summary** - Record counts, date ranges, sensor availability
3. **Statistical Analysis** - Min, max, mean, median, std dev for all sensors
4. **Correlation Analysis** - Matrix calculation, diagonal validation
5. **Anomaly Detection** - Z-score calculation, threshold testing
6. **Pattern Analysis** - Weekly patterns (168 data points)
7. **Scatter Data** - Two-sensor correlation plots
8. **Period Comparison** - Multiple time range comparisons
9. **Performance** - Execution time, cache effectiveness
10. **Edge Cases** - Invalid inputs, error handling

### Creating Test Data

```bash
# Create fresh test data (2000 records over 14 days)
python3 qa_automated_test.py --create-data --verbose
```

---

## Manual Testing

### 1. Standalone Unit Tests

Test the analysis engine in isolation:

```bash
# Run the original test suite
python3 test_analysis_engine.py
```

**What to Check:**
- ✅ All 8 tests pass
- ✅ No errors or exceptions
- ✅ Reasonable performance (< 2s total)

---

### 2. Integration Testing via Application

Start the application and test via browser console.

#### Step 1: Start the Application

```bash
python3 gateway_webview.py
```

**Check Logs:**
```bash
# In another terminal
tail -f ~/Library/Logs/ClueGatewayWebview/gateway_webview.log
```

**Look for:**
```
INFO - Analysis Engine initialized successfully
```

If you see this error instead:
```
ERROR - Failed to initialize Analysis Engine: ...
```
Check the [Troubleshooting](#troubleshooting) section.

---

#### Step 2: Open Browser DevTools

1. In the application window, right-click → **Inspect** (or press F12/Cmd+Option+I)
2. Navigate to **Console** tab
3. Run the test commands below

---

### 3. Browser Console Tests

Copy and paste these tests into the browser console:

#### Test 1: Data Summary
```javascript
pywebview.api.get_data_summary().then(result => {
    console.log('📊 Data Summary:', result);
    console.table({
        'Total Records': result.total_records,
        'Start Date': result.date_range?.start,
        'End Date': result.date_range?.end,
        'Days Covered': result.date_range?.days
    });
    console.log('Sensors:', result.sensors);
});
```

**Expected Output:**
```javascript
{
  total_records: 1000,
  date_range: {
    start: "2024-XX-XXT...",
    end: "2024-XX-XXT...",
    days: 7
  },
  sensors: {
    temperature_sht: 1000,
    humidity: 1000,
    ...
  },
  file_path: "/path/to/sensor_data.csv"
}
```

---

#### Test 2: Temperature Statistics
```javascript
pywebview.api.get_statistics('temperature_sht', '24h').then(stats => {
    console.log('🌡️ Temperature Statistics (24h):', stats);
    console.table({
        'Count': stats.count,
        'Mean': stats.mean?.toFixed(2) + '°F',
        'Min': stats.min?.toFixed(2) + '°F',
        'Max': stats.max?.toFixed(2) + '°F',
        'Median': stats.median?.toFixed(2) + '°F',
        'Std Dev': stats.std_dev?.toFixed(2),
        'P25': stats.percentile_25?.toFixed(2) + '°F',
        'P75': stats.percentile_75?.toFixed(2) + '°F',
        'P95': stats.percentile_95?.toFixed(2) + '°F'
    });
});
```

**Validation:**
- ✅ `count > 0`
- ✅ `min < mean < max`
- ✅ `percentile_25 < median < percentile_75`
- ✅ Reasonable temperature values (e.g., 60-80°F for indoor)

---

#### Test 3: All Time Ranges
```javascript
async function testAllTimeRanges() {
    const ranges = ['1h', '6h', '24h', '7d', '30d', 'all'];
    console.log('⏱️ Testing all time ranges...');

    for (const range of ranges) {
        const stats = await pywebview.api.get_statistics('temperature_sht', range);
        if (stats.error) {
            console.log(`  ${range}: ❌ ${stats.error}`);
        } else {
            console.log(`  ${range}: ✅ ${stats.count} records, mean=${stats.mean?.toFixed(2)}°F`);
        }
    }

    console.log('✅ Time range tests complete');
}

testAllTimeRanges();
```

---

#### Test 4: Correlation Matrix
```javascript
pywebview.api.get_correlation_matrix('7d').then(corr => {
    console.log('📈 Correlation Matrix (7d):');
    console.log('Sensors:', corr.labels);

    // Create a formatted table
    const table = {};
    for (let i = 1; i < corr.matrix.length; i++) {
        const row = {};
        for (let j = 0; j < corr.labels.length; j++) {
            row[corr.labels[j]] = corr.matrix[i][j]?.toFixed(3);
        }
        table[corr.labels[i-1]] = row;
    }
    console.table(table);
});
```

**Validation:**
- ✅ Diagonal values are 1.0 (or very close)
- ✅ Matrix is symmetric
- ✅ Values are between -1 and 1
- ✅ Expected correlations (e.g., temp vs humidity typically negative)

---

#### Test 5: Anomaly Detection
```javascript
pywebview.api.get_anomalies('temperature_sht', 2.5, '7d').then(anomalies => {
    console.log(`🚨 Anomalies Found: ${anomalies.total_count}`);
    console.log(`Mean: ${anomalies.mean?.toFixed(2)}°F, Std Dev: ${anomalies.std_dev?.toFixed(2)}`);

    if (anomalies.total_count > 0) {
        console.log('First 5 anomalies:');
        console.table(anomalies.anomalies.slice(0, 5));
    }
});
```

**Validation:**
- ✅ `total_count >= 0`
- ✅ Each anomaly has: `timestamp`, `value`, `z_score`, `deviation`
- ✅ Z-scores exceed threshold (2.5 in this case)

---

#### Test 6: Weekly Pattern
```javascript
pywebview.api.get_weekly_pattern('temperature_sht', 4).then(pattern => {
    console.log(`📅 Weekly Pattern (4 weeks):`);
    console.log(`Total points: ${pattern.pattern?.length}`);

    // Find average for each day
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dailyAvg = {};

    days.forEach(day => {
        const dayPoints = pattern.pattern.filter(p => p.day === day && p.value !== null);
        const avg = dayPoints.reduce((sum, p) => sum + p.value, 0) / dayPoints.length;
        dailyAvg[day] = avg.toFixed(2) + '°F';
    });

    console.table(dailyAvg);

    // Show 9 AM values for each day
    console.log('9 AM values by day:');
    const nineAM = {};
    days.forEach(day => {
        const point = pattern.pattern.find(p => p.day === day && p.hour === 9);
        nineAM[day] = point?.value?.toFixed(2) + '°F' || 'N/A';
    });
    console.table(nineAM);
});
```

**Validation:**
- ✅ Exactly 168 data points (7 days × 24 hours)
- ✅ Each point has: `day`, `day_num`, `hour`, `value`
- ✅ Hours range from 0-23
- ✅ Days are Monday-Sunday

---

#### Test 7: Scatter Plot Data
```javascript
pywebview.api.get_scatter_data('temperature_sht', 'humidity', '24h', 100).then(scatter => {
    console.log(`📊 Scatter Data: ${scatter.sensor_x} vs ${scatter.sensor_y}`);
    console.log(`Points returned: ${scatter.count}`);

    if (scatter.count > 0) {
        console.log('First 5 points:');
        console.table(scatter.points.slice(0, 5));

        // Simple statistics
        const xValues = scatter.points.map(p => p.x);
        const yValues = scatter.points.map(p => p.y);
        console.log('X range:', Math.min(...xValues).toFixed(2), '-', Math.max(...xValues).toFixed(2));
        console.log('Y range:', Math.min(...yValues).toFixed(2), '-', Math.max(...yValues).toFixed(2));
    }
});
```

**Validation:**
- ✅ `count <= max_points` (respects limit)
- ✅ Each point has `x` and `y` values
- ✅ No NaN or null values in points

---

#### Test 8: Period Comparison
```javascript
pywebview.api.compare_periods('temperature_sht', '24h', '7d').then(comparison => {
    console.log('📊 Period Comparison:');

    const p1 = comparison.period1.stats;
    const p2 = comparison.period2.stats;
    const diff = comparison.differences;

    console.table({
        'Metric': ['Mean', 'Median', 'Std Dev', 'Count'],
        '24h': [
            p1.mean?.toFixed(2) + '°F',
            p1.median?.toFixed(2) + '°F',
            p1.std_dev?.toFixed(2),
            p1.count
        ],
        '7d': [
            p2.mean?.toFixed(2) + '°F',
            p2.median?.toFixed(2) + '°F',
            p2.std_dev?.toFixed(2),
            p2.count
        ],
        'Difference': [
            diff.mean_diff?.toFixed(2) + '°F',
            diff.median_diff?.toFixed(2) + '°F',
            diff.std_dev_diff?.toFixed(2),
            diff.count_diff
        ]
    });

    if (diff.mean_pct_change) {
        console.log(`Mean % Change: ${diff.mean_pct_change.toFixed(2)}%`);
    }
});
```

---

#### Test 9: Daily Pattern
```javascript
// Test daily aggregates for today
const today = new Date().toISOString().split('T')[0];

pywebview.api.get_daily_pattern('temperature_sht', today).then(daily => {
    console.log(`📅 Daily Pattern for ${today}:`);

    if (daily.error) {
        console.log('❌', daily.error);
    } else {
        console.log(`Aggregates for ${daily.aggregates?.length} hours:`);
        console.table(daily.aggregates);
    }
});
```

---

#### Test 10: All Sensors Test
```javascript
async function testAllSensors() {
    const sensors = ['temperature_sht', 'humidity', 'pressure', 'light', 'sound_level'];
    console.log('🔬 Testing all sensors (24h)...');

    for (const sensor of sensors) {
        const stats = await pywebview.api.get_statistics(sensor, '24h');
        if (stats.error) {
            console.log(`  ${sensor}: ❌ ${stats.error}`);
        } else {
            console.log(`  ${sensor}: ✅ count=${stats.count}, mean=${stats.mean?.toFixed(2)}`);
        }
    }

    console.log('✅ All sensor tests complete');
}

testAllSensors();
```

---

## Performance Testing

### Test 1: Execution Time

```javascript
async function testPerformance() {
    console.log('⚡ Performance Tests:');

    // Test 1: Statistics (30d)
    console.time('stats-30d');
    await pywebview.api.get_statistics('temperature_sht', '30d');
    console.timeEnd('stats-30d');

    // Test 2: Cached statistics
    console.time('stats-30d-cached');
    await pywebview.api.get_statistics('temperature_sht', '30d');
    console.timeEnd('stats-30d-cached');

    // Test 3: Correlation matrix
    console.time('correlation-7d');
    await pywebview.api.get_correlation_matrix('7d');
    console.timeEnd('correlation-7d');

    // Test 4: Anomaly detection
    console.time('anomalies-7d');
    await pywebview.api.get_anomalies('temperature_sht', 2.5, '7d');
    console.timeEnd('anomalies-7d');

    console.log('✅ Performance tests complete');
}

testPerformance();
```

**Performance Targets:**
- ✅ Statistics (30d): < 1000ms
- ✅ Cached query: < 100ms
- ✅ Correlation matrix: < 3000ms
- ✅ Anomaly detection: < 1000ms

---

### Test 2: Large Dataset Performance

If you have 6+ months of data (100K+ records):

```javascript
async function testLargeDataset() {
    console.log('📊 Large Dataset Performance:');

    const start = performance.now();
    const stats = await pywebview.api.get_statistics('temperature_sht', 'all');
    const duration = performance.now() - start;

    console.log(`Processed ${stats.count} records in ${duration.toFixed(2)}ms`);
    console.log(`Performance: ${(stats.count / (duration/1000)).toFixed(0)} records/sec`);

    if (duration < 5000) {
        console.log('✅ Performance acceptable for large dataset');
    } else {
        console.warn('⚠️ Performance may need optimization');
    }
}

testLargeDataset();
```

---

## Edge Case Testing

### Test Invalid Inputs

```javascript
async function testEdgeCases() {
    console.log('🔍 Edge Case Tests:');

    // Test 1: Invalid sensor
    const invalid = await pywebview.api.get_statistics('invalid_sensor', '24h');
    console.log('Invalid sensor:', invalid.error ? '✅ Error returned' : '❌ No error');

    // Test 2: Invalid time range
    const invalidRange = await pywebview.api.get_statistics('temperature_sht', 'invalid');
    console.log('Invalid time range:', invalidRange.count >= 0 ? '✅ Handled gracefully' : '❌');

    // Test 3: Empty custom range
    const emptyRange = await pywebview.api.get_statistics('temperature_sht', {});
    console.log('Empty range dict:', emptyRange.count >= 0 || emptyRange.error ? '✅' : '❌');

    // Test 4: Future date range (no data expected)
    const futureRange = await pywebview.api.get_statistics('temperature_sht', {
        start: '2030-01-01T00:00:00Z',
        end: '2030-01-02T00:00:00Z'
    });
    console.log('Future date range:', futureRange.error ? '✅ No data error' : '❌');

    // Test 5: Very old date range
    const oldRange = await pywebview.api.get_statistics('temperature_sht', {
        start: '2020-01-01T00:00:00Z',
        end: '2020-01-02T00:00:00Z'
    });
    console.log('Old date range:', oldRange.error || oldRange.count === 0 ? '✅' : '❌');

    // Test 6: Invalid threshold
    const invalidThreshold = await pywebview.api.get_anomalies('temperature_sht', -1, '24h');
    console.log('Negative threshold:', invalidThreshold.total_count >= 0 ? '✅ Handled' : '❌');

    console.log('✅ Edge case tests complete');
}

testEdgeCases();
```

---

## Regression Testing

Ensure existing functionality still works:

### 1. Serial Connection Test
```
✅ Can connect to CLUE device
✅ Data streams correctly
✅ Real-time chart updates
✅ CSV file receives new data
```

### 2. Data Export Test
```javascript
// Test chart data export (use UI button or API)
pywebview.api.export_chart_data('24h').then(result => {
    console.log('Export result:', result);
    // Should open file dialog
});
```

### 3. Adafruit IO Test
```
✅ AIO credentials still work
✅ Data uploads successfully
✅ No new errors in logs
```

### 4. Application Stability
```
✅ No crashes on startup
✅ No memory leaks (check Activity Monitor)
✅ Logs show no new errors
✅ UI remains responsive
```

---

## Troubleshooting

### Issue: "Analysis engine not initialized"

**Symptoms:**
```javascript
{error: "Analysis engine not initialized"}
```

**Diagnosis:**
```bash
# Check logs
tail -n 50 ~/Library/Logs/ClueGatewayWebview/gateway_webview.log | grep -i "analysis"
```

**Solutions:**
1. Check pandas/numpy installed: `pip list | grep -E "pandas|numpy"`
2. Verify CSV file exists: `ls -lh ~/Library/Application\ Support/ClueGatewayWebview/sensor_data.csv`
3. Check for import errors in logs
4. Restart application

---

### Issue: "ModuleNotFoundError: pandas"

**Solution:**
```bash
pip install -r requirements.txt
# or specifically:
pip install pandas>=2.0.0 numpy>=1.24.0
```

---

### Issue: Slow Performance (> 5s for queries)

**Diagnosis:**
```bash
# Check CSV file size
ls -lh ~/Library/Application\ Support/ClueGatewayWebview/sensor_data.csv
wc -l ~/Library/Application\ Support/ClueGatewayWebview/sensor_data.csv
```

**Solutions:**
1. If > 1M records, consider archiving old data
2. Check available RAM: System may be swapping
3. Clear cache by restarting application
4. Use shorter time ranges ('7d' instead of 'all')

---

### Issue: No Data Found Errors

**Symptoms:**
```javascript
{error: "No data found for this time range"}
```

**Solutions:**
1. Check if you have data for the requested time range
2. Run data summary: `pywebview.api.get_data_summary()`
3. Try 'all' time range to see if any data exists
4. Verify CSV file is not empty

---

### Issue: Correlation Matrix Errors

**Symptoms:**
```javascript
{error: "No numeric data available"}
```

**Solutions:**
1. Ensure you have numeric sensors (not just color_hex)
2. Check for data quality issues (all NaN values)
3. Try a different time range with more data

---

## Success Criteria

### Functional Requirements
- ✅ Analysis engine initializes without errors
- ✅ All API methods return valid JSON
- ✅ Statistics are mathematically correct (min < mean < max)
- ✅ Correlation matrix values are between -1 and 1
- ✅ Anomalies have z-scores exceeding threshold
- ✅ Weekly pattern has exactly 168 points
- ✅ All time ranges work correctly
- ✅ Error handling works for invalid inputs

### Performance Requirements
- ✅ Statistics (30d): < 1 second
- ✅ Cached queries: < 100ms
- ✅ Correlation matrix: < 3 seconds
- ✅ Memory usage: < 500MB for full dataset
- ✅ No memory leaks over extended use

### Integration Requirements
- ✅ Imports successfully into gateway_webview.py
- ✅ No errors on application startup
- ✅ Logs show "Analysis Engine initialized successfully"
- ✅ All API methods callable from JavaScript
- ✅ No impact on serial/chart/export functionality

### Code Quality
- ✅ No console errors in browser DevTools
- ✅ No exceptions in application logs
- ✅ Automated tests pass (50+ tests)
- ✅ All sensors tested
- ✅ Edge cases handled gracefully

---

## Quick QA Checklist

Use this for rapid validation:

```
□ Dependencies installed (pip install -r requirements.txt)
□ Application starts without errors
□ Log shows "Analysis Engine initialized successfully"
□ get_data_summary() returns data
□ get_statistics('temperature_sht', '24h') works
□ get_correlation_matrix('7d') works
□ get_anomalies() finds anomalies (if data has outliers)
□ get_weekly_pattern() returns 168 points
□ Serial connection still works
□ Chart updates still work
□ Data export still works
□ No new errors in browser console
□ No memory leaks (check Activity Monitor)
□ Automated tests pass: python3 qa_automated_test.py
```

---

## Additional Resources

- **Test Data Generator:** `test_analysis_engine.py` creates sample data
- **Automated Tests:** `qa_automated_test.py --verbose`
- **Manual Tests:** See sections above
- **Log File:** `~/Library/Logs/ClueGatewayWebview/gateway_webview.log`
- **Data File:** `~/Library/Application Support/ClueGatewayWebview/sensor_data.csv`

---

## Reporting Issues

If you find bugs during QA:

1. **Capture the error:**
   - Browser console output
   - Application log excerpt
   - Steps to reproduce

2. **Gather context:**
   - Data summary: `pywebview.api.get_data_summary()`
   - Record count and date range
   - System info (OS, Python version)

3. **Create an issue:**
   - Include error message
   - Include reproduction steps
   - Tag with "bug" and "analysis-engine"

---

**Last Updated:** November 2024
**Maintainer:** Analysis Engine Team
