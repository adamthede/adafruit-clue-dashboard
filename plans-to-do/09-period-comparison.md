# Implementation Plan: Multi-Period Comparison Tool

**Priority:** MEDIUM
**Phase:** 3
**Estimated Effort:** 4-5 hours
**Dependencies:** 01-backend-analysis-engine, 02-tabbed-ui-architecture

---

## Overview

Enable users to compare sensor data across two different time periods (e.g., "This week vs. last week" or "June vs. July"). This reveals how environmental conditions have changed over time and helps identify trends, improvements, or degradations.

---

## Goals

1. **Side-by-Side Comparison**: View two periods simultaneously
2. **Statistical Diff**: Show % change, absolute differences
3. **Visual Overlay**: Overlay charts for direct comparison
4. **Common Use Cases**: "Compare to same time last month/year"
5. **Insights Generation**: Auto-identify biggest changes

---

## Key Features

### Comparison Interface
```
Period 1: [Last 7 Days ▼]  vs  Period 2: [Previous 7 Days ▼]
Sensor: [Temperature ▼]  [Compare]

Results:
┌────────────────┬─────────────┬─────────────┬───────────┐
│ Metric         │ Period 1    │ Period 2    │ Change    │
├────────────────┼─────────────┼─────────────┼───────────┤
│ Average        │ 72.3°F      │ 69.8°F      │ +2.5°F ↑  │
│ Min            │ 68.5°F      │ 65.2°F      │ +3.3°F    │
│ Max            │ 76.2°F      │ 74.1°F      │ +2.1°F    │
│ Std Dev        │ 1.8°F       │ 2.3°F       │ -0.5°F    │
└────────────────┴─────────────┴─────────────┴───────────┘

Overlay Chart: Shows both periods on same axis
```

---

## Implementation

### Backend (analysis_engine.py)
```python
def compare_periods(self, sensor, period1_range, period2_range):
    """
    Compare statistics between two time periods

    Returns:
        {
            "period1": {...stats...},
            "period2": {...stats...},
            "differences": {
                "mean_diff": X,
                "mean_diff_percent": Y,
                ...
            },
            "period1_data": [...data points...],
            "period2_data": [...data points...]
        }
    """
    # Load data for both periods
    df1 = self.load_data(period1_range, sensors=[sensor])
    df2 = self.load_data(period2_range, sensors=[sensor])

    # Compute stats
    stats1 = self._compute_period_stats(df1, sensor)
    stats2 = self._compute_period_stats(df2, sensor)

    # Calculate differences
    differences = {
        "mean_diff": stats1["mean"] - stats2["mean"],
        "mean_diff_percent": ((stats1["mean"] - stats2["mean"]) / stats2["mean"] * 100),
        "min_diff": stats1["min"] - stats2["min"],
        "max_diff": stats1["max"] - stats2["max"],
        "std_diff": stats1["std"] - stats2["std"]
    }

    return {
        "period1": stats1,
        "period2": stats2,
        "differences": differences,
        "period1_data": df1[[sensor, 'gw_timestamp']].to_dict('records'),
        "period2_data": df2[[sensor, 'gw_timestamp']].to_dict('records')
    }
```

### Frontend (js/analysis.js)
```javascript
async function comparePeriodsfunction() {
    const sensor = document.getElementById('compare-sensor').value;
    const period1 = document.getElementById('compare-period1').value;
    const period2 = document.getElementById('compare-period2').value;

    const data = await window.pywebview.api.compare_periods(sensor, period1, period2);

    renderComparisonTable(data);
    renderComparisonChart(data);
    generateComparisonInsights(data);
}

function renderComparisonChart(data) {
    // Overlay line chart with two series
    // Use Chart.js with different colors for each period
}
```

---

## Success Criteria

- [ ] Can select any two arbitrary time periods
- [ ] Statistical comparison table shows meaningful differences
- [ ] Overlay chart renders both periods clearly
- [ ] Insights auto-generate biggest changes
- [ ] Percentage changes calculated correctly
- [ ] UI is intuitive for selecting periods

---

## Quick Implementation Notes

- Reuse existing time range parsing logic
- Consider caching period stats to avoid recomputation
- Add "quick compare" presets: "This week vs last week", "This month vs last month"
- Highlight significant changes (>20% difference) in red/green
