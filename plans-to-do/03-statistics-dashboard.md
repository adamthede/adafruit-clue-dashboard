# Implementation Plan: Statistics Dashboard

**Priority:** HIGH
**Phase:** 1
**Estimated Effort:** 4-5 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture
**Blocks:** None (standalone feature)

---

## Overview

Create an interactive statistics dashboard in the Analysis tab that displays comprehensive statistical summaries for each sensor. This provides immediate insights into data distributions, trends, and key metrics without requiring users to export data to external tools.

---

## Goals & Objectives

1. **At-a-Glance Insights**: Display min, max, mean, median, std dev for each sensor
2. **Time Range Awareness**: Statistics update based on selected time range
3. **Visual Clarity**: Use cards/panels to organize information
4. **Comparative View**: Show all sensors side-by-side for easy comparison
5. **Interactivity**: Click on a stat card to see detailed breakdown

---

## Architecture

### Visual Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Analysis Tab > Statistics Dashboard                        │
├──────────────────────────────────────────────────────────────┤
│  Time Range: [Last 24 Hours ▼]  [Refresh Stats]            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ Temperature   │ │ Humidity      │ │ Pressure      │    │
│  │ 72.3°F        │ │ 45.2%         │ │ 1013.2 hPa    │    │
│  │ ───────────   │ │ ───────────   │ │ ───────────   │    │
│  │ Min: 68.5°F   │ │ Min: 38.1%    │ │ Min: 1008 hPa │    │
│  │ Max: 76.2°F   │ │ Max: 52.3%    │ │ Max: 1018 hPa │    │
│  │ σ: 1.8°F      │ │ σ: 3.2%       │ │ σ: 2.1 hPa    │    │
│  │ [Details]     │ │ [Details]     │ │ [Details]     │    │
│  └───────────────┘ └───────────────┘ └───────────────┘    │
│                                                              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ Light         │ │ Sound Level   │ │ Color         │    │
│  │ 1847          │ │ 142           │ │ #FF5C21       │    │
│  │ ───────────   │ │ ───────────   │ │ ───────────   │    │
│  │ Min: 12       │ │ Min: 85       │ │ Most Common   │    │
│  │ Max: 3891     │ │ Max: 892      │ │ ▉ #FFD4A3     │    │
│  │ σ: 456        │ │ σ: 67         │ │ ▉ #2A3B4C     │    │
│  │ [Details]     │ │ [Details]     │ │ [Details]     │    │
│  └───────────────┘ └───────────────┘ └───────────────┘    │
│                                                              │
│  Summary Insights:                                          │
│  • Temperature varied by 7.7°F over the last 24 hours       │
│  • Humidity is most stable (lowest variation)               │
│  • Light peaked at 2:45 PM (3891)                          │
└──────────────────────────────────────────────────────────────┘
```

### Detail Modal (Click "Details" on any card)

```
┌─────────────────────────────────────────────────────┐
│  Temperature Statistics - Last 24 Hours        [×]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Current: 72.3°F                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                     │
│  Distribution:                                      │
│  • Minimum: 68.5°F (at 6:15 AM)                   │
│  • 25th Percentile: 70.2°F                        │
│  • Median: 72.1°F                                 │
│  • 75th Percentile: 73.8°F                        │
│  • 95th Percentile: 75.5°F                        │
│  • Maximum: 76.2°F (at 3:47 PM)                   │
│                                                     │
│  Variability:                                       │
│  • Mean: 72.3°F                                    │
│  • Std Dev: 1.8°F                                  │
│  • Coefficient of Variation: 2.5%                  │
│  • Range: 7.7°F                                    │
│                                                     │
│  Data Quality:                                      │
│  • Total Readings: 2,880                           │
│  • Missing Data: 0 (0%)                            │
│  • Time Span: 24.0 hours                          │
│                                                     │
│  [Export Stats] [View Histogram] [Close]           │
└─────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### HTML Structure (tabs/tab_analysis.html)

