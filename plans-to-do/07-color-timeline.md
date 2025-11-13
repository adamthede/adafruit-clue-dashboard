# Implementation Plan: Color Timeline Visualization

**Priority:** MEDIUM
**Phase:** 2
**Estimated Effort:** 4-5 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture
**Blocks:** None

---

## Overview

Create a unique visualization that displays the 6+ months of ambient color data captured by the CLUE's color sensor. This creates a visual "story" of the environment's lighting changes over time - a feature unique to this project that can't be replicated elsewhere.

---

## Goals & Objectives

1. **Visual Timeline**: Show color evolution over weeks/months
2. **Temporal Patterns**: Discover when lighting changed (seasons, bulb changes, routines)
3. **Color Analysis**: Find most common colors, unique events, color diversity
4. **Interactive Exploration**: Click time periods to see color details
5. **Export as Art**: Generate beautiful visualization that could be printed/shared

---

## Architecture

### Visual Design

```
┌────────────────────────────────────────────────────────────────┐
│  Patterns Tab > Color Timeline                                │
├────────────────────────────────────────────────────────────────┤
│  View: [Daily Blocks ▼]  Range: [Last 3 Months ▼]  [Refresh]│
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Your Environmental Color Story                               │
│                                                                │
│  May 2024                                                     │
│  ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ (31 days)                  │
│  │warm oranges     │cooler blues   │bright yellows│          │
│                                                                │
│  June 2024                                                    │
│  ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ (30 days)                   │
│  │yellows & whites              │evening oranges │            │
│                                                                │
│  July 2024                                                    │
│  ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ (31 days)                  │
│  │consistent warm tones all month               │            │
│                                                                │
│  ──────────────────────────────────────────────────────────  │
│                                                                │
│  Most Common Colors:                                          │
│  ▉ #FFD4A3 (18.3%)  ▉ #FF8C42 (12.1%)  ▉ #2A3B4C (9.7%)    │
│  ▉ #FFFFFF (8.4%)   ▉ #FFA07A (7.2%)   ▉ #87CEEB (5.9%)    │
│                                                                │
│  Insights:                                                     │
│  • Detected lighting change on June 15 (blues → yellows)      │
│  • Warmest colors: Evenings (6PM-10PM)                        │
│  • Coolest colors: Mornings (6AM-9AM)                         │
│  • 47 unique colors detected over 3 months                    │
│  • Color diversity increased 23% in July vs May               │
└────────────────────────────────────────────────────────────────┘

Detail View (Click a day block):
┌─────────────────────────────────────────────────────┐
│  May 15, 2024 - Color Details                  [×]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Dominant Color: #FFD4A3                           │
│  ████████████████████ (45% of day)                 │
│                                                     │
│  Hourly Color Progression:                         │
│  0─────6─────12────18────24                        │
│  ▉▉▉▉▉░░░░░░▓▓▓▓▓▓███████▓▓▉▉                    │
│  Dark  Dawn  Bright  Warm  Evening  Night         │
│                                                     │
│  Top Colors This Day:                              │
│  ▉ #FFD4A3 - 45% (Warm white)                     │
│  ▉ #2A3B4C - 28% (Cool blue)                      │
│  ▉ #FFFFFF - 15% (Bright white)                    │
│  ▉ #FF8C42 - 12% (Orange)                         │
│                                                     │
│  [Export Day Colors] [Close]                       │
└─────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### HTML Structure (add to tabs/tab_patterns.html)

```html
<!-- Add this section -->
<div class="color-timeline">
    <h2>Color Timeline</h2>
    <p class="subtitle">Your environmental color story captured over time</p>

    <!-- Controls -->
    <div class="color-timeline-controls">
        <label for="color-view-mode">View:</label>
        <select id="color-view-mode">
            <option value="daily">Daily Blocks</option>
            <option value="hourly">Hourly Detail</option>
            <option value="monthly">Monthly Average</option>
        </select>

        <label for="color-time-range">Range:</label>
        <select id="color-time-range">
            <option value="1m">Last Month</option>
            <option value="3m" selected>Last 3 Months</option>
            <option value="6m">Last 6 Months</option>
            <option value="all">All Time</option>
        </select>

        <button id="refresh-color-timeline" class="btn-primary">Refresh</button>
        <button id="export-color-art" class="btn-secondary">Export as Image</button>
    </div>

    <!-- Timeline Canvas -->
    <div class="color-timeline-canvas-container">
        <canvas id="color-timeline-canvas" width="1000" height="600"></canvas>
    </div>

    <!-- Most Common Colors -->
    <div class="color-palette-analysis">
        <h3>Most Common Colors</h3>
        <div id="common-colors-grid" class="common-colors-grid">
            <!-- Populated dynamically -->
        </div>
    </div>

    <!-- Color Insights -->
    <div class="color-insights">
        <h3>Color Insights</h3>
        <ul id="color-insights-list"></ul>
    </div>

    <!-- Color Detail Modal -->
    <div id="color-detail-modal" class="modal hidden">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="color-detail-title">Color Details</h2>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body" id="color-detail-body">
                <!-- Populated dynamically -->
            </div>
            <div class="modal-footer">
                <button id="close-color-detail" class="btn-secondary">Close</button>
            </div>
        </div>
    </div>
