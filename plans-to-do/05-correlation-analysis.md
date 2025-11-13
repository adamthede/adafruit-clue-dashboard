# Implementation Plan: Correlation Analysis & Scatter Plots

**Priority:** HIGH
**Phase:** 2
**Estimated Effort:** 5-7 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture
**Blocks:** None

---

## Overview

Create interactive correlation analysis tools to discover relationships between different environmental sensors. Includes a correlation matrix heatmap and interactive scatter plots that reveal how sensors influence each other over time.

---

## Goals & Objectives

1. **Discover Relationships**: Visualize correlations between all sensor pairs
2. **Quantify Strength**: Show correlation coefficients (-1 to +1)
3. **Interactive Exploration**: Click matrix cell to see detailed scatter plot
4. **Lag Analysis**: Optional feature to detect time-delayed relationships
5. **Actionable Insights**: Auto-generate findings (e.g., "Temperature ↑ → Humidity ↓")

---

## Architecture

### Visual Layout

```
┌────────────────────────────────────────────────────────────────┐
│  Analysis Tab > Correlation Analysis                          │
├────────────────────────────────────────────────────────────────┤
│  Time Range: [Last 30 Days ▼]  [Refresh]                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Correlation Matrix                                           │
│  ┌───────────────────────────────────────────────────────┐   │
│  │         Temp    Humid   Press   Light   Sound         │   │
│  │ Temp   │1.00│ -0.65│  0.23│  0.41│  0.18│            │   │
│  │ Humid  │-0.65│  1.00│ -0.12│ -0.32│ -0.08│            │   │
│  │ Press  │ 0.23│ -0.12│  1.00│  0.15│  0.09│            │   │
│  │ Light  │ 0.41│ -0.32│  0.15│  1.00│  0.52│            │   │
│  │ Sound  │ 0.18│ -0.08│  0.09│  0.52│  1.00│            │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                                │
│  Click any cell to see scatter plot                           │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Temperature vs. Humidity (r = -0.65)                    │ │
│  │                                                         │ │
│  │  60% │                        • •                       │ │
│  │      │              • •  • • •                         │ │
│  │  50% │          • • •   • •                            │ │
│  │      │      • • •                                      │ │
│  │  40% │  • • •                                          │ │
│  │      └────────────────────────────────                │ │
│  │        68°F   70°F   72°F   74°F   76°F               │ │
│  │                                                         │ │
│  │  Strong negative correlation: As temperature rises,    │ │
│  │  humidity tends to decrease.                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  Key Findings:                                                │
│  • Temperature & Humidity: Strong inverse (-0.65)             │
│  • Light & Sound: Moderate positive (0.52) - activity?       │
│  • Pressure: Mostly independent of other sensors              │
└────────────────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### HTML Structure (add to tabs/tab_analysis.html)

```html
<!-- Add this section below the statistics dashboard -->
<div class="correlation-analysis">
    <h2>Correlation Analysis</h2>

    <!-- Controls -->
    <div class="correlation-controls">
        <label for="corr-time-range">Time Range:</label>
        <select id="corr-time-range">
            <option value="7d">Last 7 Days</option>
            <option value="30d" selected>Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="all">All Time</option>
        </select>
        <button id="refresh-correlation" class="btn-primary">Refresh</button>
    </div>

    <!-- Correlation Matrix -->
    <div class="correlation-matrix-container">
        <h3>Correlation Matrix</h3>
        <p class="help-text">Click any cell to see detailed scatter plot</p>
        <table id="correlation-matrix" class="correlation-matrix">
            <!-- Populated dynamically -->
        </table>
    </div>

    <!-- Scatter Plot -->
    <div class="scatter-plot-container">
        <h3 id="scatter-title">Select a correlation cell to view scatter plot</h3>
        <canvas id="scatter-canvas" width="800" height="500"></canvas>
        <div id="scatter-insights" class="scatter-insights"></div>
    </div>

    <!-- Key Findings -->
    <div class="correlation-insights">
        <h3>Key Findings</h3>
        <ul id="correlation-findings"></ul>
    </div>
</div>
```

### CSS (add to css/styles.css)

```css
/* Correlation Analysis */
.correlation-analysis {
    margin-top: 40px;
    padding-top: 40px;
    border-top: 2px solid #e0e0e0;
}

.correlation-controls {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}