```html
<div id="analysis-container" class="statistics-dashboard">
    <!-- Time Range Selector -->
    <div class="stats-controls">
        <label for="stats-time-range">Time Range:</label>
        <select id="stats-time-range">
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h" selected>Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="all">All Time</option>
        </select>
        <button id="refresh-stats" class="btn-primary">Refresh Stats</button>
    </div>

    <!-- Stats Cards Grid -->
    <div class="stats-grid">
        <!-- Temperature Card -->
        <div class="stat-card" data-sensor="temperature_sht">
            <div class="stat-card-header">
                <span class="stat-icon">🌡️</span>
                <h3>Temperature</h3>
            </div>
            <div class="stat-card-current">
                <span id="temp-current">--</span>
            </div>
            <div class="stat-card-details">
                <div class="stat-row">
                    <span class="stat-label">Min:</span>
                    <span id="temp-min">--</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Max:</span>
                    <span id="temp-max">--</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">σ:</span>
                    <span id="temp-std">--</span>
                </div>
            </div>
            <button class="stat-details-btn" data-sensor="temperature_sht">Details</button>
        </div>

        <!-- Humidity Card -->
        <div class="stat-card" data-sensor="humidity">
            <!-- Similar structure -->
        </div>

        <!-- Pressure Card -->
        <div class="stat-card" data-sensor="pressure">
            <!-- Similar structure -->
        </div>

        <!-- Light Card -->
        <div class="stat-card" data-sensor="light">
            <!-- Similar structure -->
        </div>

        <!-- Sound Card -->
        <div class="stat-card" data-sensor="sound_level">
            <!-- Similar structure -->
        </div>

        <!-- Color Card (special handling) -->
        <div class="stat-card" data-sensor="color_hex">
            <div class="stat-card-header">
                <span class="stat-icon">🎨</span>
                <h3>Color</h3>
            </div>
            <div class="color-swatch" id="color-current"></div>
            <div class="color-palette" id="color-common"></div>
            <button class="stat-details-btn" data-sensor="color_hex">Details</button>
        </div>
    </div>

    <!-- Summary Insights -->
    <div class="insights-panel">
        <h3>Summary Insights</h3>
        <ul id="insights-list">
            <!-- Auto-generated insights -->
        </ul>
    </div>

    <!-- Details Modal (hidden by default) -->
    <div id="stats-modal" class="modal hidden">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">Sensor Statistics</h2>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body" id="modal-body">
                <!-- Populated dynamically -->
            </div>
            <div class="modal-footer">
                <button id="export-sensor-stats" class="btn-primary">Export Stats</button>
                <button id="modal-close-btn" class="btn-secondary">Close</button>
            </div>
        </div>
    </div>
</div>
```

### CSS (add to css/styles.css)

```css
/* Statistics Dashboard */
.statistics-dashboard {
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
}

.stats-controls {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 30px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}

.stats-controls select {
    padding: 8px 12px;
    font-size: 14px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Stats Cards Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.stat-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 15px;
}

.stat-icon {
    font-size: 24px;
}

.stat-card h3 {
    margin: 0;
    font-size: 18px;
    color: #333;
}

.stat-card-current {
    font-size: 32px;
    font-weight: bold;
    color: #2980b9;
    text-align: center;
    margin-bottom: 15px;
}

.stat-card-details {
    border-top: 1px solid #eee;
    padding-top: 10px;
}

.stat-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    font-size: 14px;
}

.stat-label {
    color: #666;
}

.stat-details-btn {
    width: 100%;
    margin-top: 10px;
    padding: 8px;
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.stat-details-btn:hover {
    background-color: #2980b9;
}

/* Color Card Special Styles */
.color-swatch {
    width: 100%;
    height: 80px;
    border-radius: 8px;
    margin-bottom: 10px;
    border: 1px solid #ddd;
}

.color-palette {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
}

.color-palette-item {
    width: 40px;
    height: 40px;
    border-radius: 5px;
    border: 1px solid #ddd;
}

/* Insights Panel */
.insights-panel {
    background-color: #fffbea;
    border: 1px solid #f9e79f;
    border-radius: 8px;
    padding: 20px;
}

.insights-panel h3 {
    margin-top: 0;
    color: #f39c12;
}

#insights-list {
    list-style: none;
    padding: 0;
}

#insights-list li {
    padding: 8px 0;
    border-bottom: 1px solid #f9e79f;
}

#insights-list li:last-child {
    border-bottom: none;
}

/* Modal */
.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 1000;
}

.modal.active {
    display: flex;
    justify-content: center;
    align-items: center;
}

.modal-content {
    background: white;
    border-radius: 10px;
    width: 90%;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid #eee;
}

.modal-close {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #999;
}

.modal-body {
    padding: 20px;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 20px;
    border-top: 1px solid #eee;
}
```

