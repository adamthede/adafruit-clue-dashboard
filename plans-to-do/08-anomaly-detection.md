# Implementation Plan: Anomaly Detection & Event Timeline

**Priority:** MEDIUM
**Phase:** 3
**Estimated Effort:** 5-6 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture
**Blocks:** None

---

## Overview

Implement automatic anomaly detection to identify unusual sensor readings and create an interactive event timeline that highlights significant environmental changes. This helps users quickly find interesting patterns, potential problems, or noteworthy occurrences in their 6+ months of data.

---

## Goals & Objectives

1. **Automatic Detection**: Use statistical methods to identify outliers
2. **Event Timeline**: Visual timeline showing when anomalies occurred
3. **Severity Classification**: Flag anomalies as minor, moderate, or severe
4. **Context Provision**: Show what was "normal" vs. what happened
5. **Actionable Insights**: Help users understand *why* something is unusual

---

## Architecture

### Visual Design

```
┌────────────────────────────────────────────────────────────────┐
│  Analysis Tab > Anomaly Detection                             │
├────────────────────────────────────────────────────────────────┤
│  Sensor: [Temperature ▼]  Sensitivity: [2.5σ ▼]  [Scan]     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Anomaly Summary:                                             │
│  • Found 47 anomalies in the last 6 months                    │
│  • 8 severe (>3σ), 15 moderate (2-3σ), 24 minor (<2σ)       │
│  • Most common: Temperature spikes (18 events)                │
│                                                                │
│  ──────────────────────────────────────────────────────────  │
│                                                                │
│  Event Timeline:                                              │
│  May ────●─────────●──●──── Jun ──────●──●───── Jul          │
│       5/12     5/23 5/28        6/15  6/22                   │
│                                                                │
│  Recent Anomalies:                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ⚠️  Jul 15, 2024 3:47 PM - Severe                       │ │
│  │     Temperature: 85.3°F (3.2σ above mean)                │ │
│  │     Normal range: 68-76°F, This reading: 9.3°F higher   │ │
│  │     [View Context]                                       │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ ⚠️  Jun 22, 2024 11:23 PM - Moderate                    │ │
│  │     Humidity: 62.3% (2.8σ above mean)                    │ │
│  │     Normal range: 38-52%, This reading: 10.3% higher    │ │
│  │     [View Context]                                       │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ ⚠️  Jun 15, 2024 6:12 AM - Moderate                     │ │
│  │     Sound Level: 892 (2.5σ above mean)                   │ │
│  │     Normal range: 85-200, This reading: 692 higher      │ │
│  │     [View Context]                                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  [Export Anomaly Report] [Clear Filters]                      │
└────────────────────────────────────────────────────────────────┘

Context Modal (Click "View Context"):
┌─────────────────────────────────────────────────────┐
│  Anomaly Context - Jul 15, 2024 3:47 PM       [×]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Temperature: 85.3°F                               │
│  Z-Score: +3.2σ (Severe anomaly)                   │
│                                                     │
│  Context Chart:                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ 86°F│              ★ Anomaly                  │ │
│  │     │                                         │ │
│  │ 75°F├─────────────────●●●●●●●●●──────────    │ │
│  │     │        ●●●●●●●●                  ●●●●  │ │
│  │ 64°F│  ●●●●●●                              ●●│ │
│  │     └──────────────────────────────────────  │ │
│  │      12PM   1PM    2PM    3PM    4PM    5PM  │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  Normal Behavior:                                  │
│  • Typical 3PM temp: 74.2°F (±1.8°F)              │
│  • This reading: 11.1°F above typical              │
│  • Previous spike of this magnitude: Never         │
│                                                     │
│  Surrounding Conditions:                            │
│  • Humidity: 38.2% (normal)                        │
│  • Pressure: 1013 hPa (normal)                     │
│  • Light: 3847 (bright - expected for 3PM)        │
│                                                     │
│  Possible Causes:                                   │
│  • Direct sunlight on device                       │
│  • HVAC system failure                             │
│  • External heat source nearby                     │
│                                                     │
│  [Mark as False Positive] [Add Note] [Close]       │
└─────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### HTML Structure (add to tabs/tab_analysis.html)

```html
<!-- Add this section -->
<div class="anomaly-detection">
    <h2>Anomaly Detection & Event Timeline</h2>

    <!-- Controls -->
    <div class="anomaly-controls">
        <label for="anomaly-sensor">Sensor:</label>
        <select id="anomaly-sensor">
            <option value="all">All Sensors</option>
            <option value="temperature_sht">Temperature</option>
            <option value="humidity">Humidity</option>
            <option value="pressure">Pressure</option>
            <option value="light">Light</option>
            <option value="sound_level">Sound Level</option>
        </select>

        <label for="anomaly-sensitivity">Sensitivity:</label>
        <select id="anomaly-sensitivity">
            <option value="2.0">High (2.0σ)</option>
            <option value="2.5" selected>Medium (2.5σ)</option>
            <option value="3.0">Low (3.0σ)</option>
        </select>

        <label for="anomaly-time-range">Time Range:</label>
        <select id="anomaly-time-range">
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="6m" selected>Last 6 Months</option>
            <option value="all">All Time</option>
        </select>

        <button id="scan-anomalies" class="btn-primary">Scan for Anomalies</button>
    </div>

    <!-- Summary -->
    <div id="anomaly-summary" class="anomaly-summary">
        <!-- Populated dynamically -->
    </div>

    <!-- Event Timeline -->
    <div class="anomaly-timeline-container">
        <h3>Event Timeline</h3>
        <canvas id="anomaly-timeline-canvas" width="900" height="100"></canvas>
    </div>

    <!-- Anomaly List -->
    <div class="anomaly-list-container">
        <h3>Detected Anomalies</h3>
        <div id="anomaly-list" class="anomaly-list">
            <!-- Populated dynamically -->
        </div>
    </div>

    <!-- Actions -->
    <div class="anomaly-actions">
        <button id="export-anomaly-report" class="btn-secondary">Export Anomaly Report</button>
        <button id="clear-anomaly-filters" class="btn-secondary">Clear Filters</button>
    </div>

    <!-- Context Modal -->
    <div id="anomaly-context-modal" class="modal hidden">
        <div class="modal-content large">
            <div class="modal-header">
                <h2 id="anomaly-context-title">Anomaly Context</h2>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body" id="anomaly-context-body">
                <!-- Populated dynamically -->
            </div>
            <div class="modal-footer">
                <button id="mark-false-positive" class="btn-secondary">Mark as False Positive</button>
                <button id="close-anomaly-context" class="btn-secondary">Close</button>
            </div>
        </div>
    </div>