/* Correlation Matrix */
.correlation-matrix-container {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.help-text {
    color: #666;
    font-size: 14px;
    font-style: italic;
    margin-bottom: 15px;
}

.correlation-matrix {
    margin: 0 auto;
    border-collapse: collapse;
    font-size: 14px;
}

.correlation-matrix th,
.correlation-matrix td {
    padding: 12px;
    text-align: center;
    border: 1px solid #ddd;
    min-width: 80px;
}

.correlation-matrix th {
    background-color: #34495e;
    color: white;
    font-weight: bold;
}

.correlation-matrix td {
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Courier New', monospace;
}

.correlation-matrix td:hover {
    transform: scale(1.1);
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
    z-index: 10;
}

/* Color coding for correlation strength */
.corr-strong-positive {
    background-color: #27ae60;
    color: white;
    font-weight: bold;
}

.corr-moderate-positive {
    background-color: #7bed9f;
    color: #333;
}

.corr-weak-positive {
    background-color: #dfe4ea;
    color: #333;
}

.corr-weak-negative {
    background-color: #ffd7d7;
    color: #333;
}

.corr-moderate-negative {
    background-color: #ff6b81;
    color: white;
}

.corr-strong-negative {
    background-color: #e74c3c;
    color: white;
    font-weight: bold;
}

.corr-perfect {
    background-color: #34495e;
    color: white;
    font-weight: bold;
}

/* Scatter Plot */
.scatter-plot-container {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

#scatter-title {
    text-align: center;
    color: #333;
    margin-bottom: 15px;
}

#scatter-canvas {
    display: block;
    margin: 0 auto;
    border: 1px solid #eee;
    max-width: 100%;
    height: auto;
}

.scatter-insights {
    margin-top: 15px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 5px;
    font-size: 14px;
    line-height: 1.6;
}

/* Correlation Insights */
.correlation-insights {
    background-color: #e8f8f5;
    border: 1px solid #a2d9ce;
    border-radius: 8px;
    padding: 20px;
}

.correlation-insights h3 {
    margin-top: 0;
    color: #16a085;
}

#correlation-findings {
    list-style: none;
    padding: 0;
}

#correlation-findings li {
    padding: 8px 0;
    border-bottom: 1px solid #d5f4e6;
}

#correlation-findings li:last-child {
    border-bottom: none;
}
```

### JavaScript (add to js/analysis.js)

```javascript
/**
 * Correlation Analysis
 */

let correlationData = null;
let correlationTimeRange = '30d';
let scatterCanvas = null;
let scatterCtx = null;

const SENSOR_LABELS = {
    'temperature_sht': 'Temp',
    'humidity': 'Humid',
    'pressure': 'Press',
    'light': 'Light',
    'sound_level': 'Sound'
};

const SENSOR_FULL_NAMES = {
    'temperature_sht': 'Temperature',
    'humidity': 'Humidity',
    'pressure': 'Pressure',
    'light': 'Light',
    'sound_level': 'Sound Level'
};

function setupCorrelationAnalysis() {
    scatterCanvas = document.getElementById('scatter-canvas');
    if (scatterCanvas) {
        scatterCtx = scatterCanvas.getContext('2d');
    }

    // Time range selector
    const timeRangeSelect = document.getElementById('corr-time-range');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', (e) => {
            correlationTimeRange = e.target.value;
            loadCorrelationData();
        });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refresh-correlation');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadCorrelationData();
        });
    }

    // Load initial data
    loadCorrelationData();
}

async function loadCorrelationData() {
    console.log(`Loading correlation data for time range: ${correlationTimeRange}`);

    try {
        const data = await window.pywebview.api.get_correlation_matrix(correlationTimeRange);
        correlationData = data;
        renderCorrelationMatrix();
        generateCorrelationFindings();
    } catch (error) {
        console.error('Failed to load correlation data:', error);
        alert('Failed to load correlation analysis. Please try again.');
    }
}

