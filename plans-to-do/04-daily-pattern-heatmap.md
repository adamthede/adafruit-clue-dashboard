# Implementation Plan: Daily Pattern Heatmap

**Priority:** HIGH
**Phase:** 2
**Estimated Effort:** 6-8 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture
**Blocks:** None

---

## Overview

Create an interactive heatmap visualization showing how sensor values vary across hours of the day and days of the week. This reveals daily routines, weekly patterns, and environmental cycles that are invisible in time-series charts.

---

## Goals & Objectives

1. **Pattern Discovery**: Visualize "when" things typically happen
2. **Week-at-a-Glance**: See full weekly pattern in single view
3. **Multi-Sensor Support**: Toggle between temperature, humidity, light, sound, pressure
4. **Interactive**: Hover to see exact values, click cells for details
5. **Temporal Flexibility**: Compare patterns across different time periods (last 4 weeks, last 3 months, all time)

---

## Architecture

### Visual Design

```
┌────────────────────────────────────────────────────────────────┐
│  Patterns Tab > Daily Heatmap                                 │
├────────────────────────────────────────────────────────────────┤
│  Sensor: [Temperature ▼]  Period: [Last 4 Weeks ▼]  [Refresh]│
├────────────────────────────────────────────────────────────────┤
│                                                                │
│        Hour of Day                                            │
│        0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15...      │
│    ┌────────────────────────────────────────────────────────┐ │
│ Mon│▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│ Tue│▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│ Wed│▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│ Thu│▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│ Fri│▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│ Sat│▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│ Sun│▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ │
│    └────────────────────────────────────────────────────────┘ │
│                                                                │
│    Legend: ░░░ Cool (68°F) ▓▓▓ Medium (72°F) ███ Warm (76°F) │
│                                                                │
│    Hover Info: Mon 14:00 - 75.3°F (avg over 4 weeks)         │
│                                                                │
│    Insights:                                                   │
│    • Coldest: Mon-Fri 6:00-8:00 AM (avg 68.2°F)              │
│    • Warmest: Mon-Fri 2:00-4:00 PM (avg 75.8°F)              │
│    • Weekend mornings are 2-3°F warmer (sleep in pattern?)    │
└────────────────────────────────────────────────────────────────┘
```

### Heatmap Specifications

- **X-Axis**: 24 hours (0-23)
- **Y-Axis**: 7 days (Mon-Sun)
- **Cell Color**: Gradient based on sensor value
- **Cell Size**: ~30-40px square (responsive)
- **Color Schemes**:
  - Temperature: Blue (cool) → Yellow → Red (hot)
  - Humidity: Brown (dry) → Blue (humid)
  - Pressure: Purple (low) → Green (high)
  - Light: Black (dark) → Yellow (bright)
  - Sound: Gray (quiet) → Orange (loud)

---

## Technical Specifications

### HTML Structure (tabs/tab_patterns.html)

```html
<div id="patterns-container" class="patterns-dashboard">
    <!-- Controls -->
    <div class="heatmap-controls">
        <label for="heatmap-sensor">Sensor:</label>
        <select id="heatmap-sensor">
            <option value="temperature_sht">Temperature</option>
            <option value="humidity">Humidity</option>
            <option value="pressure">Pressure</option>
            <option value="light">Light</option>
            <option value="sound_level">Sound Level</option>
        </select>

        <label for="heatmap-period">Period:</label>
        <select id="heatmap-period">
            <option value="4w" selected>Last 4 Weeks</option>
            <option value="8w">Last 8 Weeks</option>
            <option value="3m">Last 3 Months</option>
            <option value="6m">Last 6 Months</option>
            <option value="all">All Time</option>
        </select>

        <button id="refresh-heatmap" class="btn-primary">Refresh</button>
    </div>

    <!-- Heatmap Canvas -->
    <div class="heatmap-wrapper">
        <h3 id="heatmap-title">Temperature - Average by Hour & Day</h3>
        <canvas id="heatmap-canvas" width="1000" height="400"></canvas>

        <!-- Hover tooltip -->
        <div id="heatmap-tooltip" class="heatmap-tooltip hidden">
            <div id="tooltip-content"></div>
        </div>
    </div>

    <!-- Legend -->
    <div class="heatmap-legend">
        <span class="legend-label">Low</span>
        <div id="heatmap-legend-gradient" class="legend-gradient"></div>
        <span class="legend-label">High</span>
        <div id="legend-values"></div>
    </div>

    <!-- Insights -->
    <div class="heatmap-insights">
        <h4>Pattern Insights</h4>
        <ul id="heatmap-insights-list"></ul>
    </div>
</div>
```

