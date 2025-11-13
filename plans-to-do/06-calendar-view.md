# Implementation Plan: Calendar View

**Priority:** MEDIUM-HIGH
**Phase:** 2
**Estimated Effort:** 5-6 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture
**Blocks:** None

---

## Overview

Create an interactive calendar view that displays daily averages for each sensor as color-coded day cells. Clicking a day drills down to show detailed data for that specific date. This provides an intuitive, month-at-a-glance overview perfect for spotting trends and anomalies.

---

## Goals & Objectives

1. **Month-at-a-Glance**: Visualize entire month in familiar calendar format
2. **Color-Coded Days**: Each day shows average sensor value as background color
3. **Interactive Drill-Down**: Click any day to see detailed hourly breakdown
4. **Multi-Month Navigation**: Browse forward/backward through months
5. **Multi-Sensor Support**: Toggle between different sensors

---

## Architecture

### Visual Design

```
┌────────────────────────────────────────────────────────────────┐
│  Patterns Tab > Calendar View                                 │
├────────────────────────────────────────────────────────────────┤
│  Sensor: [Temperature ▼]  « May 2024 »  [Today]             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│    Sun      Mon      Tue      Wed      Thu      Fri      Sat  │
│  ┌──────┐┌──────┐┌──────┐┌──────┐┌───1──┐┌───2──┐┌───3──┐  │
│  │      ││      ││      ││      ││ 71.2 ││ 72.5 ││ 73.1 │  │
│  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘  │
│  ┌───4──┐┌───5──┐┌───6──┐┌───7──┐┌───8──┐┌───9──┐┌──10──┐  │
│  │ 74.3 ││ 72.8 ││ 71.5 ││ 70.9 ││ 69.2 ││ 71.8 ││ 73.4 │  │
│  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘  │
│  ┌──11──┐┌──12──┐┌──13──┐┌──14──┐┌──15──┐┌──16──┐┌──17──┐  │
│  │ 75.2 ││ 76.1 ││ 74.8 ││ 73.3 ││ 72.1 ││ 71.9 ││ 73.7 │  │
│  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘  │
│  ┌──18──┐┌──19──┐┌──20──┐┌──21──┐┌──22──┐┌──23──┐┌──24──┐  │
│  │ 74.5 ││ 72.9 ││ 71.6 ││ 70.3 ││ 72.8 ││ 74.1 ││ 75.8 │  │
│  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘  │
│  ┌──25──┐┌──26──┐┌──27──┐┌──28──┐┌──29──┐┌──30──┐┌──31──┐  │
│  │ 73.2 ││ 71.7 ││ 72.4 ││ 73.9 ││ 74.6 ││ 72.1 ││ 71.8 │  │
│  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘  │
│                                                                │
│  Legend: Blue (cooler) → Yellow → Red (warmer)                │
│                                                                │
│  Click any day to see hourly details                          │
└────────────────────────────────────────────────────────────────┘

Day Detail Modal (Click May 15):
┌─────────────────────────────────────────────────────┐
│  May 15, 2024 - Temperature Details            [×]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Daily Average: 72.1°F                             │
│  Range: 68.5°F - 75.8°F (7.3°F variation)         │
│                                                     │
│  Hourly Breakdown:                                  │
│  ┌───────────────────────────────────────────────┐ │
│  │ 76°F │                         •••            │ │
│  │      │                     ••••   •           │ │
│  │ 72°F │            ••••••••           •        │ │
│  │      │       •••••                     ••••   │ │
│  │ 68°F │  ••••                              ••• │ │
│  │      └────────────────────────────────────   │ │
│  │       0    4    8   12   16   20   24       │ │
│  │                  Hour of Day                  │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  Statistics:                                        │
│  • Coldest: 6:15 AM (68.5°F)                      │
│  • Warmest: 3:47 PM (75.8°F)                      │
│  • Std Dev: 1.9°F                                  │
│  • Total Readings: 2,880                           │
│                                                     │
│  [View Full Day Data] [Close]                      │
└─────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### HTML Structure (add to tabs/tab_patterns.html)

```html
<!-- Add this section below heatmap -->
<div class="calendar-view">
    <h2>Calendar View</h2>

    <!-- Controls -->
    <div class="calendar-controls">
        <label for="calendar-sensor">Sensor:</label>
        <select id="calendar-sensor">
            <option value="temperature_sht">Temperature</option>
            <option value="humidity">Humidity</option>
            <option value="pressure">Pressure</option>
            <option value="light">Light</option>
            <option value="sound_level">Sound Level</option>
        </select>

        <button id="calendar-prev" class="btn-secondary">«</button>
        <span id="calendar-month-year" class="calendar-month-label">May 2024</span>
        <button id="calendar-next" class="btn-secondary">»</button>
        <button id="calendar-today" class="btn-primary">Today</button>
    </div>

    <!-- Calendar Grid -->
    <div class="calendar-grid-container">
        <div class="calendar-legend">
            <span>Low</span>
            <div id="calendar-legend-gradient" class="legend-gradient"></div>
            <span>High</span>
        </div>

        <div id="calendar-grid" class="calendar-grid">
            <!-- Day headers -->
            <div class="calendar-header">Sun</div>
            <div class="calendar-header">Mon</div>
            <div class="calendar-header">Tue</div>
            <div class="calendar-header">Wed</div>
            <div class="calendar-header">Thu</div>
            <div class="calendar-header">Fri</div>
            <div class="calendar-header">Sat</div>

            <!-- Day cells - populated dynamically -->
        </div>
    </div>

    <!-- Day Detail Modal -->
    <div id="day-detail-modal" class="modal hidden">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="day-detail-title">Day Details</h2>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body" id="day-detail-body">
                <!-- Populated dynamically -->
            </div>
            <div class="modal-footer">
                <button id="close-day-detail" class="btn-secondary">Close</button>
            </div>
        </div>
    </div>