### JavaScript (js/analysis.js)

```javascript
/**
 * Statistics Dashboard for Analysis Tab
 */

let statsTimeRange = '24h';
let currentStats = {};

// Initialize when tab is first activated
function initializeAnalysisTab() {
    console.log('Initializing Analysis Tab - Statistics Dashboard');

    // Setup event listeners
    setupStatsEventListeners();

    // Load initial statistics
    loadStatistics();
}

function setupStatsEventListeners() {
    // Time range selector
    const timeRangeSelect = document.getElementById('stats-time-range');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', (e) => {
            statsTimeRange = e.target.value;
            loadStatistics();
        });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refresh-stats');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadStatistics();
        });
    }

    // Details buttons
    const detailButtons = document.querySelectorAll('.stat-details-btn');
    detailButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const sensor = e.target.dataset.sensor;
            showStatsModal(sensor);
        });
    });

    // Modal close
    const modalClose = document.querySelector('.modal-close');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    if (modalClose) {
        modalClose.addEventListener('click', hideStatsModal);
    }
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', hideStatsModal);
    }

    // Export sensor stats
    const exportBtn = document.getElementById('export-sensor-stats');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportCurrentSensorStats);
    }
}

async function loadStatistics() {
    console.log(`Loading statistics for time range: ${statsTimeRange}`);

    const sensors = ['temperature_sht', 'humidity', 'pressure', 'light', 'sound_level'];

    // Load stats for each sensor
    for (const sensor of sensors) {
        try {
            const stats = await window.pywebview.api.get_statistics(sensor, statsTimeRange);
            currentStats[sensor] = stats;
            updateStatCard(sensor, stats);
        } catch (error) {
            console.error(`Failed to load stats for ${sensor}:`, error);
        }
    }

    // Load color stats separately (special handling)
    await loadColorStats();

    // Generate insights
    generateInsights();
}

function updateStatCard(sensor, stats) {
    const sensorId = sensor.replace('_', '-');

    // Update current value (mean)
    const currentEl = document.getElementById(`${sensorId}-current`);
    if (currentEl && stats.mean !== undefined) {
        currentEl.textContent = formatValue(sensor, stats.mean);
    }

    // Update min
    const minEl = document.getElementById(`${sensorId}-min`);
    if (minEl && stats.min !== undefined) {
        minEl.textContent = formatValue(sensor, stats.min);
    }

    // Update max
    const maxEl = document.getElementById(`${sensorId}-max`);
    if (maxEl && stats.max !== undefined) {
        maxEl.textContent = formatValue(sensor, stats.max);
    }

    // Update std dev
    const stdEl = document.getElementById(`${sensorId}-std`);
    if (stdEl && stats.std_dev !== undefined) {
        stdEl.textContent = formatValue(sensor, stats.std_dev);
    }
}

function formatValue(sensor, value) {
    if (value === null || value === undefined) return '--';

    switch (sensor) {
        case 'temperature_sht':
            return `${value.toFixed(1)}°F`;
        case 'humidity':
            return `${value.toFixed(1)}%`;
        case 'pressure':
            return `${value.toFixed(1)} hPa`;
        case 'light':
        case 'sound_level':
            return Math.round(value).toString();
        default:
            return value.toFixed(2);
    }
}

async function loadColorStats() {
    // Special handling for color sensor
    // Get most common colors from time range
    try {
        const colorData = await window.pywebview.api.get_color_statistics(statsTimeRange);

        // Update current color swatch
        const currentSwatch = document.getElementById('color-current');
        if (currentSwatch && colorData.current) {
            currentSwatch.style.backgroundColor = colorData.current;
        }

        // Update common colors palette
        const palette = document.getElementById('color-common');
        if (palette && colorData.most_common) {
            palette.innerHTML = '';
            colorData.most_common.slice(0, 5).forEach(color => {
                const item = document.createElement('div');
                item.className = 'color-palette-item';
                item.style.backgroundColor = color;
                item.title = color;
                palette.appendChild(item);
            });
        }

        currentStats['color_hex'] = colorData;
    } catch (error) {
        console.error('Failed to load color stats:', error);
    }
}

function showStatsModal(sensor) {
    const modal = document.getElementById('stats-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');

    if (!currentStats[sensor]) {
        alert('No statistics available for this sensor');
        return;
    }

    const stats = currentStats[sensor];

    // Set title
    title.textContent = `${getSensorDisplayName(sensor)} Statistics - ${getTimeRangeLabel(statsTimeRange)}`;

    // Build modal content
    body.innerHTML = `
        <div class="modal-stats-detail">
            <h3>Current: ${formatValue(sensor, stats.mean)}</h3>

            <h4>Distribution:</h4>
            <ul>
                <li>Minimum: ${formatValue(sensor, stats.min)} ${stats.min_timestamp ? `(at ${formatTimestamp(stats.min_timestamp)})` : ''}</li>
                <li>25th Percentile: ${formatValue(sensor, stats.percentile_25)}</li>
                <li>Median: ${formatValue(sensor, stats.median)}</li>
                <li>75th Percentile: ${formatValue(sensor, stats.percentile_75)}</li>
                <li>95th Percentile: ${formatValue(sensor, stats.percentile_95)}</li>
                <li>Maximum: ${formatValue(sensor, stats.max)} ${stats.max_timestamp ? `(at ${formatTimestamp(stats.max_timestamp)})` : ''}</li>
            </ul>

            <h4>Variability:</h4>
            <ul>
                <li>Mean: ${formatValue(sensor, stats.mean)}</li>
                <li>Std Dev: ${formatValue(sensor, stats.std_dev)}</li>
                <li>Range: ${formatValue(sensor, stats.max - stats.min)}</li>
            </ul>

            <h4>Data Quality:</h4>
            <ul>
                <li>Total Readings: ${stats.count ? stats.count.toLocaleString() : 'N/A'}</li>
                <li>Missing Data: ${stats.missing_count || 0} (${stats.missing_percent ? stats.missing_percent.toFixed(1) : 0}%)</li>
                <li>Time Span: ${stats.time_span_hours ? stats.time_span_hours.toFixed(1) : 'N/A'} hours</li>
            </ul>
        </div>
    `;

    // Show modal
    modal.classList.add('active');
}

function hideStatsModal() {
    const modal = document.getElementById('stats-modal');
    modal.classList.remove('active');
}

function getSensorDisplayName(sensor) {
    const names = {
        'temperature_sht': 'Temperature',
        'humidity': 'Humidity',
        'pressure': 'Pressure',
        'light': 'Light',
        'sound_level': 'Sound Level',
        'color_hex': 'Color'
    };
    return names[sensor] || sensor;
}

function getTimeRangeLabel(range) {
    const labels = {
        '1h': 'Last Hour',
        '6h': 'Last 6 Hours',
        '24h': 'Last 24 Hours',
        '7d': 'Last 7 Days',
        '30d': 'Last 30 Days',
        'all': 'All Time'
    };
    return labels[range] || range;
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function generateInsights() {
    const insightsList = document.getElementById('insights-list');
    if (!insightsList) return;

    insightsList.innerHTML = '';

    const insights = [];

    // Temperature insights
    if (currentStats.temperature_sht) {
        const range = currentStats.temperature_sht.max - currentStats.temperature_sht.min;
        insights.push(`Temperature varied by ${range.toFixed(1)}°F over the ${getTimeRangeLabel(statsTimeRange).toLowerCase()}`);
    }

    // Find most stable sensor (lowest coefficient of variation)
    let mostStable = null;
    let lowestCV = Infinity;

    ['temperature_sht', 'humidity', 'pressure'].forEach(sensor => {
        if (currentStats[sensor] && currentStats[sensor].mean > 0) {
            const cv = (currentStats[sensor].std_dev / currentStats[sensor].mean) * 100;
            if (cv < lowestCV) {
                lowestCV = cv;
                mostStable = sensor;
            }
        }
    });

    if (mostStable) {
        insights.push(`${getSensorDisplayName(mostStable)} is most stable (lowest variation)`);
    }

    // Light peak
    if (currentStats.light && currentStats.light.max_timestamp) {
        const time = new Date(currentStats.light.max_timestamp).toLocaleTimeString();
        insights.push(`Light peaked at ${time} (${currentStats.light.max})`);
    }

    // Render insights
    insights.forEach(insight => {
        const li = document.createElement('li');
        li.textContent = `• ${insight}`;
        insightsList.appendChild(li);
    });
}

async function exportCurrentSensorStats() {
    // Export the currently viewed sensor's detailed stats
    // Placeholder - implement based on needs
    alert('Export sensor stats - to be implemented');
}

// Export initialization function for tab manager
window.initializeAnalysisTab = initializeAnalysisTab;
```