### CSS (add to css/styles.css)

```css
/* Patterns Dashboard */
.patterns-dashboard {
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

.heatmap-controls {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}

.heatmap-wrapper {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    position: relative;
}

#heatmap-title {
    text-align: center;
    margin-bottom: 20px;
    color: #333;
}

#heatmap-canvas {
    display: block;
    margin: 0 auto;
    cursor: crosshair;
    max-width: 100%;
    height: auto;
}

/* Tooltip */
.heatmap-tooltip {
    position: absolute;
    background-color: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 10px;
    border-radius: 5px;
    font-size: 12px;
    pointer-events: none;
    z-index: 1000;
    white-space: nowrap;
}

.heatmap-tooltip.hidden {
    display: none;
}

/* Legend */
.heatmap-legend {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-bottom: 20px;
}

.legend-gradient {
    width: 300px;
    height: 20px;
    border-radius: 4px;
    border: 1px solid #ddd;
}

.legend-label {
    font-weight: bold;
    font-size: 14px;
    color: #666;
}

#legend-values {
    margin-top: 5px;
    text-align: center;
    font-size: 12px;
    color: #999;
}

/* Insights */
.heatmap-insights {
    background-color: #f0f8ff;
    border: 1px solid #b0d4f1;
    border-radius: 8px;
    padding: 20px;
}

.heatmap-insights h4 {
    margin-top: 0;
    color: #2980b9;
}

#heatmap-insights-list {
    list-style: none;
    padding: 0;
}

#heatmap-insights-list li {
    padding: 5px 0;
    border-bottom: 1px solid #d4e9f7;
}

#heatmap-insights-list li:last-child {
    border-bottom: none;
}
```

### JavaScript (js/patterns.js)