</div>
```

### CSS (add to css/styles.css)

```css
/* Anomaly Detection */
.anomaly-detection {
    margin-top: 40px;
    padding-top: 40px;
    border-top: 2px solid #e0e0e0;
}

.anomaly-controls {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    flex-wrap: wrap;
}

/* Summary */
.anomaly-summary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.anomaly-summary h3 {
    margin-top: 0;
    font-size: 20px;
}

.anomaly-summary ul {
    list-style: none;
    padding: 0;
    margin: 10px 0 0 0;
}

.anomaly-summary li {
    padding: 5px 0;
    font-size: 14px;
}

/* Timeline */
.anomaly-timeline-container {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

#anomaly-timeline-canvas {
    display: block;
    margin: 0 auto;
    cursor: pointer;
    max-width: 100%;
}

/* Anomaly List */
.anomaly-list-container {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.anomaly-list {
    max-height: 600px;
    overflow-y: auto;
}

.anomaly-item {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    transition: all 0.2s;
    cursor: pointer;
}

.anomaly-item:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
}

.anomaly-item.severe {
    border-left: 5px solid #e74c3c;
    background-color: #ffebee;
}

.anomaly-item.moderate {
    border-left: 5px solid #f39c12;
    background-color: #fff8e1;
}

.anomaly-item.minor {
    border-left: 5px solid #3498db;
    background-color: #e3f2fd;
}