</div>
```

### CSS (add to css/styles.css)

```css
/* Color Timeline */
.color-timeline {
    margin-top: 40px;
    padding-top: 40px;
    border-top: 2px solid #e0e0e0;
}

.subtitle {
    text-align: center;
    color: #666;
    font-style: italic;
    margin-bottom: 20px;
}

.color-timeline-controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    flex-wrap: wrap;
}

.color-timeline-canvas-container {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
    overflow-x: auto;
}

#color-timeline-canvas {
    display: block;
    margin: 0 auto;
    cursor: pointer;
    max-width: 100%;
}

/* Color Palette Analysis */
.color-palette-analysis {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.common-colors-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-top: 15px;
}

.color-palette-item-large {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px;
    border: 1px solid #ddd;
    border-radius: 8px;
    transition: transform 0.2s;
}

.color-palette-item-large:hover {
    transform: scale(1.05);
}

.color-swatch-large {
    width: 60px;
    height: 60px;
    border-radius: 8px;
    border: 2px solid #333;
    flex-shrink: 0;
}

.color-info {
    flex: 1;
}

.color-hex-large {
    font-family: 'Courier New', monospace;
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 5px;
}

.color-percentage {
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
}

.color-name {
    font-size: 12px;
    color: #999;
    font-style: italic;
}

/* Color Insights */
.color-insights {
    background-color: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 8px;
    padding: 20px;
}

.color-insights h3 {
    margin-top: 0;
    color: #856404;
}

#color-insights-list {
    list-style: none;
    padding: 0;
}

#color-insights-list li {
    padding: 8px 0;
    border-bottom: 1px solid #ffeeba;
}

#color-insights-list li:last-child {
    border-bottom: none;
}

/* Color Detail Modal */
.color-progression-bar {
    width: 100%;
    height: 60px;
    border-radius: 8px;
    border: 1px solid #ddd;
    margin: 20px 0;
    display: flex;
    overflow: hidden;
}

.color-progression-segment {
    flex: 1;
    transition: flex 0.3s;
}

.color-progression-segment:hover {
    flex: 1.2;
}

.day-color-list {
    margin-top: 20px;
}

.day-color-item {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 10px;
    border-bottom: 1px solid #eee;
}

.day-color-item:last-child {
    border-bottom: none;
}
```

### JavaScript (add to js/patterns.js)

```javascript
/**
 * Color Timeline Visualization
 */

let colorTimelineData = null;
let colorViewMode = 'daily';
let colorTimeRange = '3m';
let colorCanvas = null;
let colorCtx = null;