</div>
```

### CSS (add to css/styles.css)

```css
/* Calendar View */
.calendar-view {
    margin-top: 40px;
    padding-top: 40px;
    border-top: 2px solid #e0e0e0;
}

.calendar-controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}

.calendar-month-label {
    font-size: 18px;
    font-weight: bold;
    min-width: 150px;
    text-align: center;
}

/* Calendar Grid */
.calendar-grid-container {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
}

.calendar-legend {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-bottom: 20px;
}

.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 5px;
    max-width: 900px;
    margin: 0 auto;
}

.calendar-header {
    text-align: center;
    font-weight: bold;
    padding: 10px;
    background-color: #34495e;
    color: white;
    border-radius: 5px;
}

.calendar-day {
    aspect-ratio: 1;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 8px;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
}

.calendar-day:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    z-index: 10;
}

.calendar-day.empty {
    background-color: #f9f9f9;
    cursor: default;
}

.calendar-day.empty:hover {
    transform: none;
    box-shadow: none;
}

.calendar-day.today {
    border: 3px solid #e74c3c;
    font-weight: bold;
}

.day-number {
    font-size: 14px;
    font-weight: bold;
    color: #333;
}

.day-value {
    font-size: 16px;
    text-align: center;
    color: #333;
}

.day-no-data {
    font-size: 12px;
    text-align: center;
    color: #999;
    font-style: italic;
}

/* Day Detail Modal */
.day-detail-chart {
    width: 100%;
    height: 300px;
    margin: 20px 0;
}

.day-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-top: 20px;
}

.day-stat-item {
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 5px;
}

.day-stat-label {
    font-size: 12px;
    color: #666;
    margin-bottom: 5px;
}

.day-stat-value {
    font-size: 18px;
    font-weight: bold;
    color: #2980b9;
}
```

### JavaScript (add to js/patterns.js)

```javascript
/**
 * Calendar View
 */

let calendarSensor = 'temperature_sht';
let calendarDate = new Date(); // Current viewing month
let calendarData = null;

