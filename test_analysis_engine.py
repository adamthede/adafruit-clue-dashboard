#!/usr/bin/env python3
"""
Test script for the Analysis Engine

This script tests the basic functionality of the AnalysisEngine class
with sample data or existing CSV data if available.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Import the analysis engine
from analysis_engine import AnalysisEngine


def create_test_data(filepath):
    """Create test CSV data if no data exists."""
    print(f"Creating test data at {filepath}...")

    # Generate sample data for testing
    now = datetime.now(timezone.utc)
    records = []

    # Generate 1000 sample records over 7 days
    for i in range(1000):
        timestamp = now - timedelta(days=7) + timedelta(minutes=i * 10)

        # Create realistic sensor patterns
        hour = timestamp.hour
        record = {
            'gw_timestamp': timestamp.isoformat(),
            'timestamp_monotonic': i * 10.0,
            'timestamp_iso': timestamp.isoformat(),
            'temperature_sht': 70 + 5 * np.sin(hour * np.pi / 12) + np.random.normal(0, 1),
            'humidity': 50 + 10 * np.cos(hour * np.pi / 12) + np.random.normal(0, 2),
            'pressure': 1013 + np.random.normal(0, 5),
            'light': max(0, 500 + 400 * np.sin(hour * np.pi / 12) + np.random.normal(0, 50)),
            'sound_level': 40 + np.random.normal(0, 5),
            'color_hex': '#FFFFFF'
        }

        # Add some anomalies
        if i % 100 == 0:
            record['temperature_sht'] += 15  # Anomalous spike

        records.append(record)

    # Create DataFrame and save
    df = pd.DataFrame(records)
    df.to_csv(filepath, index=False)
    print(f"Created {len(records)} test records")


def test_analysis_engine():
    """Run comprehensive tests on the Analysis Engine."""
    print("=" * 60)
    print("Analysis Engine Test Suite")
    print("=" * 60)

    # Setup test data
    data_dir = Path.home() / "Library" / "Application Support" / "ClueGatewayWebview"
    data_dir.mkdir(parents=True, exist_ok=True)
    test_csv = data_dir / "sensor_data.csv"

    # Create test data if file doesn't exist or is empty
    if not test_csv.exists() or test_csv.stat().st_size == 0:
        create_test_data(test_csv)

    # Initialize engine
    print(f"\nInitializing AnalysisEngine with: {test_csv}")
    engine = AnalysisEngine(csv_filepath=test_csv)

    # Test 1: Data Summary
    print("\n" + "-" * 60)
    print("TEST 1: Data Summary")
    print("-" * 60)
    summary = engine.get_data_summary()
    if "error" in summary:
        print(f"❌ FAILED: {summary['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Total records: {summary['total_records']}")
        print(f"   Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"   Days covered: {summary['date_range']['days']}")
        print(f"   Sensors: {list(summary['sensors'].keys())}")

    # Test 2: Basic Statistics
    print("\n" + "-" * 60)
    print("TEST 2: Statistics for temperature_sht (24h)")
    print("-" * 60)
    stats = engine.compute_statistics("temperature_sht", "24h")
    if "error" in stats:
        print(f"❌ FAILED: {stats['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Count: {stats['count']}")
        print(f"   Mean: {stats['mean']:.2f}°F")
        print(f"   Min: {stats['min']:.2f}°F")
        print(f"   Max: {stats['max']:.2f}°F")
        print(f"   Std Dev: {stats['std_dev']:.2f}")

    # Test 3: Correlation Matrix
    print("\n" + "-" * 60)
    print("TEST 3: Correlation Matrix (7d)")
    print("-" * 60)
    corr = engine.compute_correlation_matrix("7d")
    if "error" in corr:
        print(f"❌ FAILED: {corr['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Sensors analyzed: {corr['labels']}")
        if len(corr['matrix']) > 2:
            print(f"   Sample correlation (temp vs humidity): {corr['matrix'][1][2]:.3f}")

    # Test 4: Anomaly Detection
    print("\n" + "-" * 60)
    print("TEST 4: Anomaly Detection for temperature_sht")
    print("-" * 60)
    anomalies = engine.detect_anomalies("temperature_sht", threshold_stdev=2.0, time_range="7d")
    if "error" in anomalies:
        print(f"❌ FAILED: {anomalies['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Mean: {anomalies['mean']:.2f}°F")
        print(f"   Std Dev: {anomalies['std_dev']:.2f}")
        print(f"   Anomalies found: {anomalies['total_count']}")
        if anomalies['total_count'] > 0:
            print(f"   First anomaly:")
            first = anomalies['anomalies'][0]
            print(f"     - Timestamp: {first['timestamp']}")
            print(f"     - Value: {first['value']:.2f}°F")
            print(f"     - Z-score: {first['z_score']:.2f}")

    # Test 5: Weekly Pattern
    print("\n" + "-" * 60)
    print("TEST 5: Weekly Pattern for temperature_sht")
    print("-" * 60)
    pattern = engine.compute_weekly_pattern("temperature_sht", weeks_back=1)
    if "error" in pattern:
        print(f"❌ FAILED: {pattern['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Pattern points: {len(pattern['pattern'])}")
        # Show sample from Monday morning
        monday_am = [p for p in pattern['pattern'] if p['day'] == 'Monday' and p['hour'] == 9]
        if monday_am:
            print(f"   Monday 9 AM average: {monday_am[0]['value']:.2f}°F")

    # Test 6: Scatter Data
    print("\n" + "-" * 60)
    print("TEST 6: Scatter Data (temperature vs humidity)")
    print("-" * 60)
    scatter = engine.compute_scatter_data("temperature_sht", "humidity", "24h", max_points=100)
    if "error" in scatter:
        print(f"❌ FAILED: {scatter['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Points returned: {scatter['count']}")
        if scatter['points']:
            sample = scatter['points'][0]
            print(f"   Sample point: x={sample['x']:.2f}, y={sample['y']:.2f}")

    # Test 7: Period Comparison
    print("\n" + "-" * 60)
    print("TEST 7: Period Comparison (24h vs 7d)")
    print("-" * 60)
    comparison = engine.compare_periods("temperature_sht", "24h", "7d")
    if "error" in comparison:
        print(f"❌ FAILED: {comparison['error']}")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   Period 1 mean: {comparison['period1']['stats']['mean']:.2f}°F")
        print(f"   Period 2 mean: {comparison['period2']['stats']['mean']:.2f}°F")
        print(f"   Mean difference: {comparison['differences']['mean_diff']:.2f}°F")
        pct = comparison['differences']['mean_pct_change']
        if pct:
            print(f"   Percent change: {pct:.2f}%")

    # Test 8: Cache Performance
    print("\n" + "-" * 60)
    print("TEST 8: Cache Performance")
    print("-" * 60)
    import time

    # First call (uncached)
    start = time.time()
    stats1 = engine.compute_statistics("temperature_sht", "7d")
    time1 = time.time() - start

    # Second call (should be cached)
    start = time.time()
    stats2 = engine.compute_statistics("temperature_sht", "7d")
    time2 = time.time() - start

    if "error" in stats1 or "error" in stats2:
        print(f"❌ FAILED: Error in statistics computation")
        return False
    else:
        print(f"✅ PASSED")
        print(f"   First call (uncached): {time1*1000:.2f} ms")
        print(f"   Second call (cached): {time2*1000:.2f} ms")
        if time2 < time1:
            speedup = time1 / time2
            print(f"   Cache speedup: {speedup:.1f}x faster")

    # All tests passed
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_analysis_engine()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