```javascript
/**
 * Daily Pattern Heatmap Visualization
 */

let heatmapData = null;
let heatmapSensor = 'temperature_sht';
let heatmapPeriod = '4w';
let heatmapCanvas = null;
let heatmapCtx = null;

// Color schemes for different sensors
const colorSchemes = {
    temperature_sht: {
        name: 'Temperature',
        gradient: ['#0066cc', '#00ccff', '#ffff00', '#ff6600', '#cc0000'],
        unit: '°F'
    },
    humidity: {
        name: 'Humidity',
        gradient: ['#8B4513', '#D2691E', '#87CEEB', '#4682B4', '#000080'],
        unit: '%'
    },
    pressure: {
        name: 'Pressure',
        gradient: ['#9b59b6', '#3498db', '#2ecc71', '#f39c12', '#e74c3c'],
        unit: ' hPa'
    },
    light: {
        name: 'Light',
        gradient: ['#000000', '#333333', '#666666', '#ffcc00', '#ffff00'],
        unit: ''
    },
    sound_level: {
        name: 'Sound Level',
        gradient: ['#d3d3d3', '#a9a9a9', '#808080', '#ff8c00', '#ff4500'],
        unit: ''
    }
};

function initializePatternsTab() {
    console.log('Initializing Patterns Tab - Daily Heatmap');

    heatmapCanvas = document.getElementById('heatmap-canvas');
    heatmapCtx = heatmapCanvas.getContext('2d');

    setupHeatmapEventListeners();
    loadHeatmapData();
}

function setupHeatmapEventListeners() {
    // Sensor selector
    const sensorSelect = document.getElementById('heatmap-sensor');
    if (sensorSelect) {
        sensorSelect.addEventListener('change', (e) => {
            heatmapSensor = e.target.value;
            loadHeatmapData();
        });
    }

    // Period selector
    const periodSelect = document.getElementById('heatmap-period');
    if (periodSelect) {
        periodSelect.addEventListener('change', (e) => {
            heatmapPeriod = e.target.value;
            loadHeatmapData();
        });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refresh-heatmap');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadHeatmapData();
        });
    }

    // Canvas hover for tooltip
    if (heatmapCanvas) {
        heatmapCanvas.addEventListener('mousemove', handleHeatmapHover);
        heatmapCanvas.addEventListener('mouseleave', hideHeatmapTooltip);
    }
}

async function loadHeatmapData() {
    console.log(`Loading heatmap data: ${heatmapSensor}, ${heatmapPeriod}`);

    try {
        // Call backend to get hourly averages by day of week
        const data = await window.pywebview.api.get_weekly_pattern(
            heatmapSensor,
            heatmapPeriod
        );

        heatmapData = data;
        renderHeatmap();
        generateHeatmapInsights();
    } catch (error) {
        console.error('Failed to load heatmap data:', error);
        alert('Failed to load heatmap data. Please try again.');
    }
}

function renderHeatmap() {
    if (!heatmapData || !heatmapCtx) return;

    const canvas = heatmapCanvas;
    const ctx = heatmapCtx;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dimensions
    const marginLeft = 60;
    const marginTop = 40;
    const marginRight = 20;
    const marginBottom = 60;

    const plotWidth = canvas.width - marginLeft - marginRight;
    const plotHeight = canvas.height - marginTop - marginBottom;

    const cellWidth = plotWidth / 24; // 24 hours
    const cellHeight = plotHeight / 7; // 7 days

    // Get min/max for color scaling
    const values = heatmapData.values.flat();
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);

    // Update legend
    updateHeatmapLegend(minValue, maxValue);

    // Draw cells
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
            const value = heatmapData.values[day][hour];

            if (value !== null) {
                const x = marginLeft + hour * cellWidth;
                const y = marginTop + day * cellHeight;

                // Get color for value
                const color = getColorForValue(value, minValue, maxValue, heatmapSensor);

                ctx.fillStyle = color;
                ctx.fillRect(x, y, cellWidth - 1, cellHeight - 1);
            }
        }
    }

    // Draw labels
    ctx.fillStyle = '#333';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    // Hour labels (X-axis)
    for (let hour = 0; hour < 24; hour += 2) {
        const x = marginLeft + hour * cellWidth + cellWidth / 2;
        const y = marginTop - 10;
        ctx.fillText(hour.toString(), x, y);
    }

    // Day labels (Y-axis)
    ctx.textAlign = 'right';
    for (let day = 0; day < 7; day++) {
        const x = marginLeft - 10;
        const y = marginTop + day * cellHeight + cellHeight / 2 + 5;
        ctx.fillText(days[day], x, y);
    }

    // Title
    const scheme = colorSchemes[heatmapSensor];
    document.getElementById('heatmap-title').textContent =
        `${scheme.name} - Average by Hour & Day (${getPeriodLabel(heatmapPeriod)})`;
}

function getColorForValue(value, min, max, sensor) {
    // Normalize value to 0-1
    const normalized = (value - min) / (max - min);

    // Get gradient colors for sensor
    const gradient = colorSchemes[sensor].gradient;

    // Map to gradient
    const index = normalized * (gradient.length - 1);
    const lowerIndex = Math.floor(index);
    const upperIndex = Math.ceil(index);
    const fraction = index - lowerIndex;

    if (lowerIndex === upperIndex) {
        return gradient[lowerIndex];
    }

    // Interpolate between two colors
    return interpolateColor(gradient[lowerIndex], gradient[upperIndex], fraction);
}

function interpolateColor(color1, color2, fraction) {
    // Convert hex to RGB
    const c1 = hexToRgb(color1);
    const c2 = hexToRgb(color2);

    // Interpolate
    const r = Math.round(c1.r + (c2.r - c1.r) * fraction);
    const g = Math.round(c1.g + (c2.g - c1.g) * fraction);
    const b = Math.round(c1.b + (c2.b - c1.b) * fraction);

    return `rgb(${r}, ${g}, ${b})`;
}

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : { r: 0, g: 0, b: 0 };
}

function updateHeatmapLegend(minValue, maxValue) {
    const scheme = colorSchemes[heatmapSensor];
    const legendGradient = document.getElementById('heatmap-legend-gradient');
    const legendValues = document.getElementById('legend-values');

    // Create CSS gradient
    const gradientStr = `linear-gradient(to right, ${scheme.gradient.join(', ')})`;
    legendGradient.style.background = gradientStr;

    // Update values
    legendValues.textContent =
        `${minValue.toFixed(1)}${scheme.unit} — ${maxValue.toFixed(1)}${scheme.unit}`;
}

function handleHeatmapHover(event) {
    const rect = heatmapCanvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate which cell was hovered
    const marginLeft = 60;
    const marginTop = 40;
    const marginRight = 20;
    const marginBottom = 60;

    const plotWidth = heatmapCanvas.width - marginLeft - marginRight;
    const plotHeight = heatmapCanvas.height - marginTop - marginBottom;

    const cellWidth = plotWidth / 24;
    const cellHeight = plotHeight / 7;

    const hour = Math.floor((x - marginLeft) / cellWidth);
    const day = Math.floor((y - marginTop) / cellHeight);

    if (hour >= 0 && hour < 24 && day >= 0 && day < 7) {
        const value = heatmapData.values[day][hour];

        if (value !== null) {
            showHeatmapTooltip(event, day, hour, value);
        } else {
            hideHeatmapTooltip();
        }
    } else {
        hideHeatmapTooltip();
    }
}

function showHeatmapTooltip(event, day, hour, value) {
    const tooltip = document.getElementById('heatmap-tooltip');
    const content = document.getElementById('tooltip-content');

    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const scheme = colorSchemes[heatmapSensor];

    content.innerHTML = `
        <strong>${days[day]} ${hour.toString().padStart(2, '0')}:00</strong><br>
        ${scheme.name}: ${value.toFixed(1)}${scheme.unit}<br>
        <em>(avg over ${getPeriodLabel(heatmapPeriod).toLowerCase()})</em>
    `;

    tooltip.style.left = `${event.clientX + 15}px`;
    tooltip.style.top = `${event.clientY + 15}px`;
    tooltip.classList.remove('hidden');
}

function hideHeatmapTooltip() {
    const tooltip = document.getElementById('heatmap-tooltip');
    tooltip.classList.add('hidden');
}

function getPeriodLabel(period) {
    const labels = {
        '4w': 'Last 4 Weeks',
        '8w': 'Last 8 Weeks',
        '3m': 'Last 3 Months',
        '6m': 'Last 6 Months',
        'all': 'All Time'
    };
    return labels[period] || period;
}

function generateHeatmapInsights() {
    if (!heatmapData) return;

    const insightsList = document.getElementById('heatmap-insights-list');
    insightsList.innerHTML = '';

    const insights = [];

    // Find coldest/hottest times
    const values = heatmapData.values;
    let minValue = Infinity;
    let maxValue = -Infinity;
    let minCell = null;
    let maxCell = null;

    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
            const value = values[day][hour];
            if (value !== null) {
                if (value < minValue) {
                    minValue = value;
                    minCell = { day, hour };
                }
                if (value > maxValue) {
                    maxValue = value;
                    maxCell = { day, hour };
                }
            }
        }
    }

    const scheme = colorSchemes[heatmapSensor];

    if (minCell) {
        insights.push(
            `Lowest: ${days[minCell.day]} ${minCell.hour.toString().padStart(2, '0')}:00 (avg ${minValue.toFixed(1)}${scheme.unit})`
        );
    }

    if (maxCell) {
        insights.push(
            `Highest: ${days[maxCell.day]} ${maxCell.hour.toString().padStart(2, '0')}:00 (avg ${maxValue.toFixed(1)}${scheme.unit})`
        );
    }

    // Weekday vs weekend comparison
    const weekdayAvg = calculateAverage(values.slice(0, 5));
    const weekendAvg = calculateAverage(values.slice(5, 7));

    if (weekdayAvg && weekendAvg) {
        const diff = Math.abs(weekdayAvg - weekendAvg);
        const direction = weekdayAvg > weekendAvg ? 'higher' : 'lower';
        insights.push(
            `Weekdays average ${diff.toFixed(1)}${scheme.unit} ${direction} than weekends`
        );
    }

    // Render insights
    insights.forEach(insight => {
        const li = document.createElement('li');
        li.textContent = `• ${insight}`;
        insightsList.appendChild(li);
    });
}

function calculateAverage(dayArrays) {
    const allValues = dayArrays.flat().filter(v => v !== null);
    if (allValues.length === 0) return null;
    return allValues.reduce((sum, v) => sum + v, 0) / allValues.length;
}

// Export initialization function
window.initializePatternsTab = initializePatternsTab;
```

