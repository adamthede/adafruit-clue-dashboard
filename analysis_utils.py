"""
Analysis Utilities for Adafruit CLUE Environmental Sensor Data

This module provides helper functions and utilities for data analysis,
visualization preparation, and data formatting.

Author: Analysis Engine Implementation
Date: 2024
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union


def format_timestamp(dt: datetime, format_type: str = "iso") -> str:
    """
    Format datetime object to string.

    Args:
        dt: Datetime object
        format_type: Type of format ('iso', 'short', 'long')

    Returns:
        Formatted string
    """
    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "short":
        return dt.strftime("%Y-%m-%d %H:%M")
    elif format_type == "long":
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        return str(dt)


def convert_celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9 / 5) + 32


def convert_fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    Convert temperature from Fahrenheit to Celsius.

    Args:
        fahrenheit: Temperature in Fahrenheit

    Returns:
        Temperature in Celsius
    """
    return (fahrenheit - 32) * 5 / 9


def calculate_heat_index(temperature_f: float, humidity: float) -> Optional[float]:
    """
    Calculate heat index (feels like temperature).

    Args:
        temperature_f: Temperature in Fahrenheit
        humidity: Relative humidity percentage (0-100)

    Returns:
        Heat index in Fahrenheit, or None if not applicable
    """
    # Heat index only meaningful for temp >= 80°F
    if temperature_f < 80:
        return None

    # Simplified heat index formula
    hi = (
        -42.379 +
        2.04901523 * temperature_f +
        10.14333127 * humidity -
        0.22475541 * temperature_f * humidity -
        6.83783e-3 * temperature_f ** 2 -
        5.481717e-2 * humidity ** 2 +
        1.22874e-3 * temperature_f ** 2 * humidity +
        8.5282e-4 * temperature_f * humidity ** 2 -
        1.99e-6 * temperature_f ** 2 * humidity ** 2
    )

    return round(hi, 2)


def calculate_dew_point(temperature_f: float, humidity: float) -> float:
    """
    Calculate dew point temperature.

    Args:
        temperature_f: Temperature in Fahrenheit
        humidity: Relative humidity percentage (0-100)

    Returns:
        Dew point in Fahrenheit
    """
    # Convert to Celsius for calculation
    temp_c = convert_fahrenheit_to_celsius(temperature_f)

    # Magnus formula coefficients
    a = 17.27
    b = 237.7

    alpha = ((a * temp_c) / (b + temp_c)) + np.log(humidity / 100.0)
    dew_point_c = (b * alpha) / (a - alpha)

    # Convert back to Fahrenheit
    return round(convert_celsius_to_fahrenheit(dew_point_c), 2)


def downsample_data(df: pd.DataFrame, max_points: int = 1000) -> pd.DataFrame:
    """
    Downsample dataframe to maximum number of points.

    Args:
        df: Input DataFrame
        max_points: Maximum number of points to keep

    Returns:
        Downsampled DataFrame
    """
    if len(df) <= max_points:
        return df

    # Use systematic sampling to keep temporal distribution
    step = len(df) // max_points
    return df.iloc[::step].head(max_points)


def fill_missing_data(series: pd.Series, method: str = "linear") -> pd.Series:
    """
    Fill missing data in a series.

    Args:
        series: Input series with potential NaN values
        method: Interpolation method ('linear', 'forward', 'backward')

    Returns:
        Series with filled values
    """
    if method == "linear":
        return series.interpolate(method='linear')
    elif method == "forward":
        return series.fillna(method='ffill')
    elif method == "backward":
        return series.fillna(method='bfill')
    else:
        return series


def detect_sensor_drift(series: pd.Series, window: int = 100) -> Dict[str, Any]:
    """
    Detect if sensor readings show drift over time.

    Args:
        series: Time series of sensor readings
        window: Window size for rolling statistics

    Returns:
        Dict with drift analysis
    """
    if len(series) < window * 2:
        return {"error": "Insufficient data for drift detection"}

    # Calculate rolling mean
    rolling_mean = series.rolling(window=window).mean()

    # Compare first and last window
    first_mean = rolling_mean.iloc[window - 1]
    last_mean = rolling_mean.iloc[-1]

    drift = last_mean - first_mean
    drift_pct = (drift / first_mean * 100) if first_mean != 0 else 0

    return {
        "drift": float(drift),
        "drift_percentage": float(drift_pct),
        "first_window_mean": float(first_mean),
        "last_window_mean": float(last_mean),
        "has_significant_drift": abs(drift_pct) > 5  # 5% threshold
    }


def calculate_moving_average(series: pd.Series, window: int = 10) -> pd.Series:
    """
    Calculate moving average of a series.

    Args:
        series: Input series
        window: Window size for moving average

    Returns:
        Series with moving average
    """
    return series.rolling(window=window, min_periods=1).mean()


