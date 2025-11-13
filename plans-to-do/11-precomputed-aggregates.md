# Implementation Plan: Precomputed Aggregates & Caching

**Priority:** LOW (Performance Optimization)
**Phase:** 3
**Estimated Effort:** 4-5 hours
**Dependencies:** 01-backend-analysis-engine

---

## Overview

With 500K+ data points, repeatedly computing statistics becomes slow. This plan implements a background aggregation system that precomputes daily/hourly summaries, dramatically improving query performance for analysis features.

---

## Goals

1. **Performance**: Reduce query time from seconds to milliseconds
2. **Background Processing**: Compute aggregates without blocking UI
3. **Incremental Updates**: Only recompute new data
4. **Storage Efficiency**: Use SQLite for fast lookups
5. **Transparent**: Existing code works without changes

---

## Architecture

### Data Flow
```
Raw CSV (500K+ rows)
    ↓
Background Aggregator (runs on app start + periodically)
    ↓
SQLite Database
    ├─ hourly_aggregates (sensor, hour, avg, min, max, std, count)
    ├─ daily_aggregates (sensor, date, avg, min, max, std, count)
    └─ monthly_aggregates (sensor, month, avg, min, max, std, count)
    ↓
Analysis Engine (queries aggregates instead of raw CSV)
    ↓
Fast response to UI
```

---

## Implementation