function setupCalendarView() {
    // Sensor selector
    const sensorSelect = document.getElementById('calendar-sensor');
    if (sensorSelect) {
        sensorSelect.addEventListener('change', (e) => {
            calendarSensor = e.target.value;
            loadCalendarData();
        });
    }

    // Navigation buttons
    document.getElementById('calendar-prev')?.addEventListener('click', () => {
        calendarDate.setMonth(calendarDate.getMonth() - 1);
        loadCalendarData();
    });

    document.getElementById('calendar-next')?.addEventListener('click', () => {
        calendarDate.setMonth(calendarDate.getMonth() + 1);
        loadCalendarData();
    });

    document.getElementById('calendar-today')?.addEventListener('click', () => {
        calendarDate = new Date();
        loadCalendarData();
    });

    // Modal close
    document.querySelector('#day-detail-modal .modal-close')?.addEventListener('click', hideDayDetailModal);
    document.getElementById('close-day-detail')?.addEventListener('click', hideDayDetailModal);

    // Load initial data
    loadCalendarData();
}

async function loadCalendarData() {
    console.log(`Loading calendar data for ${calendarDate.toISOString()} - ${calendarSensor}`);

    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth() + 1; // JS months are 0-indexed

    try {
        const data = await window.pywebview.api.get_calendar_data(
            calendarSensor,
            year,
            month
        );

        calendarData = data;
        renderCalendar();
    } catch (error) {
        console.error('Failed to load calendar data:', error);
        alert('Failed to load calendar data. Please try again.');
    }
}

function renderCalendar() {
    if (!calendarData) return;

    // Update month/year label
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    const monthLabel = document.getElementById('calendar-month-year');
    monthLabel.textContent = `${monthNames[calendarDate.getMonth()]} ${calendarDate.getFullYear()}`;

    // Update legend
    updateCalendarLegend();

    // Clear existing day cells (keep headers)
    const grid = document.getElementById('calendar-grid');
    const headers = grid.querySelectorAll('.calendar-header');
    grid.innerHTML = '';
    headers.forEach(h => grid.appendChild(h));

    // Get first day of month and number of days
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay(); // 0 = Sunday
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Add empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
        const emptyCell = document.createElement('div');
        emptyCell.className = 'calendar-day empty';
        grid.appendChild(emptyCell);
    }

    // Add day cells
    const today = new Date();
    const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;

    for (let day = 1; day <= daysInMonth; day++) {
        const dayCell = createDayCell(day, isCurrentMonth && today.getDate() === day);
        grid.appendChild(dayCell);
    }
}

function createDayCell(day, isToday) {
    const cell = document.createElement('div');
    cell.className = 'calendar-day';
    if (isToday) cell.classList.add('today');

    // Day number
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day;
    cell.appendChild(dayNumber);

    // Day value
    const dayData = calendarData.days[day];

    if (dayData && dayData.avg !== null) {
        const dayValue = document.createElement('div');
        dayValue.className = 'day-value';
        dayValue.textContent = formatCalendarValue(calendarSensor, dayData.avg);
        cell.appendChild(dayValue);

        // Set background color
        const color = getColorForCalendarValue(dayData.avg, calendarData.min, calendarData.max);
        cell.style.backgroundColor = color;

        // Click handler
        cell.addEventListener('click', () => {
            showDayDetail(day, dayData);
        });
    } else {
        const noData = document.createElement('div');
        noData.className = 'day-no-data';
        noData.textContent = 'No data';
        cell.appendChild(noData);
        cell.style.backgroundColor = '#f9f9f9';
        cell.style.cursor = 'default';
    }

    return cell;
}

function formatCalendarValue(sensor, value) {
    switch (sensor) {
        case 'temperature_sht':
            return `${value.toFixed(1)}°F`;
        case 'humidity':
            return `${value.toFixed(1)}%`;
        case 'pressure':
            return `${value.toFixed(0)}`;
        case 'light':
        case 'sound_level':
            return Math.round(value).toString();
        default:
            return value.toFixed(1);
    }
}

function getColorForCalendarValue(value, min, max) {
    const normalized = (value - min) / (max - min);
    const scheme = colorSchemes[calendarSensor]; // Reuse from heatmap

    if (!scheme) return '#ddd';

    const gradient = scheme.gradient;
    const index = normalized * (gradient.length - 1);
    const lowerIndex = Math.floor(index);
    const upperIndex = Math.ceil(index);
    const fraction = index - lowerIndex;

    if (lowerIndex === upperIndex) {
        return gradient[lowerIndex];
    }

    return interpolateColor(gradient[lowerIndex], gradient[upperIndex], fraction);
}