---

## Backend Integration

### Add to analysis_engine.py

```python
def get_weekly_pattern(self, sensor, period='4w'):
    """
    Get hourly averages by day of week

    Returns:
        {
            "sensor": sensor_name,
            "period": period,
            "values": [[hour0_mon, hour1_mon, ...], [hour0_tue, ...], ...]  # 7x24 matrix
        }
    """
    # Convert period to time_range
    time_range_map = {
        '4w': '28d',
        '8w': '56d',
        '3m': '90d',
        '6m': '180d',
        'all': None
    }
    time_range = time_range_map.get(period, '28d')

    df = self.load_data(time_range, sensors=[sensor])

    if df.empty:
        return {"error": "No data available"}

    # Add day_of_week and hour columns
    df['day_of_week'] = df['gw_timestamp'].dt.dayofweek  # 0=Monday
    df['hour'] = df['gw_timestamp'].dt.hour

    # Group by day and hour, calculate mean
    grouped = df.groupby(['day_of_week', 'hour'])[sensor].mean()

    # Build 7x24 matrix
    values = []
    for day in range(7):
        day_values = []
        for hour in range(24):
            if (day, hour) in grouped.index:
                day_values.append(float(grouped[(day, hour)]))
            else:
                day_values.append(None)  # Missing data
        values.append(day_values)

    return {
        "sensor": sensor,
        "period": period,
        "values": values
    }
```

### Add to gateway_webview.py Api class

```python
def get_weekly_pattern(self, sensor, period='4w'):
    """Get hourly pattern by day of week"""
    return analysis_engine.get_weekly_pattern(sensor, period)
```

---

## Implementation Steps

1. **Create HTML structure** in tabs/tab_patterns.html
2. **Add CSS styles** for heatmap
3. **Implement JavaScript** rendering logic
4. **Add backend method** to analysis_engine.py
5. **Test with real data** - verify patterns match expectations
6. **Add interactivity** - hover tooltips, click events
7. **Optimize rendering** for smooth canvas drawing

---

## Success Criteria

- [ ] Heatmap renders correctly with proper colors
- [ ] Hover tooltip shows accurate values
- [ ] Sensor switching updates heatmap
- [ ] Period selection changes data range
- [ ] Legend accurately reflects min/max
- [ ] Insights auto-generate meaningful patterns
- [ ] Performance is smooth (< 500ms render)

---

## Future Enhancements

- Click cell to drill down to specific hour/day details
- Export heatmap as PNG image
- Overlay comparison (compare two time periods)
- Hourly heatmap (minute-level resolution)
- Custom time period selection