function setupColorTimeline() {
    colorCanvas = document.getElementById('color-timeline-canvas');
    if (colorCanvas) {
        colorCtx = colorCanvas.getContext('2d');

        // Click handler for canvas
        colorCanvas.addEventListener('click', handleColorTimelineClick);
    }

    // View mode selector
    const viewModeSelect = document.getElementById('color-view-mode');
    if (viewModeSelect) {
        viewModeSelect.addEventListener('change', (e) => {
            colorViewMode = e.target.value;
            renderColorTimeline();
        });
    }

    // Time range selector
    const timeRangeSelect = document.getElementById('color-time-range');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', (e) => {
            colorTimeRange = e.target.value;
            loadColorTimelineData();
        });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refresh-color-timeline');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadColorTimelineData();
        });
    }

    // Export button
    const exportBtn = document.getElementById('export-color-art');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportColorArt);
    }

    // Modal close
    const modalClose = document.querySelector('#color-detail-modal .modal-close');
    const closeBtn = document.getElementById('close-color-detail');

    if (modalClose) modalClose.addEventListener('click', hideColorDetailModal);
    if (closeBtn) closeBtn.addEventListener('click', hideColorDetailModal);

    // Load initial data
    loadColorTimelineData();
}

async function loadColorTimelineData() {
    console.log(`Loading color timeline data: ${colorTimeRange}`);

    try {
        const data = await window.pywebview.api.get_color_timeline_data(colorTimeRange);
        colorTimelineData = data;
        renderColorTimeline();
        renderCommonColors();
        generateColorInsights();
    } catch (error) {
        console.error('Failed to load color timeline data:', error);
        alert('Failed to load color timeline. Please try again.');
    }
}

function renderColorTimeline() {
    if (!colorTimelineData || !colorCtx) return;

    const canvas = colorCanvas;
    const ctx = colorCtx;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (colorViewMode === 'daily') {
        renderDailyColorBlocks();
    } else if (colorViewMode === 'hourly') {
        renderHourlyColorDetail();
    } else if (colorViewMode === 'monthly') {
        renderMonthlyColorAverage();
    }
}

function renderDailyColorBlocks() {
    const ctx = colorCtx;
    const canvas = colorCanvas;

    const marginLeft = 100;
    const marginTop = 40;
    const marginBottom = 20;
    const rowHeight = 40;
    const dayWidth = 15;

    // Group by month
    const months = {};

    colorTimelineData.daily_colors.forEach(day => {
        const date = new Date(day.date);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;

        if (!months[monthKey]) {
            months[monthKey] = [];
        }

        months[monthKey].push(day);
    });

    let y = marginTop;

    Object.keys(months).sort().forEach(monthKey => {
        const days = months[monthKey];
        const [year, month] = monthKey.split('-');
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const monthLabel = `${monthNames[parseInt(month) - 1]} ${year}`;

        // Draw month label
        ctx.fillStyle = '#333';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(monthLabel, marginLeft - 10, y + rowHeight / 2 + 5);

        // Draw day blocks
        days.forEach((day, index) => {
            const x = marginLeft + index * dayWidth;

            ctx.fillStyle = day.dominant_color;
            ctx.fillRect(x, y, dayWidth - 1, rowHeight);

            // Store click area
            day._renderX = x;
            day._renderY = y;
            day._renderWidth = dayWidth;
            day._renderHeight = rowHeight;
        });

        // Draw day count
        ctx.fillStyle = '#999';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`(${days.length} days)`, marginLeft + days.length * dayWidth + 10, y + rowHeight / 2 + 5);

        y += rowHeight + 10;
    });
}

function renderHourlyColorDetail() {
    // More detailed view - each hour of each day as a tiny block
    // Similar logic but with finer granularity
    // Implementation similar to daily but with hourly_colors data
    const ctx = colorCtx;
    ctx.fillStyle = '#666';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Hourly detail view - Coming soon', colorCanvas.width / 2, colorCanvas.height / 2);
}

function renderMonthlyColorAverage() {
    // Large blocks for each month showing average color
    const ctx = colorCtx;
    ctx.fillStyle = '#666';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Monthly average view - Coming soon', colorCanvas.width / 2, colorCanvas.height / 2);
}

function handleColorTimelineClick(event) {
    if (!colorTimelineData || colorViewMode !== 'daily') return;

    const rect = colorCanvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Find clicked day
    const clickedDay = colorTimelineData.daily_colors.find(day => {
        return day._renderX && x >= day._renderX && x <= day._renderX + day._renderWidth &&
               y >= day._renderY && y <= day._renderY + day._renderHeight;
    });

    if (clickedDay) {
        showColorDetail(clickedDay);
    }
}

