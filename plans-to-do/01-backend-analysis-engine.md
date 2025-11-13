# Implementation Plan: Backend Analysis Engine

**Priority:** CRITICAL - Foundation
**Phase:** 1
**Estimated Effort:** 4-6 hours
**Dependencies:** None
**Blocks:** All other analysis features

---

## Overview

Create a centralized Python analysis engine that processes the 6+ months of CSV sensor data to compute statistics, detect patterns, and generate insights. This engine will serve as the backend foundation for all analysis features.

---

## Goals & Objectives

1. **Centralized Analysis Logic**: Single source of truth for all data computations
2. **Performance**: Handle 500K+ data points efficiently with caching
3. **Extensibility**: Easy to add new analysis methods
4. **Zero Impact**: Don't modify existing serial/logging functionality
5. **Testability**: Pure functions that can be unit tested

---

## Architecture

### File Structure
```
/
├── gateway_webview.py (existing - minimal changes)
├── analysis_engine.py (NEW)
├── analysis_utils.py (NEW - helper functions)
└── plans-to-do/ (this directory)
```

### Class Design

```python
# analysis_engine.py
class AnalysisEngine:
    """
    Central engine for analyzing historical sensor data.
    All methods are stateless and operate on CSV data.
    """

    def __init__(self, csv_filepath):
        self.csv_filepath = csv_filepath
        self._cache = {}  # Simple in-memory cache

    # Core loading
    def load_data(self, time_range_filter=None, sensors=None):
        """Load CSV data with optional filtering"""
        pass

    # Statistical analysis
    def compute_statistics(self, sensor, time_range=None):
        """Calculate min, max, mean, median, std dev, percentiles"""
        pass

    def compute_daily_aggregates(self, sensor, date):
        """Aggregate by hour for a specific day"""
        pass

    def compute_weekly_pattern(self, sensor, weeks_back=4):
        """Hour x Day of week pattern (168 data points)"""
        pass

    # Correlation analysis
    def compute_correlation_matrix(self, time_range=None):
        """Pearson correlation between all sensors"""
        pass

    def compute_scatter_data(self, sensor_x, sensor_y, time_range=None):
        """Scatter plot data for two sensors"""
        pass

    # Anomaly detection
    def detect_anomalies(self, sensor, threshold_stdev=2.5, time_range=None):
        """Find outliers using z-score method"""
        pass

    # Comparison
    def compare_periods(self, period1, period2):
        """Compare statistics between two time ranges"""
        pass

    # Helper methods
    def _parse_time_range(self, time_range):
        """Convert time_range string to datetime objects"""
        pass

    def _filter_by_time(self, df, start_dt, end_dt):
        """Filter dataframe by datetime range"""
        pass
```

---

## Integration Points

### 1. Import into gateway_webview.py

```python
# At top of gateway_webview.py
from analysis_engine import AnalysisEngine

# Initialize in main or at module level
analysis_engine = AnalysisEngine(csv_filepath=get_csv_path())
```

### 2. Expose via API class

```python
class Api:
    # ... existing methods ...

    # NEW: Analysis endpoints
    def get_statistics(self, sensor, time_range=None):
        """Get statistical summary for a sensor"""
        return analysis_engine.compute_statistics(sensor, time_range)

    def get_correlation_matrix(self, time_range=None):
        """Get correlation matrix for all sensors"""
        return analysis_engine.compute_correlation_matrix(time_range)

    def get_daily_pattern(self, sensor, weeks_back=4):
        """Get hourly pattern across week"""
        return analysis_engine.compute_weekly_pattern(sensor, weeks_back)

    def get_anomalies(self, sensor, threshold=2.5, time_range=None):
        """Detect and return anomalous readings"""
        return analysis_engine.detect_anomalies(sensor, threshold, time_range)
```

---

## Technical Specifications

### Data Processing

**CSV Reading:**
- Use `pandas.read_csv()` for efficiency
- Parse `gw_timestamp` as datetime index
- Cache loaded DataFrames with timestamp-based invalidation

**Memory Management:**
- For large time ranges, consider downsampling
- Use iterators for very large datasets
- Implement configurable max_points limit

**Time Range Filters:**
Support these standard ranges:
- `"1h"` - Last hour
- `"6h"` - Last 6 hours
- `"24h"` - Last 24 hours
- `"7d"` - Last 7 days
- `"30d"` - Last 30 days
- `"all"` - All data
- Custom: `{"start": "2024-01-01T00:00:00", "end": "2024-01-31T23:59:59"}`

### Statistical Methods

**compute_statistics() return format:**
```python
{
    "sensor": "temperature_sht",
    "time_range": "24h",
    "count": 2880,
    "min": 68.5,
    "max": 76.2,
    "mean": 72.3,
    "median": 72.1,
    "std_dev": 1.8,
    "percentile_25": 71.0,
    "percentile_75": 73.5,
    "percentile_95": 75.0
}
```

**compute_correlation_matrix() return format:**
```python
{
    "matrix": [
        ["temperature_sht", "humidity", "pressure", "light", "sound_level"],
        [1.0, -0.65, 0.23, 0.41, 0.18],
        [-0.65, 1.0, -0.12, -0.32, -0.08],
        # ... etc
    ],
    "labels": ["temperature_sht", "humidity", "pressure", "light", "sound_level"]
}
```

**detect_anomalies() return format:**
```python
{
    "sensor": "temperature_sht",
    "threshold": 2.5,
    "anomalies": [
        {
            "timestamp": "2024-06-15T14:32:00",
            "value": 85.3,
            "z_score": 3.2,
            "deviation": "+12.1°F from mean"
        },
        # ... more anomalies
    ],
    "total_count": 47
}
```

---

## Implementation Steps