function renderCorrelationMatrix() {
    if (!correlationData) return;

    const table = document.getElementById('correlation-matrix');
    table.innerHTML = '';

    const sensors = correlationData.sensors || Object.keys(SENSOR_LABELS);
    const matrix = correlationData.matrix;

    // Header row
    const headerRow = document.createElement('tr');
    headerRow.appendChild(document.createElement('th')); // Empty corner cell

    sensors.forEach(sensor => {
        const th = document.createElement('th');
        th.textContent = SENSOR_LABELS[sensor];
        th.title = SENSOR_FULL_NAMES[sensor];
        headerRow.appendChild(th);
    });

    table.appendChild(headerRow);

    // Data rows
    sensors.forEach((sensorY, i) => {
        const row = document.createElement('tr');

        // Row header
        const th = document.createElement('th');
        th.textContent = SENSOR_LABELS[sensorY];
        th.title = SENSOR_FULL_NAMES[sensorY];
        row.appendChild(th);

        // Data cells
        sensors.forEach((sensorX, j) => {
            const td = document.createElement('td');
            const corrValue = matrix[i][j];

            td.textContent = corrValue.toFixed(2);
            td.dataset.sensorX = sensorX;
            td.dataset.sensorY = sensorY;
            td.dataset.corrValue = corrValue;

            // Color coding
            td.className = getCorrelationClass(corrValue);

            // Click handler (except diagonal)
            if (i !== j) {
                td.addEventListener('click', () => {
                    showScatterPlot(sensorX, sensorY, corrValue);
                });
            }

            row.appendChild(td);
        });

        table.appendChild(row);
    });
}

function getCorrelationClass(value) {
    if (Math.abs(value - 1.0) < 0.01) return 'corr-perfect';
    if (value >= 0.7) return 'corr-strong-positive';
    if (value >= 0.4) return 'corr-moderate-positive';
    if (value >= 0.1) return 'corr-weak-positive';
    if (value >= -0.1) return 'corr-weak-positive';
    if (value >= -0.4) return 'corr-weak-negative';
    if (value >= -0.7) return 'corr-moderate-negative';
    return 'corr-strong-negative';
}

async function showScatterPlot(sensorX, sensorY, corrValue) {
    console.log(`Showing scatter plot: ${sensorX} vs ${sensorY}`);

    // Update title
    const title = document.getElementById('scatter-title');
    title.textContent = `${SENSOR_FULL_NAMES[sensorX]} vs. ${SENSOR_FULL_NAMES[sensorY]} (r = ${corrValue.toFixed(2)})`;

    // Fetch scatter data
    try {
        const scatterData = await window.pywebview.api.get_scatter_data(
            sensorX,
            sensorY,
            correlationTimeRange
        );

        renderScatterPlot(scatterData, sensorX, sensorY, corrValue);
        generateScatterInsights(sensorX, sensorY, corrValue);
    } catch (error) {
        console.error('Failed to load scatter data:', error);
        alert('Failed to load scatter plot. Please try again.');
    }
}