async function showColorDetail(dayData) {
    const modal = document.getElementById('color-detail-modal');
    const title = document.getElementById('color-detail-title');
    const body = document.getElementById('color-detail-body');

    const date = new Date(dayData.date);
    const dateStr = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

    title.textContent = `${dateStr} - Color Details`;

    // Fetch detailed hourly colors for the day
    try {
        const detailData = await window.pywebview.api.get_day_color_detail(dayData.date);

        // Create color progression bar
        let progressionHTML = '<div class="color-progression-bar">';

        detailData.top_colors.forEach(colorData => {
            progressionHTML += `
                <div class="color-progression-segment"
                     style="background-color: ${colorData.color}; flex: ${colorData.percentage};"
                     title="${colorData.color} - ${colorData.percentage.toFixed(1)}%">
                </div>
            `;
        });

        progressionHTML += '</div>';

        // Create color list
        let colorListHTML = '<div class="day-color-list">';

        detailData.top_colors.forEach(colorData => {
            const colorName = getColorName(colorData.color);

            colorListHTML += `
                <div class="day-color-item">
                    <div class="color-swatch-large" style="background-color: ${colorData.color};"></div>
                    <div class="color-info">
                        <div class="color-hex-large">${colorData.color}</div>
                        <div class="color-percentage">${colorData.percentage.toFixed(1)}% of day</div>
                        <div class="color-name">${colorName}</div>
                    </div>
                </div>
            `;
        });

        colorListHTML += '</div>';

        body.innerHTML = `
            <h3>Dominant Color: <span style="color: ${dayData.dominant_color}">${dayData.dominant_color}</span></h3>

            <h4>Color Distribution:</h4>
            ${progressionHTML}

            <h4>Top Colors This Day:</h4>
            ${colorListHTML}
        `;

        modal.classList.add('active');
    } catch (error) {
        console.error('Failed to load color detail:', error);
        alert('Failed to load color details.');
    }
}

function hideColorDetailModal() {
    const modal = document.getElementById('color-detail-modal');
    modal.classList.remove('active');
}

function renderCommonColors() {
    if (!colorTimelineData) return;

    const grid = document.getElementById('common-colors-grid');
    grid.innerHTML = '';

    colorTimelineData.most_common_colors.forEach(colorData => {
        const colorName = getColorName(colorData.color);

        const item = document.createElement('div');
        item.className = 'color-palette-item-large';

        item.innerHTML = `
            <div class="color-swatch-large" style="background-color: ${colorData.color};"></div>
            <div class="color-info">
                <div class="color-hex-large">${colorData.color}</div>
                <div class="color-percentage">${colorData.percentage.toFixed(1)}% of time</div>
                <div class="color-name">${colorName}</div>
            </div>
        `;

        grid.appendChild(item);
    });
}

function generateColorInsights() {
    if (!colorTimelineData) return;

    const insightsList = document.getElementById('color-insights-list');
    insightsList.innerHTML = '';

    const insights = [];

    // Total unique colors
    insights.push(`${colorTimelineData.unique_color_count} unique colors detected over ${getTimeRangeLabel(colorTimeRange).toLowerCase()}`);

    // Most common color
    if (colorTimelineData.most_common_colors.length > 0) {
        const topColor = colorTimelineData.most_common_colors[0];
        insights.push(`Most common: ${topColor.color} (${topColor.percentage.toFixed(1)}% of time)`);
    }

    // Color diversity (if available)
    if (colorTimelineData.color_diversity_trend) {
        insights.push(colorTimelineData.color_diversity_trend);
    }

    // Render insights
    insights.forEach(insight => {
        const li = document.createElement('li');
        li.textContent = `• ${insight}`;
        insightsList.appendChild(li);
    });
}

function getColorName(hexColor) {
    // Simple color name mapping (expand as needed)
    const colorNames = {
        '#FFFFFF': 'Bright White',
        '#FFD4A3': 'Warm White',
        '#FF8C42': 'Orange Glow',
        '#2A3B4C': 'Cool Blue',
        '#87CEEB': 'Sky Blue',
        '#FFA07A': 'Light Salmon',
        '#000000': 'Dark/Off'
    };

    return colorNames[hexColor.toUpperCase()] || 'Custom Color';
}