.anomaly-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}

.anomaly-icon {
    font-size: 24px;
}

.anomaly-severity {
    font-weight: bold;
    font-size: 14px;
}

.anomaly-datetime {
    color: #666;
    font-size: 14px;
}

.anomaly-details {
    margin-left: 34px;
    font-size: 14px;
    line-height: 1.6;
}

.anomaly-value {
    font-weight: bold;
    color: #e74c3c;
}

.anomaly-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
}

/* Context Modal */
.modal-content.large {
    max-width: 800px;
}

.anomaly-context-chart {
    width: 100%;
    height: 300px;
    margin: 20px 0;
}

.context-section {
    margin: 20px 0;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}

.context-section h4 {
    margin-top: 0;
    color: #2c3e50;
}

.context-section ul {
    margin: 10px 0 0 0;
    padding-left: 20px;
}

.context-section li {
    padding: 3px 0;
}
```

### JavaScript (add to js/analysis.js)

```javascript
/**
 * Anomaly Detection
 */

let anomalyData = null;
let anomalySensor = 'all';
let anomalySensitivity = 2.5;
let anomalyTimeRange = '6m';

function setupAnomalyDetection() {
    // Sensor selector
    const sensorSelect = document.getElementById('anomaly-sensor');
    if (sensorSelect) {
        sensorSelect.addEventListener('change', (e) => {
            anomalySensor = e.target.value;
        });
    }

    // Sensitivity selector
    const sensitivitySelect = document.getElementById('anomaly-sensitivity');
    if (sensitivitySelect) {
        sensitivitySelect.addEventListener('change', (e) => {
            anomalySensitivity = parseFloat(e.target.value);
        });
    }

    // Time range selector
    const timeRangeSelect = document.getElementById('anomaly-time-range');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', (e) => {
            anomalyTimeRange = e.target.value;
        });
    }

    // Scan button
    const scanBtn = document.getElementById('scan-anomalies');
    if (scanBtn) {
        scanBtn.addEventListener('click', () => {
            scanForAnomalies();
        });
    }

    // Export button
    const exportBtn = document.getElementById('export-anomaly-report');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportAnomalyReport);
    }

    // Clear filters
    const clearBtn = document.getElementById('clear-anomaly-filters');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAnomalyFilters);
    }

    // Modal close
    const modalClose = document.querySelector('#anomaly-context-modal .modal-close');
    const closeBtn = document.getElementById('close-anomaly-context');

    if (modalClose) modalClose.addEventListener('click', hideAnomalyContextModal);
    if (closeBtn) closeBtn.addEventListener('click', hideAnomalyContextModal);

    // Initial scan
    scanForAnomalies();
}

async function scanForAnomalies() {
    console.log(`Scanning for anomalies: sensor=${anomalySensor}, sensitivity=${anomalySensitivity}, range=${anomalyTimeRange}`);

    try {
        const data = await window.pywebview.api.detect_anomalies(
            anomalySensor,
            anomalySensitivity,
            anomalyTimeRange
        );

        anomalyData = data;
        renderAnomalySummary();
        renderAnomalyTimeline();
        renderAnomalyList();
    } catch (error) {
        console.error('Failed to detect anomalies:', error);
        alert('Failed to scan for anomalies. Please try again.');
    }
}

