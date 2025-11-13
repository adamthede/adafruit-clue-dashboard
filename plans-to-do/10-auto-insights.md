# Implementation Plan: Auto-Generated Insights & Data Stories

**Priority:** MEDIUM
**Phase:** 3
**Estimated Effort:** 3-4 hours
**Dependencies:** 01-backend-analysis-engine

---

## Overview

Automatically generate natural-language insights from sensor data that tell the "story" of what's happening in the environment. Transform raw statistics into human-readable, actionable observations.

---

## Goals

1. **Automatic Discovery**: Scan data for interesting patterns
2. **Natural Language**: Present findings in plain English
3. **Actionable**: Provide insights users can act on
4. **Contextual**: Compare to historical baselines
5. **Refresh Daily**: New insights based on recent data

---

## Insight Categories

### 1. **Trend Insights**
- "Temperature has been steadily increasing over the past week (+1.2°F per day)"
- "Humidity is 15% lower than this time last month"

### 2. **Pattern Insights**
- "You tend to arrive home around 6:15 PM on weekdays (sound spike)"
- "Weekend mornings are consistently 3°F warmer than weekdays"

### 3. **Anomaly Insights**
- "Detected unusual temperature spike on July 15 (85.3°F - highest ever)"
- "Sound levels have been quieter than normal this week"

### 4. **Correlation Insights**
- "When temperature rises, humidity tends to drop (r=-0.65)"
- "Light and sound are often high together - possible activity correlation"

### 5. **Environmental Health**
- "Your space was in the comfort zone 78% of this week"
- "Air pressure has been stable - good weather conditions"

### 6. **Milestone Insights**
- "Celebrating 6 months of continuous monitoring!"
- "You've collected over 500,000 data points"

---

## Implementation

### Backend (analysis_engine.py)
```python
class InsightGenerator:
    """Generate natural language insights from sensor data"""

    def generate_insights(self, time_range='7d'):
        """
        Generate insights for recent time period

        Returns:
            {
                "insights": [
                    {
                        "category": "trend|pattern|anomaly|correlation|milestone",
                        "priority": "high|medium|low",
                        "title": "Short title",
                        "description": "Longer explanation",
                        "icon": "emoji",
                        "data": {...supporting data...}
                    },
                    ...
                ]
            }
        """
        insights = []

        # Trend insights
        insights.extend(self._generate_trend_insights(time_range))

        # Pattern insights
        insights.extend(self._generate_pattern_insights(time_range))

        # Anomaly insights (if any)
        insights.extend(self._generate_anomaly_insights(time_range))

        # Correlation insights
        insights.extend(self._generate_correlation_insights(time_range))

        # Milestone insights
        insights.extend(self._generate_milestone_insights())

        # Sort by priority
        insights.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['priority']])

        return {"insights": insights}

    def _generate_trend_insights(self, time_range):
        """Detect trends using linear regression"""
        insights = []

        df = self.load_data(time_range)

        for sensor in ['temperature_sht', 'humidity', 'pressure']:
            # Calculate trend
            x = np.arange(len(df))
            y = df[sensor].values

            if len(y) < 10:
                continue

            # Linear regression
            slope, intercept = np.polyfit(x, y, 1)

            # Convert slope to per-day rate
            samples_per_day = 2880  # 30-second intervals
            daily_change = slope * samples_per_day

            if abs(daily_change) > 0.5:  # Significant change
                direction = "increasing" if daily_change > 0 else "decreasing"

                insights.append({
                    "category": "trend",
                    "priority": "high" if abs(daily_change) > 2 else "medium",
                    "title": f"{SENSOR_NAMES[sensor]} is {direction}",
                    "description": f"{SENSOR_NAMES[sensor]} has been steadily {direction} over the past {time_range} ({daily_change:+.1f} per day)",
                    "icon": "📈" if daily_change > 0 else "📉",
                    "data": {"slope": daily_change, "sensor": sensor}
                })

        return insights

    def _generate_pattern_insights(self, time_range):
        """Find recurring patterns"""
        insights = []

        # Weekday vs weekend comparison
        df = self.load_data(time_range)
        df['is_weekend'] = df['gw_timestamp'].dt.dayofweek >= 5

        for sensor in ['temperature_sht', 'light', 'sound_level']:
            weekday_mean = df[~df['is_weekend']][sensor].mean()
            weekend_mean = df[df['is_weekend']][sensor].mean()

            diff = weekend_mean - weekday_mean
            percent_diff = abs(diff / weekday_mean * 100)

            if percent_diff > 10:  # Significant difference
                higher = "weekends" if diff > 0 else "weekdays"

                insights.append({
                    "category": "pattern",
                    "priority": "medium",
                    "title": f"{higher.title()} are different",
                    "description": f"{SENSOR_NAMES[sensor]} averages {abs(diff):.1f} {'higher' if diff > 0 else 'lower'} on {higher}",
                    "icon": "🔄",
                    "data": {"sensor": sensor, "diff": diff}
                })

        return insights

    def _generate_anomaly_insights(self, time_range):
        """Recent anomalies"""
        insights = []

        anomalies = self.detect_anomalies('all', threshold=2.5, time_range=time_range)

        if anomalies['total_count'] > 0:
            most_recent = anomalies['anomalies'][0]

            insights.append({
                "category": "anomaly",
                "priority": "high",
                "title": f"Unusual {SENSOR_NAMES[most_recent['sensor']]} detected",
                "description": f"Detected {most_recent['severity']} anomaly on {most_recent['timestamp']}: {most_recent['value']} ({abs(most_recent['z_score']):.1f}σ from normal)",
                "icon": "⚠️",
                "data": most_recent
            })

        return insights

    def _generate_milestone_insights(self):
        """Fun milestones"""
        insights = []

        # Total data points
        df = self.load_data(None)
        total_points = len(df)

        if total_points > 500000:
            insights.append({
                "category": "milestone",
                "priority": "low",
                "title": "Half a million data points!",
                "description": f"You've collected {total_points:,} environmental measurements",
                "icon": "🎉",
                "data": {"total_points": total_points}
            })

        # Monitoring duration
        first_timestamp = df['gw_timestamp'].min()
        days_monitored = (datetime.now() - first_timestamp).days

        if days_monitored >= 180:
            insights.append({
                "category": "milestone",
                "priority": "low",
                "title": "6 months of monitoring!",
                "description": f"You've been monitoring for {days_monitored} days straight",
                "icon": "📅",
                "data": {"days": days_monitored}
            })

        return insights
```

### Frontend Display (js/analysis.js)
```javascript
async function loadAutoInsights() {
    const insights = await window.pywebview.api.get_auto_insights('7d');

    const container = document.getElementById('insights-container');
    container.innerHTML = '';

    insights.insights.forEach(insight => {
        const card = document.createElement('div');
        card.className = `insight-card priority-${insight.priority}`;

        card.innerHTML = `
            <div class="insight-icon">${insight.icon}</div>
            <div class="insight-content">
                <h4>${insight.title}</h4>
                <p>${insight.description}</p>
            </div>
        `;

        container.appendChild(card);
    });
}
```

---

## Success Criteria

- [ ] Generates 5-10 meaningful insights automatically
- [ ] Insights are in natural language
- [ ] Covers multiple categories (trends, patterns, anomalies)
- [ ] Updates based on new data
- [ ] Visually appealing presentation
- [ ] No "obvious" or redundant insights

---

## Notes

Auto-insights transform data into stories. Make them feel personalized and actionable. Consider adding "dismiss" functionality so users don't see the same insight repeatedly.