function exportColorArt() {
    // Export canvas as PNG
    const dataURL = colorCanvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `color-timeline-${new Date().toISOString().split('T')[0]}.png`;
    link.href = dataURL;
    link.click();
}

// Call from initializePatternsTab():
// setupColorTimeline();
```

---

## Backend Integration

### Add to analysis_engine.py

```python
def get_color_timeline_data(self, time_range='3m'):
    """
    Get color data for timeline visualization

    Returns:
        {
            "daily_colors": [
                {"date": "2024-05-01", "dominant_color": "#FFD4A3", ...},
                ...
            ],
            "most_common_colors": [
                {"color": "#FFD4A3", "count": 1234, "percentage": 18.3},
                ...
            ],
            "unique_color_count": 47,
            "color_diversity_trend": "Color diversity increased 23% in July vs May"
        }
    """
    df = self.load_data(time_range, sensors=['color_hex'])

    if df.empty:
        return {"error": "No data available"}

    # Daily dominant colors
    df['date'] = df['gw_timestamp'].dt.date

    daily_colors = []
    for date, group in df.groupby('date'):
        dominant_color = group['color_hex'].mode().iloc[0] if len(group) > 0 else '#000000'

        daily_colors.append({
            "date": date.isoformat(),
            "dominant_color": dominant_color,
            "sample_count": len(group)
        })

    # Most common colors overall
    color_counts = df['color_hex'].value_counts()
    total_count = len(df)

    most_common = []
    for color, count in color_counts.head(6).items():
        most_common.append({
            "color": color,
            "count": int(count),
            "percentage": float((count / total_count) * 100)
        })

    return {
        "daily_colors": daily_colors,
        "most_common_colors": most_common,
        "unique_color_count": len(color_counts),
        "color_diversity_trend": None  # TODO: Calculate trend
    }

def get_day_color_detail(self, date_str):
    """
    Get detailed color breakdown for a specific day

    Returns:
        {
            "top_colors": [
                {"color": "#FFD4A3", "count": 432, "percentage": 45.0},
                ...
            ]
        }
    """
    date = datetime.fromisoformat(date_str)
    start_dt = datetime(date.year, date.month, date.day, 0, 0, 0)
    end_dt = datetime(date.year, date.month, date.day, 23, 59, 59)

    time_range = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat()
    }

    df = self.load_data(time_range, sensors=['color_hex'])

    if df.empty:
        return {"top_colors": []}

    color_counts = df['color_hex'].value_counts()
    total_count = len(df)

    top_colors = []
    for color, count in color_counts.head(4).items():
        top_colors.append({
            "color": color,
            "count": int(count),
            "percentage": float((count / total_count) * 100)
        })

    return {
        "top_colors": top_colors
    }
```

### Add to gateway_webview.py Api class

```python
def get_color_timeline_data(self, time_range='3m'):
    """Get color timeline data"""
    return analysis_engine.get_color_timeline_data(time_range)

def get_day_color_detail(self, date_str):
    """Get detailed color breakdown for specific day"""
    return analysis_engine.get_day_color_detail(date_str)
```

---

## Implementation Steps

1. **Create HTML structure** in tab_patterns.html
2. **Add CSS styles** for timeline and color swatches
3. **Implement canvas rendering** for daily blocks
4. **Add click interaction** for drill-down
5. **Implement backend methods** for color data
6. **Add export functionality** (canvas to PNG)
7. **Test with real color data** - verify visualization is meaningful

---

## Success Criteria

- [ ] Timeline renders with actual color blocks
- [ ] Months are labeled clearly
- [ ] Clicking a day shows detailed modal
- [ ] Most common colors displayed accurately
- [ ] Export creates usable PNG image
- [ ] Handles 6+ months of data smoothly
- [ ] Visual is aesthetically pleasing

---

## Notes

This is a truly unique feature - no other environmental monitor captures ambient color over time like this. The visualization could be printed as art or used to understand lighting patterns and changes in the environment.