function renderAnomalySummary() {
    if (!anomalyData) return;

    const summary = document.getElementById('anomaly-summary');

    const severeCounted = anomalyData.anomalies.filter(a => a.severity === 'severe').length;
    const moderateCount = anomalyData.anomalies.filter(a => a.severity === 'moderate').length;
    const minorCount = anomalyData.anomalies.filter(a => a.severity === 'minor').length;

    // Count by sensor
    const bySensor = {};
    anomalyData.anomalies.forEach(a => {
        bySensor[a.sensor] = (bySensor[a.sensor] || 0) + 1;
    });

    const mostCommon = Object.entries(bySensor).sort((a, b) => b[1] - a[1])[0];

    summary.innerHTML = `
        <h3>Anomaly Summary</h3>
        <ul>
            <li>• Found ${anomalyData.total_count} anomalies in the ${getTimeRangeLabel(anomalyTimeRange).toLowerCase()}</li>
            <li>• ${severeCount} severe (>3σ), ${moderateCount} moderate (2-3σ), ${minorCount} minor (<2σ)</li>
            ${mostCommon ? `<li>• Most common: ${SENSOR_FULL_NAMES[mostCommon[0]]} (${mostCommon[1]} events)</li>` : ''}
        </ul>
    `;
}

function renderAnomalyTimeline() {
    // Simple timeline visualization
    const canvas = document.getElementById('anomaly-timeline-canvas');
    if (!canvas || !anomalyData) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw timeline
    const marginLeft = 50;
    const marginRight = 50;
    const y = canvas.height / 2;

    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(marginLeft, y);
    ctx.lineTo(canvas.width - marginRight, y);
    ctx.stroke();

    // Plot anomalies
    if (anomalyData.anomalies.length === 0) return;

    const timestamps = anomalyData.anomalies.map(a => new Date(a.timestamp).getTime());
    const minTime = Math.min(...timestamps);
    const maxTime = Math.max(...timestamps);
    const timeRange = maxTime - minTime || 1;

    anomalyData.anomalies.forEach(anomaly => {
        const timestamp = new Date(anomaly.timestamp).getTime();
        const x = marginLeft + ((timestamp - minTime) / timeRange) * (canvas.width - marginLeft - marginRight);

        // Draw point
        const color = anomaly.severity === 'severe' ? '#e74c3c' :
                     anomaly.severity === 'moderate' ? '#f39c12' : '#3498db';

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fill();

        // Border
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
    });
}

function renderAnomalyList() {
    if (!anomalyData) return;

    const list = document.getElementById('anomaly-list');
    list.innerHTML = '';

    if (anomalyData.anomalies.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: #666;">No anomalies detected with current settings.</p>';
        return;
    }

    anomalyData.anomalies.forEach(anomaly => {
        const item = createAnomalyItem(anomaly);
        list.appendChild(item);
    });
}

function createAnomalyItem(anomaly) {
    const item = document.createElement('div');
    item.className = `anomaly-item ${anomaly.severity}`;

    const icon = anomaly.severity === 'severe' ? '🚨' :
                anomaly.severity === 'moderate' ? '⚠️' : 'ℹ️';

    const date = new Date(anomaly.timestamp);
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

    const value = formatValue(anomaly.sensor, anomaly.value);
    const deviation = Math.abs(anomaly.value - anomaly.expected_value);
    const deviationStr = formatValue(anomaly.sensor, deviation);

    item.innerHTML = `
        <div class="anomaly-header">
            <span class="anomaly-icon">${icon}</span>
            <span class="anomaly-datetime">${dateStr} ${timeStr}</span>
            <span class="anomaly-severity">${anomaly.severity.toUpperCase()}</span>
        </div>
        <div class="anomaly-details">
            <strong>${SENSOR_FULL_NAMES[anomaly.sensor]}:</strong>
            <span class="anomaly-value">${value}</span>
            (${Math.abs(anomaly.z_score).toFixed(1)}σ ${anomaly.z_score > 0 ? 'above' : 'below'} mean)<br>
            Normal range: ${formatValue(anomaly.sensor, anomaly.expected_min)}-${formatValue(anomaly.sensor, anomaly.expected_max)},
            This reading: ${deviationStr} ${anomaly.z_score > 0 ? 'higher' : 'lower'}<br>
            <button class="btn-link" data-anomaly-id="${anomaly.id}">View Context</button>
        </div>
    `;

    // Add click handler for "View Context"
    const viewBtn = item.querySelector('.btn-link');
    if (viewBtn) {
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showAnomalyContext(anomaly);
        });
    }

    return item;
}