function renderScatterPlot(data, sensorX, sensorY, corrValue) {
    if (!scatterCtx || !data.points) return;

    const canvas = scatterCanvas;
    const ctx = scatterCtx;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dimensions
    const marginLeft = 80;
    const marginTop = 40;
    const marginRight = 40;
    const marginBottom = 80;

    const plotWidth = canvas.width - marginLeft - marginRight;
    const plotHeight = canvas.height - marginTop - marginBottom;

    // Get data ranges
    const xValues = data.points.map(p => p.x);
    const yValues = data.points.map(p => p.y);

    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const yMin = Math.min(...yValues);
    const yMax = Math.max(...yValues);

    // Add some padding
    const xRange = xMax - xMin;
    const yRange = yMax - yMin;
    const xPadding = xRange * 0.1;
    const yPadding = yRange * 0.1;

    // Draw axes
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(marginLeft, marginTop);
    ctx.lineTo(marginLeft, canvas.height - marginBottom);
    ctx.lineTo(canvas.width - marginRight, canvas.height - marginBottom);
    ctx.stroke();

    // Plot points
    ctx.fillStyle = 'rgba(41, 128, 185, 0.5)';

    data.points.forEach(point => {
        const x = marginLeft + ((point.x - xMin + xPadding) / (xRange + 2 * xPadding)) * plotWidth;
        const y = canvas.height - marginBottom - ((point.y - yMin + yPadding) / (yRange + 2 * yPadding)) * plotHeight;

        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
    });

    // Draw trend line if correlation is significant
    if (Math.abs(corrValue) > 0.3) {
        drawTrendLine(ctx, data.points, xMin, xMax, yMin, yMax, xPadding, yPadding, xRange, yRange, marginLeft, marginTop, marginBottom, plotWidth, plotHeight, canvas.height);
    }

    // Labels
    ctx.fillStyle = '#333';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';

    // X-axis label
    ctx.fillText(SENSOR_FULL_NAMES[sensorX], canvas.width / 2, canvas.height - 20);

    // Y-axis label (rotated)
    ctx.save();
    ctx.translate(20, canvas.height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(SENSOR_FULL_NAMES[sensorY], 0, 0);
    ctx.restore();

    // Axis tick labels
    drawAxisLabels(ctx, xMin, xMax, yMin, yMax, marginLeft, marginTop, marginBottom, plotWidth, plotHeight, canvas.height);
}

function drawTrendLine(ctx, points, xMin, xMax, yMin, yMax, xPadding, yPadding, xRange, yRange, marginLeft, marginTop, marginBottom, plotWidth, plotHeight, canvasHeight) {
    // Calculate linear regression
    const n = points.length;
    const sumX = points.reduce((sum, p) => sum + p.x, 0);
    const sumY = points.reduce((sum, p) => sum + p.y, 0);
    const sumXY = points.reduce((sum, p) => sum + p.x * p.y, 0);
    const sumXX = points.reduce((sum, p) => sum + p.x * p.x, 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    // Draw line
    const x1 = xMin;
    const y1 = slope * x1 + intercept;
    const x2 = xMax;
    const y2 = slope * x2 + intercept;

    const canvasX1 = marginLeft + ((x1 - xMin + xPadding) / (xRange + 2 * xPadding)) * plotWidth;
    const canvasY1 = canvasHeight - marginBottom - ((y1 - yMin + yPadding) / (yRange + 2 * yPadding)) * plotHeight;
    const canvasX2 = marginLeft + ((x2 - xMin + xPadding) / (xRange + 2 * xPadding)) * plotWidth;
    const canvasY2 = canvasHeight - marginBottom - ((y2 - yMin + yPadding) / (yRange + 2 * yPadding)) * plotHeight;

    ctx.strokeStyle = '#e74c3c';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(canvasX1, canvasY1);
    ctx.lineTo(canvasX2, canvasY2);
    ctx.stroke();
    ctx.setLineDash([]);
}

function drawAxisLabels(ctx, xMin, xMax, yMin, yMax, marginLeft, marginTop, marginBottom, plotWidth, plotHeight, canvasHeight) {
    ctx.fillStyle = '#666';
    ctx.font = '12px sans-serif';

    // X-axis ticks
    const xTicks = 5;
    for (let i = 0; i <= xTicks; i++) {
        const value = xMin + (xMax - xMin) * (i / xTicks);
        const x = marginLeft + (i / xTicks) * plotWidth;
        const y = canvasHeight - marginBottom + 20;

        ctx.textAlign = 'center';
        ctx.fillText(value.toFixed(1), x, y);
    }

    // Y-axis ticks
    const yTicks = 5;
    for (let i = 0; i <= yTicks; i++) {
        const value = yMin + (yMax - yMin) * (i / yTicks);
        const x = marginLeft - 10;
        const y = canvasHeight - marginBottom - (i / yTicks) * plotHeight;

        ctx.textAlign = 'right';
        ctx.fillText(value.toFixed(1), x, y + 5);
    }
}

function generateScatterInsights(sensorX, sensorY, corrValue) {
    const insightsDiv = document.getElementById('scatter-insights');

    let interpretation = '';

    if (Math.abs(corrValue) >= 0.7) {
        interpretation = Math.abs(corrValue) === 1 ? 'Perfect' : 'Strong';
    } else if (Math.abs(corrValue) >= 0.4) {
        interpretation = 'Moderate';
    } else {
        interpretation = 'Weak';
    }

    const direction = corrValue > 0 ? 'positive' : 'negative';
    const relationship = corrValue > 0
        ? `As ${SENSOR_FULL_NAMES[sensorX]} increases, ${SENSOR_FULL_NAMES[sensorY]} tends to increase.`
        : `As ${SENSOR_FULL_NAMES[sensorX]} increases, ${SENSOR_FULL_NAMES[sensorY]} tends to decrease.`;

    insightsDiv.innerHTML = `
        <strong>${interpretation} ${direction} correlation (r = ${corrValue.toFixed(2)})</strong><br>
        ${relationship}
    `;
}

function generateCorrelationFindings() {
    if (!correlationData) return;

    const findingsList = document.getElementById('correlation-findings');
    findingsList.innerHTML = '';

    const sensors = correlationData.sensors || Object.keys(SENSOR_LABELS);
    const matrix = correlationData.matrix;

    const findings = [];

    // Find strongest correlations (excluding diagonal)
    const correlations = [];

    sensors.forEach((sensorY, i) => {
        sensors.forEach((sensorX, j) => {
            if (i < j) { // Only upper triangle (avoid duplicates)
                const corrValue = matrix[i][j];
                correlations.push({
                    sensorX,
                    sensorY,
                    value: corrValue
                });
            }
        });
    });

    // Sort by absolute value
    correlations.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

    // Top 3 correlations
    correlations.slice(0, 3).forEach(corr => {
        const strength = Math.abs(corr.value) >= 0.7 ? 'Strong' : Math.abs(corr.value) >= 0.4 ? 'Moderate' : 'Weak';
        const direction = corr.value > 0 ? 'positive' : 'inverse';

        findings.push(
            `${SENSOR_FULL_NAMES[corr.sensorX]} & ${SENSOR_FULL_NAMES[corr.sensorY]}: ${strength} ${direction} (${corr.value.toFixed(2)})`
        );
    });

    // Render findings
    findings.forEach(finding => {
        const li = document.createElement('li');
        li.textContent = `• ${finding}`;
        findingsList.appendChild(li);
    });
}

// Call this from initializeAnalysisTab()
// Add: setupCorrelationAnalysis();
```

---

## Backend Integration

### Add to analysis_engine.py

```python
def compute_correlation_matrix(self, time_range=None):
    """
    Compute correlation matrix for all sensors

    Returns:
        {
            "sensors": [...],
            "matrix": [[...], [...], ...]
        }
    """
    sensors = ['temperature_sht', 'humidity', 'pressure', 'light', 'sound_level']
    df = self.load_data(time_range, sensors=sensors)

    if df.empty:
        return {"error": "No data available"}

    # Compute correlation matrix
    corr_matrix = df[sensors].corr()

    return {
        "sensors": sensors,
        "matrix": corr_matrix.values.tolist()
    }

def get_scatter_data(self, sensor_x, sensor_y, time_range=None, max_points=1000):
    """
    Get scatter plot data for two sensors

    Returns:
        {
            "points": [{"x": ..., "y": ...}, ...]
        }
    """
    df = self.load_data(time_range, sensors=[sensor_x, sensor_y])

    if df.empty:
        return {"error": "No data available"}

    # Drop rows with NaN in either column
    df_clean = df[[sensor_x, sensor_y]].dropna()

    # Downsample if too many points
    if len(df_clean) > max_points:
        df_clean = df_clean.sample(n=max_points, random_state=42)

    points = [
        {"x": float(row[sensor_x]), "y": float(row[sensor_y])}
        for _, row in df_clean.iterrows()
    ]

    return {
        "points": points,
        "count": len(points)
    }
```

### Add to gateway_webview.py Api class

```python
def get_correlation_matrix(self, time_range=None):
    """Get correlation matrix for all sensors"""
    return analysis_engine.compute_correlation_matrix(time_range)

def get_scatter_data(self, sensor_x, sensor_y, time_range=None):
    """Get scatter plot data for two sensors"""
    return analysis_engine.get_scatter_data(sensor_x, sensor_y, time_range)
```

---

## Implementation Steps

1. **Add HTML structure** to tab_analysis.html
2. **Add CSS styles** for matrix and scatter plot
3. **Implement matrix rendering** in JavaScript
4. **Implement scatter plot rendering** with Canvas API
5. **Add backend methods** to analysis_engine.py
6. **Test with real data** - verify correlations are accurate
7. **Add insights generation** - auto-detect patterns

---

## Success Criteria

- [ ] Correlation matrix displays correctly with color coding
- [ ] Clicking cell shows scatter plot
- [ ] Scatter plot renders with proper axes and labels
- [ ] Trend line draws for significant correlations
- [ ] Insights accurately describe relationships
- [ ] Performance handles 1000+ scatter points smoothly

---

## Notes

This feature reveals hidden relationships in the data and is particularly useful for understanding environmental cause-effect patterns.