function updateCalendarLegend() {
    if (!calendarData) return;

    const scheme = colorSchemes[calendarSensor];
    const legendGradient = document.getElementById('calendar-legend-gradient');

    const gradientStr = `linear-gradient(to right, ${scheme.gradient.join(', ')})`;
    legendGradient.style.background = gradientStr;
}

async function showDayDetail(day, dayData) {
    const modal = document.getElementById('day-detail-modal');
    const title = document.getElementById('day-detail-title');
    const body = document.getElementById('day-detail-body');

    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth() + 1;
    const dateStr = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;

    // Set title
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    title.textContent = `${monthNames[calendarDate.getMonth()]} ${day}, ${year} - ${SENSOR_FULL_NAMES[calendarSensor]}`;

    // Fetch hourly data for the day
    try {
        const hourlyData = await window.pywebview.api.get_day_hourly_data(calendarSensor, dateStr);

        body.innerHTML = `
            <div>
                <h3>Daily Average: ${formatCalendarValue(calendarSensor, dayData.avg)}</h3>
                <p>Range: ${formatCalendarValue(calendarSensor, dayData.min)} - ${formatCalendarValue(calendarSensor, dayData.max)}
                   (${formatCalendarValue(calendarSensor, dayData.max - dayData.min)} variation)</p>
            </div>

            <div class="day-detail-chart">
                <canvas id="day-hourly-chart" width="500" height="250"></canvas>
            </div>

            <div class="day-stats">
                <div class="day-stat-item">
                    <div class="day-stat-label">Coldest/Lowest</div>
                    <div class="day-stat-value">${formatCalendarValue(calendarSensor, dayData.min)}</div>
                </div>
                <div class="day-stat-item">
                    <div class="day-stat-label">Warmest/Highest</div>
                    <div class="day-stat-value">${formatCalendarValue(calendarSensor, dayData.max)}</div>
                </div>
                <div class="day-stat-item">
                    <div class="day-stat-label">Std Deviation</div>
                    <div class="day-stat-value">${formatCalendarValue(calendarSensor, dayData.std)}</div>
                </div>
                <div class="day-stat-item">
                    <div class="day-stat-label">Total Readings</div>
                    <div class="day-stat-value">${dayData.count}</div>
                </div>
            </div>
        `;

        // Render hourly chart
        renderDayHourlyChart(hourlyData);

        modal.classList.add('active');
    } catch (error) {
        console.error('Failed to load day details:', error);
        alert('Failed to load day details.');
    }
}