async function showAnomalyContext(anomaly) {
    const modal = document.getElementById('anomaly-context-modal');
    const title = document.getElementById('anomaly-context-title');
    const body = document.getElementById('anomaly-context-body');

    const date = new Date(anomaly.timestamp);
    const dateStr = date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

    title.textContent = `Anomaly Context - ${dateStr} ${timeStr}`;

    // Fetch surrounding data for context
    try {
        const contextData = await window.pywebview.api.get_anomaly_context(
            anomaly.sensor,
            anomaly.timestamp
        );

        body.innerHTML = `
            <div>
                <h3>${SENSOR_FULL_NAMES[anomaly.sensor]}: ${formatValue(anomaly.sensor, anomaly.value)}</h3>
                <p>Z-Score: ${anomaly.z_score > 0 ? '+' : ''}${anomaly.z_score.toFixed(1)}σ (${anomaly.severity} anomaly)</p>
            </div>

            <div class="anomaly-context-chart">
                <canvas id="anomaly-context-chart-canvas" width="700" height="250"></canvas>
            </div>

            <div class="context-section">
                <h4>Normal Behavior:</h4>
                <ul>
                    <li>Typical ${timeStr}: ${formatValue(anomaly.sensor, anomaly.expected_value)} (±${formatValue(anomaly.sensor, contextData.typical_std)})</li>
                    <li>This reading: ${formatValue(anomaly.sensor, Math.abs(anomaly.value - anomaly.expected_value))} ${anomaly.z_score > 0 ? 'above' : 'below'} typical</li>
                    <li>Previous spike of this magnitude: ${contextData.previous_similar || 'Never'}</li>
                </ul>
            </div>

            <div class="context-section">
                <h4>Surrounding Conditions:</h4>
                <ul>
                    ${contextData.other_sensors.map(s => `
                        <li>${s.name}: ${s.value} (${s.status})</li>
                    `).join('')}
                </ul>
            </div>
        `;

        // Render context chart
        renderAnomalyContextChart(contextData, anomaly);

        modal.classList.add('active');
    } catch (error) {
        console.error('Failed to load anomaly context:', error);
        alert('Failed to load context data.');
    }
}

function renderAnomalyContextChart(contextData, anomaly) {
    const canvas = document.getElementById('anomaly-context-chart-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Simple line chart showing surrounding hours
    // Similar to day detail chart but highlighting the anomaly point

    const marginLeft = 60;
    const marginTop = 30;
    const marginBottom = 50;
    const marginRight = 30;

    const plotWidth = canvas.width - marginLeft - marginRight;
    const plotHeight = canvas.height - marginTop - marginBottom;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw axes
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(marginLeft, marginTop);
    ctx.lineTo(marginLeft, canvas.height - marginBottom);
    ctx.lineTo(canvas.width - marginRight, canvas.height - marginBottom);
    ctx.stroke();

    // Plot data
    const values = contextData.surrounding_values;
    const timestamps = contextData.surrounding_timestamps;

    if (values.length === 0) return;

    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue;

    // Draw line
    ctx.strokeStyle = '#2980b9';
    ctx.lineWidth = 2;
    ctx.beginPath();

    values.forEach((value, i) => {
        const x = marginLeft + (i / (values.length - 1)) * plotWidth;
        const y = canvas.height - marginBottom - ((value - minValue) / range) * plotHeight;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }

        // Draw point
        ctx.fillStyle = '#2980b9';
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
    });

    ctx.stroke();

    // Highlight anomaly point (assuming it's in the middle)
    const anomalyIndex = Math.floor(values.length / 2);
    const anomalyX = marginLeft + (anomalyIndex / (values.length - 1)) * plotWidth;
    const anomalyY = canvas.height - marginBottom - ((values[anomalyIndex] - minValue) / range) * plotHeight;

    ctx.fillStyle = '#e74c3c';
    ctx.beginPath();
    ctx.arc(anomalyX, anomalyY, 8, 0, 2 * Math.PI);
    ctx.fill();

    // Draw star
    ctx.fillStyle = '#fff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('★', anomalyX, anomalyY);

    // Labels
    ctx.fillStyle = '#333';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    // Time labels (simplified)
    const labelIndices = [0, Math.floor(values.length / 2), values.length - 1];
    labelIndices.forEach(i => {
        const x = marginLeft + (i / (values.length - 1)) * plotWidth;
        const time = new Date(timestamps[i]).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
        ctx.fillText(time, x, canvas.height - marginBottom + 10);
    });
}