### 1. Create Aggregates Database Schema
```sql
-- aggregates.db

CREATE TABLE hourly_aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO format, hour precision
    avg REAL,
    min REAL,
    max REAL,
    std REAL,
    count INTEGER,
    UNIQUE(sensor, timestamp)
);

CREATE INDEX idx_hourly_sensor_time ON hourly_aggregates(sensor, timestamp);

CREATE TABLE daily_aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor TEXT NOT NULL,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    avg REAL,
    min REAL,
    max REAL,
    std REAL,
    count INTEGER,
    UNIQUE(sensor, date)
);

CREATE INDEX idx_daily_sensor_date ON daily_aggregates(sensor, date);

CREATE TABLE aggregation_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### 2. Background Aggregator (aggregator.py)
```python
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class DataAggregator:
    """Precompute and cache data aggregates"""

    def __init__(self, csv_filepath, db_filepath='aggregates.db'):
        self.csv_filepath = csv_filepath
        self.db_filepath = db_filepath
        self.conn = sqlite3.connect(db_filepath)
        self._create_tables()

    def _create_tables(self):
        """Create aggregate tables if they don't exist"""
        # Execute schema SQL
        pass

    def compute_all_aggregates(self):
        """Compute aggregates for all data (initial run)"""
        print("Computing aggregates for all historical data...")

        # Read CSV
        df = pd.read_csv(self.csv_filepath, parse_dates=['gw_timestamp'])

        sensors = ['temperature_sht', 'humidity', 'pressure', 'light', 'sound_level']

        for sensor in sensors:
            print(f"  Aggregating {sensor}...")

            # Hourly aggregates
            self._compute_hourly_aggregates(df, sensor)

            # Daily aggregates
            self._compute_daily_aggregates(df, sensor)

        # Update metadata
        self._set_metadata('last_aggregation', datetime.now().isoformat())

        print("Aggregation complete!")

    def _compute_hourly_aggregates(self, df, sensor):
        """Compute and store hourly aggregates"""
        df['hour'] = df['gw_timestamp'].dt.floor('H')

        hourly = df.groupby('hour')[sensor].agg([
            ('avg', 'mean'),
            ('min', 'min'),
            ('max', 'max'),
            ('std', 'std'),
            ('count', 'count')
        ]).reset_index()

        # Insert into database
        for _, row in hourly.iterrows():
            self.conn.execute('''
                INSERT OR REPLACE INTO hourly_aggregates
                (sensor, timestamp, avg, min, max, std, count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sensor,
                row['hour'].isoformat(),
                float(row['avg']),
                float(row['min']),
                float(row['max']),
                float(row['std']),
                int(row['count'])
            ))

        self.conn.commit()

    def _compute_daily_aggregates(self, df, sensor):
        """Compute and store daily aggregates"""
        df['date'] = df['gw_timestamp'].dt.date

        daily = df.groupby('date')[sensor].agg([
            ('avg', 'mean'),
            ('min', 'min'),
            ('max', 'max'),
            ('std', 'std'),
            ('count', 'count')
        ]).reset_index()

        # Insert into database
        for _, row in daily.iterrows():
            self.conn.execute('''
                INSERT OR REPLACE INTO daily_aggregates
                (sensor, date, avg, min, max, std, count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sensor,
                row['date'].isoformat(),
                float(row['avg']),
                float(row['min']),
                float(row['max']),
                float(row['std']),
                int(row['count'])
            ))

        self.conn.commit()

    def update_recent_aggregates(self, hours=24):
        """Update aggregates for recent data only (incremental)"""
        # Read only last N hours from CSV
        # Recompute aggregates for affected hours/days
        pass

    def _set_metadata(self, key, value):
        """Store metadata"""
        self.conn.execute('''
            INSERT OR REPLACE INTO aggregation_metadata (key, value)
            VALUES (?, ?)
        ''', (key, value))
        self.conn.commit()

    def _get_metadata(self, key):
        """Retrieve metadata"""
        cursor = self.conn.execute(
            'SELECT value FROM aggregation_metadata WHERE key = ?',
            (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
```

### 3. Modify Analysis Engine to Use Aggregates
```python
class AnalysisEngine:
    def __init__(self, csv_filepath):
        self.csv_filepath = csv_filepath
        self.aggregator = DataAggregator(csv_filepath)

        # Check if aggregates exist
        if not self.aggregator._get_metadata('last_aggregation'):
            print("First run - computing aggregates...")
            self.aggregator.compute_all_aggregates()

    def compute_statistics(self, sensor, time_range=None):
        """Use precomputed aggregates when possible"""

        # For queries spanning days/weeks, use daily aggregates
        if self._should_use_daily_aggregates(time_range):
            return self._compute_stats_from_daily_aggregates(sensor, time_range)

        # For hourly detail, use hourly aggregates
        elif self._should_use_hourly_aggregates(time_range):
            return self._compute_stats_from_hourly_aggregates(sensor, time_range)

        # For very recent data or small ranges, use raw CSV
        else:
            return self._compute_stats_from_csv(sensor, time_range)

    def _compute_stats_from_daily_aggregates(self, sensor, time_range):
        """Fast stats using daily aggregates"""
        conn = self.aggregator.conn

        start_date, end_date = self._parse_time_range(time_range)

        cursor = conn.execute('''
            SELECT
                AVG(avg) as mean,
                MIN(min) as min,
                MAX(max) as max,
                SUM(count) as count
            FROM daily_aggregates
            WHERE sensor = ? AND date >= ? AND date <= ?
        ''', (sensor, start_date, end_date))

        row = cursor.fetchone()

        return {
            "sensor": sensor,
            "time_range": time_range,
            "mean": row[0],
            "min": row[1],
            "max": row[2],
            "count": row[3]
            # Note: Some stats like median require raw data
        }
```

### 4. Background Thread in Main App (gateway_webview.py)
```python
import threading
import time

def aggregation_worker():
    """Background thread to keep aggregates updated"""
    aggregator = DataAggregator(csv_filepath)

    while True:
        time.sleep(3600)  # Run every hour

        try:
            # Update aggregates for recent data
            aggregator.update_recent_aggregates(hours=24)
            print(f"[{datetime.now()}] Aggregates updated")
        except Exception as e:
            print(f"Aggregation error: {e}")

# Start background worker on app launch
threading.Thread(target=aggregation_worker, daemon=True).start()
```

---

## Success Criteria

- [ ] Initial aggregation completes in < 2 minutes for 500K rows
- [ ] Queries using aggregates return in < 100ms
- [ ] Incremental updates work correctly
- [ ] Database size stays < 50MB
- [ ] No breaking changes to existing analysis functions
- [ ] Background worker doesn't impact UI performance

---

## Performance Gains

**Before:**
- Statistics query (30 days): ~2-5 seconds
- Calendar view (1 month): ~8-15 seconds

**After:**
- Statistics query (30 days): ~50-100ms (20-50x faster)
- Calendar view (1 month): ~200ms (40x faster)

---

## Notes

This is the most impactful performance optimization. Implement this if users experience slowness with large datasets. Can be added later without breaking existing features.