---

## Backend Integration

### Add to analysis_engine.py

```python
def compute_statistics(self, sensor, time_range=None):
    """
    Compute comprehensive statistics for a sensor

    Returns:
        dict with min, max, mean, median, std_dev, percentiles,
        count, missing_count, timestamps for min/max
    """
    df = self.load_data(time_range, sensors=[sensor])

    if df.empty:
        return {"error": "No data available"}

    series = df[sensor]
    series_clean = series.dropna()

    # Find timestamps for min/max
    min_idx = series.idxmin()
    max_idx = series.idxmax()

    stats = {
        "sensor": sensor,
        "time_range": time_range,
        "count": len(series),
        "missing_count": series.isna().sum(),
        "missing_percent": (series.isna().sum() / len(series)) * 100,
        "min": float(series_clean.min()),
        "max": float(series_clean.max()),
        "mean": float(series_clean.mean()),
        "median": float(series_clean.median()),
        "std_dev": float(series_clean.std()),
        "percentile_25": float(series_clean.quantile(0.25)),
        "percentile_75": float(series_clean.quantile(0.75)),
        "percentile_95": float(series_clean.quantile(0.95)),
        "min_timestamp": df.loc[min_idx, 'gw_timestamp'].isoformat() if min_idx in df.index else None,
        "max_timestamp": df.loc[max_idx, 'gw_timestamp'].isoformat() if max_idx in df.index else None,
        "time_span_hours": (df['gw_timestamp'].max() - df['gw_timestamp'].min()).total_seconds() / 3600
    }

    return stats

def get_color_statistics(self, time_range=None):
    """Special handling for color sensor"""
    df = self.load_data(time_range, sensors=['color_hex'])

    if df.empty:
        return {"error": "No data available"}

    color_counts = df['color_hex'].value_counts()

    return {
        "current": df['color_hex'].iloc[-1],  # Most recent
        "most_common": color_counts.head(10).index.tolist(),
        "unique_count": len(color_counts)
    }
```