function hideAnomalyContextModal() {
    const modal = document.getElementById('anomaly-context-modal');
    modal.classList.remove('active');
}

function exportAnomalyReport() {
    if (!anomalyData) {
        alert('No anomaly data to export.');
        return;
    }

    // Generate CSV report
    let csv = 'Timestamp,Sensor,Value,Z-Score,Severity,Expected Value,Deviation\n';

    anomalyData.anomalies.forEach(a => {
        csv += `${a.timestamp},${a.sensor},${a.value},${a.z_score},${a.severity},${a.expected_value},${Math.abs(a.value - a.expected_value)}\n`;
    });

    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `anomaly-report-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
}

function clearAnomalyFilters() {
    anomalySensor = 'all';
    anomalySensitivity = 2.5;
    anomalyTimeRange = '6m';

    document.getElementById('anomaly-sensor').value = 'all';
    document.getElementById('anomaly-sensitivity').value = '2.5';
    document.getElementById('anomaly-time-range').value = '6m';

    scanForAnomalies();
}

// Call from initializeAnalysisTab():
// setupAnomalyDetection();
```

---

## Backend Integration

### Add to analysis_engine.py

```python
def detect_anomalies(self, sensor, threshold=2.5, time_range=None):
    """
    Detect anomalies using z-score method

    Args:
        sensor: Sensor name or 'all' for all sensors
        threshold: Z-score threshold (default 2.5)
        time_range: Time range to analyze

    Returns:
        {
            "anomalies": [
                {
                    "id": unique_id,
                    "timestamp": iso_timestamp,
                    "sensor": sensor_name,
                    "value": actual_value,
                    "expected_value": mean,
                    "expected_min": mean - 2*std,
                    "expected_max": mean + 2*std,
                    "z_score": z_score,
                    "severity": "severe|moderate|minor"
                },
                ...
            ],
            "total_count": N
        }
    """
    sensors = [sensor] if sensor != 'all' else [
        'temperature_sht', 'humidity', 'pressure', 'light', 'sound_level'
    ]

    df = self.load_data(time_range, sensors=sensors)

    if df.empty:
        return {"anomalies": [], "total_count": 0}

    anomalies = []

    for sensor_name in sensors:
        series = df[sensor_name].dropna()

        if len(series) < 30:  # Need enough data for meaningful stats
            continue

        mean = series.mean()
        std = series.std()

        # Calculate z-scores
        z_scores = (series - mean) / std

        # Find outliers
        outlier_mask = z_scores.abs() >= threshold

        for idx in series[outlier_mask].index:
            value = series[idx]
            z_score = z_scores[idx]

            # Classify severity
            abs_z = abs(z_score)
            if abs_z >= 3.0:
                severity = 'severe'
            elif abs_z >= 2.5:
                severity = 'moderate'
            else:
                severity = 'minor'

            anomalies.append({
                "id": f"{sensor_name}_{idx}",
                "timestamp": df.loc[idx, 'gw_timestamp'].isoformat(),
                "sensor": sensor_name,
                "value": float(value),
                "expected_value": float(mean),
                "expected_min": float(mean - 2 * std),
                "expected_max": float(mean + 2 * std),
                "z_score": float(z_score),
                "severity": severity
            })

    # Sort by timestamp (newest first)
    anomalies.sort(key=lambda x: x['timestamp'], reverse=True)

    return {
        "anomalies": anomalies,
        "total_count": len(anomalies)
    }

def get_anomaly_context(self, sensor, timestamp_str, hours_before=3, hours_after=3):
    """
    Get surrounding data for an anomaly

    Returns:
        {
            "surrounding_values": [...],
            "surrounding_timestamps": [...],
            "typical_std": std_dev,
            "previous_similar": "2024-05-15" or None,
            "other_sensors": [
                {"name": "Humidity", "value": "45.2%", "status": "normal"},
                ...
            ]
        }
    """
    anomaly_time = datetime.fromisoformat(timestamp_str)
    start_time = anomaly_time - timedelta(hours=hours_before)
    end_time = anomaly_time + timedelta(hours=hours_after)

    time_range = {
        "start": start_time.isoformat(),
        "end": end_time.isoformat()
    }

    all_sensors = ['temperature_sht', 'humidity', 'pressure', 'light', 'sound_level']
    df = self.load_data(time_range, sensors=all_sensors)

    if df.empty:
        return {"error": "No context data available"}

    # Get surrounding values for the sensor
    sensor_series = df[sensor].dropna()

    surrounding_values = sensor_series.tolist()
    surrounding_timestamps = df.loc[sensor_series.index, 'gw_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()

    # Get typical std dev for this sensor (from full dataset)
    full_df = self.load_data(None, sensors=[sensor])
    typical_std = float(full_df[sensor].std()) if not full_df.empty else 0.0

    # Check other sensors at anomaly time
    anomaly_row = df.iloc[(df['gw_timestamp'] - anomaly_time).abs().argsort()[:1]]

    other_sensors = []
    for other_sensor in all_sensors:
        if other_sensor == sensor:
            continue

        if other_sensor in anomaly_row.columns:
            value = anomaly_row[other_sensor].iloc[0]
            # Simple normality check (within 2σ)
            sensor_mean = full_df[other_sensor].mean()
            sensor_std = full_df[other_sensor].std()
            z_score = abs((value - sensor_mean) / sensor_std) if sensor_std > 0 else 0

            status = 'normal' if z_score < 2 else 'unusual'

            other_sensors.append({
                "name": SENSOR_FULL_NAMES.get(other_sensor, other_sensor),
                "value": f"{value:.1f}",
                "status": status
            })

    return {
        "surrounding_values": [float(v) for v in surrounding_values],
        "surrounding_timestamps": surrounding_timestamps,
        "typical_std": typical_std,
        "previous_similar": None,  # TODO: Find previous similar anomaly
        "other_sensors": other_sensors
    }
```

### Add to gateway_webview.py Api class

```python
def detect_anomalies(self, sensor, threshold, time_range):
    """Detect anomalies in sensor data"""
    return analysis_engine.detect_anomalies(sensor, float(threshold), time_range)

def get_anomaly_context(self, sensor, timestamp_str):
    """Get context for an anomaly"""
    return analysis_engine.get_anomaly_context(sensor, timestamp_str)
```

---

## Implementation Steps

1. **Add HTML structure** to tab_analysis.html
2. **Add CSS styles** for anomaly items and timeline
3. **Implement anomaly scanning** logic in JavaScript
4. **Implement backend detection** using z-score method
5. **Create context modal** with surrounding data visualization
6. **Add export functionality** for anomaly reports
7. **Test with real data** - verify meaningful anomalies detected

---

## Success Criteria

- [ ] Anomaly detection identifies genuine outliers
- [ ] Timeline visualization shows events clearly
- [ ] Context modal provides useful surrounding information
- [ ] Severity classification is accurate
- [ ] Export generates usable CSV report
- [ ] Performance handles large datasets
- [ ] UI is intuitive and informative

---

## Notes

Anomaly detection is powerful for surfacing interesting events that would otherwise be lost in months of data. Consider adding user ability to mark false positives and create custom rules in future iterations.