### Step 1: Create analysis_engine.py skeleton
```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

class AnalysisEngine:
    def __init__(self, csv_filepath):
        self.csv_filepath = Path(csv_filepath)
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes

    # Implement each method listed above
```

### Step 2: Implement data loading
- `load_data()` method with caching
- `_parse_time_range()` helper
- `_filter_by_time()` helper
- CSV parsing with proper datetime handling

### Step 3: Implement statistical methods
- `compute_statistics()` using pandas describe() + percentiles
- `compute_daily_aggregates()` using groupby
- `compute_weekly_pattern()` with hour-of-week binning

### Step 4: Implement correlation methods
- `compute_correlation_matrix()` using pandas corr()
- `compute_scatter_data()` with optional sampling

### Step 5: Implement anomaly detection
- `detect_anomalies()` using z-score method
- Consider using IQR method as alternative
- Return full anomaly records with context

### Step 6: Integrate into gateway_webview.py
- Import AnalysisEngine
- Initialize instance
- Add API methods to Api class
- Test with existing data

### Step 7: Create unit tests (optional but recommended)
```python
# test_analysis_engine.py
import unittest
from analysis_engine import AnalysisEngine

class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalysisEngine("test_data.csv")

    def test_compute_statistics(self):
        stats = self.engine.compute_statistics("temperature_sht", "24h")
        self.assertIn("mean", stats)
        self.assertIn("std_dev", stats)
```

---

## Success Criteria

✅ **Functional Requirements:**
- [ ] Can load CSV data with time range filtering
- [ ] Computes accurate statistics (validated against manual calculation)
- [ ] Correlation matrix produces expected values
- [ ] Anomaly detection identifies known outliers
- [ ] All methods return properly formatted JSON-serializable dicts

✅ **Performance Requirements:**
- [ ] Loads 30 days of data in < 1 second
- [ ] Statistics computation completes in < 500ms
- [ ] Caching reduces repeat queries to < 50ms
- [ ] Memory usage stays < 500MB for full dataset

✅ **Integration Requirements:**
- [ ] Successfully imports into gateway_webview.py
- [ ] API methods callable from JavaScript via pywebview
- [ ] No impact on existing serial/logging functionality
- [ ] No errors in application logs

---

## Testing Strategy

**Manual Testing:**
1. Create test CSV with known patterns
2. Verify statistics match Excel calculations
3. Test each time range filter
4. Confirm anomaly detection finds seeded outliers

**Integration Testing:**
1. Start gateway_webview.py with analysis_engine imported
2. Call API methods from browser console
3. Verify JSON responses
4. Check for memory leaks with large queries

**Performance Testing:**
1. Load full 6-month dataset
2. Time each analysis method
3. Monitor memory usage
4. Test cache effectiveness

---

## Error Handling

**CSV File Issues:**
```python
def load_data(self, time_range_filter=None):
    if not self.csv_filepath.exists():
        return {"error": "CSV file not found", "data": []}

    try:
        df = pd.read_csv(self.csv_filepath, parse_dates=['gw_timestamp'])
    except Exception as e:
        return {"error": f"Failed to read CSV: {str(e)}", "data": []}
```

**Invalid Sensor Names:**
```python
VALID_SENSORS = [
    "temperature_sht", "humidity", "pressure",
    "light", "sound_level", "color_hex"
]

def compute_statistics(self, sensor, time_range=None):
    if sensor not in VALID_SENSORS:
        return {"error": f"Invalid sensor: {sensor}"}
```

**Empty Data:**
```python
if df.empty:
    return {
        "sensor": sensor,
        "time_range": time_range,
        "error": "No data found for this time range"
    }
```

---

## Dependencies

**Required Python Packages:**
```python
# Add to requirements.txt
pandas>=2.0.0
numpy>=1.24.0
```

**Install:**
```bash
pip install pandas numpy
```

---

## Code Review Checklist

Before marking this task complete:
- [ ] All methods have docstrings
- [ ] Error handling implemented for edge cases
- [ ] Returns JSON-serializable data structures
- [ ] Cache invalidation logic tested
- [ ] No hardcoded file paths
- [ ] Logging added for debugging
- [ ] Works with existing CSV format
- [ ] Doesn't modify gateway_webview.py's serial logic
- [ ] API methods tested via pywebview bridge

---

## Future Enhancements

**Post-MVP:**
- Add moving average smoothing
- Implement seasonal decomposition
- Support custom aggregation functions
- Add data quality metrics (missing data %, drift detection)
- Implement persistent caching with SQLite
- Add export to JSON/Parquet formats

---

## Notes for Implementation Agent

**Key Considerations:**
1. **Don't break existing code**: Import analysis_engine, don't modify core serial logic
2. **Think about scale**: 500K rows is large; use pandas efficiently
3. **JSON serialization**: Ensure datetime objects converted to strings
4. **Pandas datatypes**: Be explicit about datetime parsing
5. **Cache wisely**: Balance memory vs. recomputation

**Common Pitfalls:**
- Forgetting to convert numpy types to Python types for JSON
- Not handling missing data (NaN values)
- Loading entire CSV when only recent data needed
- Inefficient groupby operations on large datasets

**Quick Start:**
```python
# Minimal working version to start with
import pandas as pd

class AnalysisEngine:
    def __init__(self, csv_filepath):
        self.csv_filepath = csv_filepath

    def compute_statistics(self, sensor, time_range=None):
        df = pd.read_csv(self.csv_filepath, parse_dates=['gw_timestamp'])
        if time_range:
            # Apply filtering
            pass

        series = df[sensor]
        return {
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
            "std_dev": float(series.std())
        }
```

Then expand from there!

---

**Questions? Unclear requirements?** Document assumptions and proceed with best judgment. This is a foundational piece - focus on correctness over performance initially.