function renderDayHourlyChart(hourlyData) {
    const canvas = document.getElementById('day-hourly-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Simple line chart
    const marginLeft = 50;
    const marginTop = 20;
    const marginRight = 20;
    const marginBottom = 40;

    const plotWidth = canvas.width - marginLeft - marginRight;
    const plotHeight = canvas.height - marginTop - marginBottom;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Get min/max
    const values = hourlyData.hourly_values.filter(v => v !== null);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue;

    // Draw axes
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(marginLeft, marginTop);
    ctx.lineTo(marginLeft, canvas.height - marginBottom);
    ctx.lineTo(canvas.width - marginRight, canvas.height - marginBottom);
    ctx.stroke();

    // Draw line
    ctx.strokeStyle = '#2980b9';
    ctx.lineWidth = 2;
    ctx.beginPath();

    let firstPoint = true;

    for (let hour = 0; hour < 24; hour++) {
        const value = hourlyData.hourly_values[hour];

        if (value !== null) {
            const x = marginLeft + (hour / 23) * plotWidth;
            const y = canvas.height - marginBottom - ((value - minValue) / range) * plotHeight;

            if (firstPoint) {
                ctx.moveTo(x, y);
                firstPoint = false;
            } else {
                ctx.lineTo(x, y);
            }

            // Draw point
            ctx.fillStyle = '#2980b9';
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fill();
        }
    }

    ctx.stroke();

    // Labels
    ctx.fillStyle = '#333';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    // X-axis (hours)
    for (let hour = 0; hour <= 24; hour += 4) {
        const x = marginLeft + (hour / 23) * plotWidth;
        const y = canvas.height - marginBottom + 20;
        ctx.fillText(hour.toString(), x, y);
    }

    // Y-axis label
    ctx.save();
    ctx.translate(15, canvas.height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(SENSOR_FULL_NAMES[calendarSensor], 0, 0);
    ctx.restore();
}

function hideDayDetailModal() {
    const modal = document.getElementById('day-detail-modal');
    modal.classList.remove('active');
}

// Call from initializePatternsTab():
// setupCalendarView();
```

---

## Backend Integration

### Add to analysis_engine.py

```python
def get_calendar_data(self, sensor, year, month):
    """
    Get daily averages for a calendar month

    Returns:
        {
            "sensor": sensor,
            "year": year,
            "month": month,
            "min": overall_min,
            "max": overall_max,
            "days": {
                1: {"avg": ..., "min": ..., "max": ..., "std": ..., "count": ...},
                2: {...},
                ...
            }
        }
    """
    # Load data for the month
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

    time_range = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat()
    }

    df = self.load_data(time_range, sensors=[sensor])

    if df.empty:
        return {"error": "No data available"}

    # Add day column
    df['day'] = df['gw_timestamp'].dt.day

    # Group by day
    daily_stats = {}
    overall_min = float('inf')
    overall_max = float('-inf')

    for day in range(1, 32):  # Max days in month
        day_df = df[df['day'] == day]

        if not day_df.empty:
            series = day_df[sensor].dropna()

            if len(series) > 0:
                stats = {
                    "avg": float(series.mean()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "std": float(series.std()),
                    "count": len(series)
                }

                daily_stats[day] = stats

                overall_min = min(overall_min, stats["min"])
                overall_max = max(overall_max, stats["max"])

    return {
        "sensor": sensor,
        "year": year,
        "month": month,
        "min": overall_min,
        "max": overall_max,
        "days": daily_stats
    }

def get_day_hourly_data(self, sensor, date_str):
    """
    Get hourly data for a specific day

    date_str: "2024-05-15"

    Returns:
        {
            "hourly_values": [val_hour0, val_hour1, ..., val_hour23]
        }
    """
    date = datetime.fromisoformat(date_str)
    start_dt = datetime(date.year, date.month, date.day, 0, 0, 0)
    end_dt = datetime(date.year, date.month, date.day, 23, 59, 59)

    time_range = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat()
    }

    df = self.load_data(time_range, sensors=[sensor])

    if df.empty:
        return {"hourly_values": [None] * 24}

    # Add hour column
    df['hour'] = df['gw_timestamp'].dt.hour

    # Group by hour, take mean
    hourly_values = []
    for hour in range(24):
        hour_df = df[df['hour'] == hour]

        if not hour_df.empty:
            hourly_values.append(float(hour_df[sensor].mean()))
        else:
            hourly_values.append(None)

    return {
        "hourly_values": hourly_values
    }
```

### Add to gateway_webview.py Api class

```python
def get_calendar_data(self, sensor, year, month):
    """Get calendar month data"""
    return analysis_engine.get_calendar_data(sensor, year, month)

def get_day_hourly_data(self, sensor, date_str):
    """Get hourly data for specific day"""
    return analysis_engine.get_day_hourly_data(sensor, date_str)
```

---

## Implementation Steps

1. **Create HTML structure** in tab_patterns.html
2. **Add CSS styles** for calendar grid
3. **Implement calendar rendering** logic
4. **Add day detail modal** with hourly chart
5. **Implement backend methods** for daily/hourly data
6. **Test navigation** between months
7. **Verify drill-down** functionality

---

## Success Criteria

- [ ] Calendar renders correctly for any month
- [ ] Color coding reflects sensor values accurately
- [ ] Navigation (prev/next/today) works smoothly
- [ ] Clicking day shows detailed modal
- [ ] Hourly chart renders in modal
- [ ] Handles missing data gracefully
- [ ] Today's date highlighted

---

## Notes

The calendar view provides the most intuitive way for users to explore their historical data and spot patterns at a glance.
