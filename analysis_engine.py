"""
Analysis Engine for Adafruit CLUE Environmental Sensor Data

This module provides centralized analysis capabilities for processing historical
sensor data from CSV files. It computes statistics, detects patterns, identifies
anomalies, and generates insights for the dashboard.

Key Features:
- Statistical analysis (min, max, mean, median, std dev, percentiles)
- Time-based aggregations (daily, weekly patterns)
- Correlation analysis between sensors
- Anomaly detection using z-score method
- Flexible time range filtering
- Efficient caching for performance

Author: Analysis Engine Implementation
Date: 2024
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union


class AnalysisEngine:
    """
    Central engine for analyzing historical sensor data.
    All methods are stateless and operate on CSV data.
    """

    # Valid sensor names
    VALID_SENSORS = [
        "temperature_sht",
        "humidity",
        "pressure",
        "light",
        "sound_level",
        "color_hex"
    ]

    # Time range filter presets (in seconds for easy calculation)
    TIME_RANGES = {
        "1h": 3600,
        "6h": 6 * 3600,
        "24h": 24 * 3600,
        "7d": 7 * 24 * 3600,
        "30d": 30 * 24 * 3600,
        "all": None  # Special case for all data
    }

    def __init__(self, csv_filepath: Union[str, Path]):
        """
        Initialize the Analysis Engine.

        Args:
            csv_filepath: Path to the CSV file containing sensor data
        """
        self.csv_filepath = Path(csv_filepath)
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes cache timeout
        self._cache_timestamps = {}

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"AnalysisEngine initialized with CSV: {self.csv_filepath}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data is still valid based on timeout.

        Args:
            cache_key: Key to check in cache

        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self._cache_timestamps:
            return False

        age = time.time() - self._cache_timestamps[cache_key]
        return age < self._cache_timeout

    def _set_cache(self, cache_key: str, data: Any) -> None:
        """
        Store data in cache with timestamp.

        Args:
            cache_key: Key to store data under
            data: Data to cache
        """
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()

    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve data from cache if valid.

        Args:
            cache_key: Key to retrieve

        Returns:
            Cached data or None if not found/invalid
        """
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Cache hit for key: {cache_key}")
            return self._cache[cache_key]

        # Remove stale cache
        if cache_key in self._cache:
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]

        return None

    def _parse_time_range(self, time_range: Optional[Union[str, Dict]]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Convert time_range parameter to datetime objects.

        Args:
            time_range: Time range specification. Can be:
                - String preset: "1h", "6h", "24h", "7d", "30d", "all"
                - Dict with 'start' and 'end' ISO timestamps
                - None for all data

        Returns:
            Tuple of (start_datetime, end_datetime). Either can be None for unbounded.
        """
        if time_range is None or time_range == "all":
            return None, None

        now = datetime.now(timezone.utc)

        # Handle string presets
        if isinstance(time_range, str):
            if time_range in self.TIME_RANGES:
                seconds = self.TIME_RANGES[time_range]
                if seconds is None:
                    return None, None
                start_dt = now - timedelta(seconds=seconds)
                return start_dt, now
            else:
                self.logger.warning(f"Unknown time range preset: {time_range}, using 1h")
                start_dt = now - timedelta(hours=1)
                return start_dt, now

        # Handle custom dict with start/end
        if isinstance(time_range, dict):
            start_str = time_range.get('start')
            end_str = time_range.get('end')

            start_dt = None
            end_dt = None

            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    self.logger.error(f"Invalid start datetime: {start_str}, {e}")

            if end_str:
                try:
                    end_dt = datetime.fromisoformat(end_str)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    self.logger.error(f"Invalid end datetime: {end_str}, {e}")

            return start_dt, end_dt

        # Default fallback
        return None, None

    def _filter_by_time(self, df: pd.DataFrame, start_dt: Optional[datetime],
                       end_dt: Optional[datetime]) -> pd.DataFrame:
        """
        Filter dataframe by datetime range.

        Args:
            df: DataFrame with 'gw_timestamp' datetime index
            start_dt: Start datetime (inclusive), None for no lower bound
            end_dt: End datetime (inclusive), None for no upper bound

        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df

        filtered_df = df

        if start_dt is not None:
            filtered_df = filtered_df[filtered_df['gw_timestamp'] >= start_dt]

        if end_dt is not None:
            filtered_df = filtered_df[filtered_df['gw_timestamp'] <= end_dt]

        return filtered_df

    def load_data(self, time_range_filter: Optional[Union[str, Dict]] = None,
                  sensors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load CSV data with optional filtering.

        Args:
            time_range_filter: Time range specification
            sensors: List of sensor names to load. None loads all sensors.

        Returns:
            Dict with 'data' (DataFrame) and 'error' (if any)
        """
        # Check if file exists
        if not self.csv_filepath.exists():
            error_msg = f"CSV file not found: {self.csv_filepath}"
            self.logger.error(error_msg)
            return {"error": error_msg, "data": pd.DataFrame()}

        # Create cache key
        cache_key = f"load_data_{time_range_filter}_{sensors}"
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return {"data": cached_data}

        try:
            # Read CSV with datetime parsing
            df = pd.read_csv(
                self.csv_filepath,
                parse_dates=['gw_timestamp']
            )

            # Ensure timezone aware
            if df['gw_timestamp'].dt.tz is None:
                df['gw_timestamp'] = pd.to_datetime(df['gw_timestamp'], utc=True)

            self.logger.info(f"Loaded {len(df)} records from CSV")

            # Apply time filtering
            if time_range_filter:
                start_dt, end_dt = self._parse_time_range(time_range_filter)
                df = self._filter_by_time(df, start_dt, end_dt)
                self.logger.info(f"Filtered to {len(df)} records for range {time_range_filter}")

            # Apply sensor filtering
            if sensors:
                # Keep timestamp and only requested sensors
                cols_to_keep = ['gw_timestamp'] + [s for s in sensors if s in df.columns]
                df = df[cols_to_keep]

            # Cache the result
            self._set_cache(cache_key, df)

            return {"data": df}

        except Exception as e:
            error_msg = f"Failed to read CSV: {str(e)}"
            self.logger.exception(error_msg)
            return {"error": error_msg, "data": pd.DataFrame()}

    def compute_statistics(self, sensor: str, time_range: Optional[Union[str, Dict]] = None) -> Dict[str, Any]:
        """
        Calculate statistical summary for a sensor.

        Args:
            sensor: Name of the sensor
            time_range: Optional time range filter

        Returns:
            Dict with statistics (min, max, mean, median, std_dev, percentiles, count)
        """
        # Validate sensor name
        if sensor not in self.VALID_SENSORS:
            error_msg = f"Invalid sensor: {sensor}. Valid sensors: {self.VALID_SENSORS}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Load data
        result = self.load_data(time_range_filter=time_range, sensors=[sensor])
        if "error" in result:
            return result

        df = result["data"]

        # Check if we have data
        if df.empty or sensor not in df.columns:
            return {
                "sensor": sensor,
                "time_range": str(time_range),
                "error": "No data found for this sensor and time range"
            }

        # Get sensor series and drop NaN values
        series = df[sensor].dropna()

        if len(series) == 0:
            return {
                "sensor": sensor,
                "time_range": str(time_range),
                "error": "No valid data points (all NaN)"
            }

        # Compute statistics
        try:
            stats = {
                "sensor": sensor,
                "time_range": str(time_range),
                "count": int(len(series)),
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std_dev": float(series.std()),
                "percentile_25": float(series.quantile(0.25)),
                "percentile_75": float(series.quantile(0.75)),
                "percentile_95": float(series.quantile(0.95))
            }

            self.logger.info(f"Computed statistics for {sensor}: count={stats['count']}, mean={stats['mean']:.2f}")
            return stats

        except Exception as e:
            error_msg = f"Error computing statistics: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "sensor": sensor,
                "time_range": str(time_range),
                "error": error_msg
            }

    def compute_daily_aggregates(self, sensor: str, date: Union[str, datetime]) -> Dict[str, Any]:
        """
        Aggregate sensor data by hour for a specific day.

        Args:
            sensor: Name of the sensor
            date: Date as ISO string or datetime object

        Returns:
            Dict with hourly aggregates (24 data points)
        """
        # Validate sensor
        if sensor not in self.VALID_SENSORS:
            return {"error": f"Invalid sensor: {sensor}"}

        # Parse date
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except ValueError:
                return {"error": f"Invalid date format: {date}"}

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        # Create time range for the entire day
        start_dt = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=1)

        # Load data for the day
        result = self.load_data(
            time_range_filter={"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            sensors=[sensor]
        )

        if "error" in result:
            return result

        df = result["data"]

        if df.empty:
            return {
                "sensor": sensor,
                "date": date.isoformat(),
                "error": "No data found for this date"
            }

        # Extract hour and group by it
        df['hour'] = df['gw_timestamp'].dt.hour
        hourly = df.groupby('hour')[sensor].agg(['mean', 'min', 'max', 'count']).reset_index()

        # Convert to list of dicts for JSON serialization
        aggregates = []
        for _, row in hourly.iterrows():
            aggregates.append({
                "hour": int(row['hour']),
                "mean": float(row['mean']) if not pd.isna(row['mean']) else None,
                "min": float(row['min']) if not pd.isna(row['min']) else None,
                "max": float(row['max']) if not pd.isna(row['max']) else None,
                "count": int(row['count'])
            })

        return {
            "sensor": sensor,
            "date": date.date().isoformat(),
            "aggregates": aggregates
        }

    def compute_weekly_pattern(self, sensor: str, weeks_back: int = 4) -> Dict[str, Any]:
        """
        Compute hour x day of week pattern (168 data points).

        Args:
            sensor: Name of the sensor
            weeks_back: Number of weeks to look back (default: 4)

        Returns:
            Dict with weekly pattern data
        """
        # Validate sensor
        if sensor not in self.VALID_SENSORS:
            return {"error": f"Invalid sensor: {sensor}"}

        # Calculate time range
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(weeks=weeks_back)

        # Load data
        result = self.load_data(
            time_range_filter={"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            sensors=[sensor]
        )

        if "error" in result:
            return result

        df = result["data"]

        if df.empty:
            return {
                "sensor": sensor,
                "weeks_back": weeks_back,
                "error": "No data found for this time range"
            }

        # Extract day of week (0=Monday) and hour
        df['day_of_week'] = df['gw_timestamp'].dt.dayofweek
        df['hour'] = df['gw_timestamp'].dt.hour

        # Group by day and hour
        pattern = df.groupby(['day_of_week', 'hour'])[sensor].mean().reset_index()

        # Create 168-point array (7 days * 24 hours)
        weekly_data = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for day in range(7):
            for hour in range(24):
                # Find matching data point
                matches = pattern[(pattern['day_of_week'] == day) & (pattern['hour'] == hour)]
                value = float(matches[sensor].iloc[0]) if len(matches) > 0 else None

                weekly_data.append({
                    "day": day_names[day],
                    "day_num": day,
                    "hour": hour,
                    "value": value
                })

        return {
            "sensor": sensor,
            "weeks_back": weeks_back,
            "pattern": weekly_data
        }

    def compute_correlation_matrix(self, time_range: Optional[Union[str, Dict]] = None) -> Dict[str, Any]:
        """
        Calculate Pearson correlation between all sensors.

        Args:
            time_range: Optional time range filter

        Returns:
            Dict with correlation matrix and labels
        """
        # Load all sensor data
        numeric_sensors = [s for s in self.VALID_SENSORS if s != "color_hex"]

        result = self.load_data(time_range_filter=time_range, sensors=numeric_sensors)
        if "error" in result:
            return result

        df = result["data"]

        if df.empty:
            return {
                "time_range": str(time_range),
                "error": "No data found for this time range"
            }

        # Select only numeric columns
        numeric_df = df[numeric_sensors].select_dtypes(include=[np.number])

        if numeric_df.empty:
            return {
                "time_range": str(time_range),
                "error": "No numeric data available"
            }

        # Compute correlation matrix
        corr_matrix = numeric_df.corr()

        # Convert to list format for JSON
        labels = list(corr_matrix.columns)

        # Convert matrix values to list, handling NaN
        matrix_values = []
        for row in corr_matrix.values:
            matrix_values.append([float(v) if not pd.isna(v) else None for v in row])

        # Combine labels header with matrix values
        matrix_data_clean = [labels] + matrix_values

        return {
            "time_range": str(time_range),
            "matrix": matrix_data_clean,
            "labels": labels
        }

    def compute_scatter_data(self, sensor_x: str, sensor_y: str,
                            time_range: Optional[Union[str, Dict]] = None,
                            max_points: int = 1000) -> Dict[str, Any]:
        """
        Get scatter plot data for two sensors.

        Args:
            sensor_x: X-axis sensor
            sensor_y: Y-axis sensor
            time_range: Optional time range filter
            max_points: Maximum number of points to return (for performance)

        Returns:
            Dict with scatter plot data
        """
        # Validate sensors
        if sensor_x not in self.VALID_SENSORS:
            return {"error": f"Invalid sensor_x: {sensor_x}"}
        if sensor_y not in self.VALID_SENSORS:
            return {"error": f"Invalid sensor_y: {sensor_y}"}

        # Load data
        result = self.load_data(time_range_filter=time_range, sensors=[sensor_x, sensor_y])
        if "error" in result:
            return result

        df = result["data"]

        if df.empty:
            return {
                "sensor_x": sensor_x,
                "sensor_y": sensor_y,
                "time_range": str(time_range),
                "error": "No data found"
            }

        # Drop rows with NaN in either sensor
        clean_df = df[[sensor_x, sensor_y]].dropna()

        if clean_df.empty:
            return {
                "sensor_x": sensor_x,
                "sensor_y": sensor_y,
                "error": "No valid data points"
            }

        # Sample if too many points
        if len(clean_df) > max_points:
            clean_df = clean_df.sample(n=max_points, random_state=42)
            self.logger.info(f"Sampled {max_points} points from {len(df)} for scatter plot")

        # Create scatter data
        scatter_points = [
            {
                "x": float(row[sensor_x]),
                "y": float(row[sensor_y])
            }
            for _, row in clean_df.iterrows()
        ]

        return {
            "sensor_x": sensor_x,
            "sensor_y": sensor_y,
            "time_range": str(time_range),
            "count": len(scatter_points),
            "points": scatter_points
        }

    def detect_anomalies(self, sensor: str, threshold_stdev: float = 2.5,
                        time_range: Optional[Union[str, Dict]] = None) -> Dict[str, Any]:
        """
        Find outliers using z-score method.

        Args:
            sensor: Name of the sensor
            threshold_stdev: Number of standard deviations for anomaly threshold
            time_range: Optional time range filter

        Returns:
            Dict with detected anomalies
        """
        # Validate sensor
        if sensor not in self.VALID_SENSORS:
            return {"error": f"Invalid sensor: {sensor}"}

        # Load data
        result = self.load_data(time_range_filter=time_range, sensors=[sensor])
        if "error" in result:
            return result

        df = result["data"]

        if df.empty:
            return {
                "sensor": sensor,
                "threshold": threshold_stdev,
                "time_range": str(time_range),
                "error": "No data found"
            }

        # Get clean data
        clean_df = df[['gw_timestamp', sensor]].dropna()

        if len(clean_df) < 3:
            return {
                "sensor": sensor,
                "threshold": threshold_stdev,
                "error": "Insufficient data for anomaly detection (need at least 3 points)"
            }

        # Calculate z-scores
        mean_val = clean_df[sensor].mean()
        std_val = clean_df[sensor].std()

        if std_val == 0:
            return {
                "sensor": sensor,
                "threshold": threshold_stdev,
                "error": "No variance in data (std dev = 0)"
            }

        clean_df['z_score'] = (clean_df[sensor] - mean_val) / std_val

        # Find anomalies
        anomalies_df = clean_df[abs(clean_df['z_score']) > threshold_stdev]

        # Format anomalies
        anomalies = []
        for _, row in anomalies_df.iterrows():
            deviation = row[sensor] - mean_val
            sign = "+" if deviation > 0 else ""

            anomalies.append({
                "timestamp": row['gw_timestamp'].isoformat(),
                "value": float(row[sensor]),
                "z_score": float(row['z_score']),
                "deviation": f"{sign}{deviation:.2f} from mean"
            })

        return {
            "sensor": sensor,
            "threshold": threshold_stdev,
            "time_range": str(time_range),
            "mean": float(mean_val),
            "std_dev": float(std_val),
            "total_count": len(anomalies),
            "anomalies": anomalies
        }

    def compare_periods(self, sensor: str, period1: Union[str, Dict],
                       period2: Union[str, Dict]) -> Dict[str, Any]:
        """
        Compare statistics between two time ranges.

        Args:
            sensor: Name of the sensor
            period1: First time period
            period2: Second time period

        Returns:
            Dict with comparison statistics
        """
        # Get statistics for both periods
        stats1 = self.compute_statistics(sensor, period1)
        stats2 = self.compute_statistics(sensor, period2)

        # Check for errors
        if "error" in stats1:
            return {"error": f"Period 1: {stats1['error']}"}
        if "error" in stats2:
            return {"error": f"Period 2: {stats2['error']}"}

        # Compute differences
        comparison = {
            "sensor": sensor,
            "period1": {
                "time_range": str(period1),
                "stats": stats1
            },
            "period2": {
                "time_range": str(period2),
                "stats": stats2
            },
            "differences": {
                "mean_diff": stats2["mean"] - stats1["mean"],
                "mean_pct_change": ((stats2["mean"] - stats1["mean"]) / stats1["mean"] * 100) if stats1["mean"] != 0 else None,
                "median_diff": stats2["median"] - stats1["median"],
                "std_dev_diff": stats2["std_dev"] - stats1["std_dev"],
                "count_diff": stats2["count"] - stats1["count"]
            }
        }

        return comparison

    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get overall summary of available data.

        Returns:
            Dict with data summary (date range, record count, sensors available)
        """
        result = self.load_data()
        if "error" in result:
            return result

        df = result["data"]

        if df.empty:
            return {"error": "No data available"}

        # Get date range
        min_date = df['gw_timestamp'].min()
        max_date = df['gw_timestamp'].max()
        total_records = len(df)

        # Count records per sensor
        sensor_counts = {}
        for sensor in self.VALID_SENSORS:
            if sensor in df.columns:
                sensor_counts[sensor] = int(df[sensor].notna().sum())

        return {
            "total_records": total_records,
            "date_range": {
                "start": min_date.isoformat() if pd.notna(min_date) else None,
                "end": max_date.isoformat() if pd.notna(max_date) else None,
                "days": (max_date - min_date).days if pd.notna(min_date) and pd.notna(max_date) else 0
            },
            "sensors": sensor_counts,
            "file_path": str(self.csv_filepath)
        }