def identify_outliers_iqr(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """
    Identify outliers using IQR (Interquartile Range) method.

    Args:
        series: Input series
        multiplier: IQR multiplier (default 1.5 for outliers, 3.0 for extreme outliers)

    Returns:
        Boolean series indicating outliers
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    return (series < lower_bound) | (series > upper_bound)


def bin_data_by_time(df: pd.DataFrame, freq: str = "H") -> pd.DataFrame:
    """
    Bin data by time frequency and aggregate.

    Args:
        df: DataFrame with datetime index or 'gw_timestamp' column
        freq: Frequency string ('H'=hour, 'D'=day, 'W'=week, 'M'=month)

    Returns:
        Binned DataFrame with mean values
    """
    if 'gw_timestamp' in df.columns:
        df_copy = df.copy()
        df_copy = df_copy.set_index('gw_timestamp')
    else:
        df_copy = df

    return df_copy.resample(freq).mean()


def calculate_sensor_correlation(df: pd.DataFrame, sensor1: str, sensor2: str) -> Optional[float]:
    """
    Calculate correlation between two sensors.

    Args:
        df: DataFrame containing sensor data
        sensor1: First sensor name
        sensor2: Second sensor name

    Returns:
        Pearson correlation coefficient or None if not possible
    """
    if sensor1 not in df.columns or sensor2 not in df.columns:
        return None

    clean_df = df[[sensor1, sensor2]].dropna()

    if len(clean_df) < 2:
        return None

    return float(clean_df[sensor1].corr(clean_df[sensor2]))


def get_time_of_day_category(hour: int) -> str:
    """
    Categorize hour into time of day.

    Args:
        hour: Hour (0-23)

    Returns:
        Category string
    """
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"


def aggregate_by_time_of_day(df: pd.DataFrame, sensor: str) -> Dict[str, float]:
    """
    Aggregate sensor readings by time of day.

    Args:
        df: DataFrame with 'gw_timestamp' column
        sensor: Sensor name

    Returns:
        Dict with average values for each time of day
    """
    if 'gw_timestamp' not in df.columns or sensor not in df.columns:
        return {}

    df_copy = df.copy()
    df_copy['hour'] = pd.to_datetime(df_copy['gw_timestamp']).dt.hour
    df_copy['time_of_day'] = df_copy['hour'].apply(get_time_of_day_category)

    result = df_copy.groupby('time_of_day')[sensor].mean().to_dict()

    return {k: float(v) for k, v in result.items()}


def calculate_data_quality_score(df: pd.DataFrame, sensor: str) -> Dict[str, Any]:
    """
    Calculate data quality metrics for a sensor.

    Args:
        df: DataFrame
        sensor: Sensor name

    Returns:
        Dict with quality metrics
    """
    if sensor not in df.columns:
        return {"error": "Sensor not found"}

    total_points = len(df)
    missing_points = df[sensor].isna().sum()
    valid_points = total_points - missing_points

    if valid_points == 0:
        return {
            "quality_score": 0,
            "completeness": 0,
            "missing_percentage": 100
        }

    completeness = (valid_points / total_points) * 100

    # Check for suspicious patterns
    series = df[sensor].dropna()
    std_dev = series.std()
    mean_val = series.mean()
    cv = (std_dev / mean_val * 100) if mean_val != 0 else 0  # Coefficient of variation

    # Calculate quality score (0-100)
    quality_score = completeness

    # Penalize if too many outliers
    z_scores = np.abs((series - mean_val) / std_dev) if std_dev > 0 else pd.Series([0] * len(series))
    outlier_percentage = (z_scores > 3).sum() / len(series) * 100
    if outlier_percentage > 5:
        quality_score *= 0.9

    return {
        "quality_score": round(float(quality_score), 2),
        "completeness": round(float(completeness), 2),
        "missing_points": int(missing_points),
        "valid_points": int(valid_points),
        "outlier_percentage": round(float(outlier_percentage), 2),
        "coefficient_of_variation": round(float(cv), 2)
    }


def format_value_with_unit(sensor: str, value: float) -> str:
    """
    Format sensor value with appropriate unit.

    Args:
        sensor: Sensor name
        value: Sensor value

    Returns:
        Formatted string with unit
    """
    units = {
        "temperature_sht": "°F",
        "humidity": "%",
        "pressure": "hPa",
        "light": "lux",
        "sound_level": "dB",
        "color_hex": ""
    }

    unit = units.get(sensor, "")

    if sensor == "color_hex":
        return str(value)
    else:
        return f"{value:.2f}{unit}"


def generate_summary_text(stats: Dict[str, Any]) -> str:
    """
    Generate human-readable summary from statistics.

    Args:
        stats: Statistics dictionary

    Returns:
        Summary text
    """
    if "error" in stats:
        return f"Error: {stats['error']}"

    sensor = stats.get("sensor", "Unknown")
    mean = stats.get("mean", 0)
    min_val = stats.get("min", 0)
    max_val = stats.get("max", 0)
    count = stats.get("count", 0)

    formatted_mean = format_value_with_unit(sensor, mean)
    formatted_min = format_value_with_unit(sensor, min_val)
    formatted_max = format_value_with_unit(sensor, max_val)

    return (
        f"{sensor}: Average {formatted_mean}, "
        f"ranging from {formatted_min} to {formatted_max} "
        f"({count} readings)"
    )