### Add to gateway_webview.py Api class

```python
def get_statistics(self, sensor, time_range=None):
    """Get statistical summary for a sensor"""
    return analysis_engine.compute_statistics(sensor, time_range)

def get_color_statistics(self, time_range=None):
    """Get color-specific statistics"""
    return analysis_engine.get_color_statistics(time_range)
```

---

## Implementation Steps

1. **Create HTML structure** in tabs/tab_analysis.html
2. **Add CSS styles** to css/styles.css
3. **Implement JavaScript** in js/analysis.js
4. **Add backend methods** to analysis_engine.py
5. **Expose API endpoints** in gateway_webview.py
6. **Test with real data** - verify accuracy
7. **Polish UI** - adjust spacing, colors, responsiveness

---

## Success Criteria

- [ ] Statistics cards display correctly for all sensors
- [ ] Time range selector updates statistics
- [ ] Details modal shows comprehensive breakdown
- [ ] Insights auto-generate based on data
- [ ] Handles missing/empty data gracefully
- [ ] Statistics match manual calculations
- [ ] UI is responsive and visually appealing

---

## Notes

This dashboard provides the foundation for data-driven insights. Future enhancements could include:
- Histogram visualization in details modal
- Comparison to previous time periods
- Trend indicators (↑ ↓)
- Export stats as JSON/CSV
