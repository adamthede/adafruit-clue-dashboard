#!/usr/bin/env python3
"""
Automated QA Testing Script for Analysis Engine Integration

This script performs comprehensive automated testing of the analysis engine
when integrated with the gateway_webview application. It can be run standalone
or integrated into CI/CD pipelines.

Usage:
    python3 qa_automated_test.py [--verbose] [--create-data]

Options:
    --verbose       Show detailed output for each test
    --create-data   Create test data if none exists
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json

# Import the analysis engine
try:
    from analysis_engine import AnalysisEngine
except ImportError as e:
    print(f"❌ FATAL: Cannot import analysis_engine: {e}")
    print("Make sure you're in the correct directory and dependencies are installed.")
    sys.exit(1)


class QATestRunner:
    """Automated QA test runner for the Analysis Engine."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.tests_run = 0
        self.start_time = None
        self.results = []

    def log(self, message, level='INFO'):
        """Log a message with timestamp."""
        if self.verbose or level in ['ERROR', 'WARN', 'PASS', 'FAIL']:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level:5s} | {message}")

    def assert_true(self, condition, test_name, message=""):
        """Assert that a condition is true."""
        self.tests_run += 1
        if condition:
            self.passed += 1
            self.log(f"✅ {test_name}", 'PASS')
            self.results.append({'test': test_name, 'status': 'PASS', 'message': message})
            return True
        else:
            self.failed += 1
            self.log(f"❌ {test_name}: {message}", 'FAIL')
            self.results.append({'test': test_name, 'status': 'FAIL', 'message': message})
            return False

    def assert_no_error(self, result, test_name):
        """Assert that a result dictionary has no 'error' key."""
        if 'error' in result:
            return self.assert_true(False, test_name, f"Error: {result['error']}")
        return self.assert_true(True, test_name)

    def assert_has_keys(self, data, keys, test_name):
        """Assert that a dictionary has all required keys."""
        missing = [k for k in keys if k not in data]
        if missing:
            return self.assert_true(False, test_name, f"Missing keys: {missing}")
        return self.assert_true(True, test_name)

    def warn(self, message):
        """Log a warning."""
        self.warnings += 1
        self.log(f"⚠️  {message}", 'WARN')

    def test_initialization(self, data_file):
        """Test 1: Engine Initialization."""
        self.log("=" * 70)
        self.log("TEST SUITE 1: Engine Initialization")
        self.log("=" * 70)

        # Test file existence
        if not data_file.exists():
            self.warn(f"Data file not found: {data_file}")
            return False

        # Test engine creation
        try:
            engine = AnalysisEngine(csv_filepath=data_file)
            self.assert_true(engine is not None, "Engine instantiation")
            self.assert_true(engine.csv_filepath == data_file, "CSV filepath set correctly")
            return engine
        except Exception as e:
            self.assert_true(False, "Engine instantiation", str(e))
            return None

    def test_data_summary(self, engine):
        """Test 2: Data Summary."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 2: Data Summary")
        self.log("=" * 70)

        result = engine.get_data_summary()

        if not self.assert_no_error(result, "get_data_summary() no error"):
            return False

        self.assert_has_keys(
            result,
            ['total_records', 'date_range', 'sensors', 'file_path'],
            "get_data_summary() has required keys"
        )

        # Validate data quality
        if 'total_records' in result:
            count = result['total_records']
            self.log(f"Total records: {count}")
            if count == 0:
                self.warn("No data records found")
            elif count < 100:
                self.warn(f"Low record count: {count}")
            else:
                self.assert_true(True, f"Sufficient data records ({count})")

        if 'date_range' in result:
            days = result['date_range'].get('days', 0)
            self.log(f"Data spans {days} days")
            if days < 1:
                self.warn("Less than 1 day of data")

        return True

    def test_statistics(self, engine):
        """Test 3: Statistical Analysis."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 3: Statistical Analysis")
        self.log("=" * 70)

        sensors = ['temperature_sht', 'humidity', 'pressure', 'light', 'sound_level']
        time_ranges = ['1h', '24h', '7d']

        for sensor in sensors:
            for time_range in time_ranges:
                result = engine.compute_statistics(sensor, time_range)

                test_name = f"Statistics: {sensor} ({time_range})"

                if 'error' in result:
                    # It's OK if there's no data for some time ranges
                    if 'No data found' in result['error']:
                        self.log(f"⚪ {test_name}: No data (OK)")
                        continue
                    else:
                        self.assert_true(False, test_name, result['error'])
                        continue

                # Validate structure
                required_keys = ['count', 'min', 'max', 'mean', 'median', 'std_dev']
                if not self.assert_has_keys(result, required_keys, test_name):
                    continue

                # Validate values
                if result['min'] > result['max']:
                    self.assert_true(False, f"{test_name} min/max check",
                                   f"min ({result['min']}) > max ({result['max']})")

                if result['count'] > 0:
                    self.assert_true(True, test_name)
                    self.log(f"   count={result['count']}, mean={result['mean']:.2f}")

    def test_correlations(self, engine):
        """Test 4: Correlation Analysis."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 4: Correlation Analysis")
        self.log("=" * 70)

        result = engine.compute_correlation_matrix('7d')

        if not self.assert_no_error(result, "compute_correlation_matrix() no error"):
            return False

        self.assert_has_keys(result, ['matrix', 'labels'],
                           "Correlation matrix has required keys")

        if 'matrix' in result and 'labels' in result:
            labels = result['labels']
            matrix = result['matrix']

            # Validate structure
            expected_size = len(labels) + 1  # Header row + data rows
            self.assert_true(
                len(matrix) == expected_size,
                "Correlation matrix size",
                f"Expected {expected_size} rows, got {len(matrix)}"
            )

            # Check diagonal values (should be 1.0 or close)
            if len(matrix) > 1:
                for i in range(1, min(len(matrix), len(labels) + 1)):
                    if isinstance(matrix[i], list) and len(matrix[i]) > i-1:
                        diag_val = matrix[i][i-1]
                        if diag_val is not None:
                            self.assert_true(
                                abs(diag_val - 1.0) < 0.01,
                                f"Correlation diagonal [{i-1}]",
                                f"Expected ~1.0, got {diag_val}"
                            )

            self.log(f"Correlation matrix: {len(labels)} sensors analyzed")

    def test_anomaly_detection(self, engine):
        """Test 5: Anomaly Detection."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 5: Anomaly Detection")
        self.log("=" * 70)

        sensors = ['temperature_sht', 'humidity', 'pressure']
        thresholds = [2.0, 2.5, 3.0]

        for sensor in sensors:
            for threshold in thresholds:
                result = engine.detect_anomalies(sensor, threshold, '7d')

                test_name = f"Anomaly detection: {sensor} (threshold={threshold})"

                if 'error' in result:
                    if 'No data found' in result['error'] or 'Insufficient data' in result['error']:
                        self.log(f"⚪ {test_name}: {result['error']} (OK)")
                        continue
                    else:
                        self.assert_true(False, test_name, result['error'])
                        continue

                # Validate structure
                required_keys = ['mean', 'std_dev', 'total_count', 'anomalies']
                if not self.assert_has_keys(result, required_keys, test_name):
                    continue

                count = result['total_count']
                self.log(f"   Found {count} anomalies")

                # Validate anomaly structure
                if count > 0 and len(result['anomalies']) > 0:
                    anomaly = result['anomalies'][0]
                    self.assert_has_keys(
                        anomaly,
                        ['timestamp', 'value', 'z_score', 'deviation'],
                        f"{test_name} - anomaly structure"
                    )

                self.assert_true(True, test_name)

    def test_patterns(self, engine):
        """Test 6: Pattern Analysis."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 6: Pattern Analysis")
        self.log("=" * 70)

        # Weekly pattern
        result = engine.compute_weekly_pattern('temperature_sht', weeks_back=4)

        if 'error' in result:
            self.assert_no_error(result, "Weekly pattern")
        else:
            self.assert_has_keys(result, ['pattern', 'sensor', 'weeks_back'],
                               "Weekly pattern structure")

            if 'pattern' in result:
                pattern = result['pattern']
                # Should have 168 entries (7 days * 24 hours)
                self.assert_true(
                    len(pattern) == 168,
                    "Weekly pattern size",
                    f"Expected 168 points, got {len(pattern)}"
                )

                # Check structure of pattern points
                if len(pattern) > 0:
                    point = pattern[0]
                    self.assert_has_keys(
                        point,
                        ['day', 'day_num', 'hour', 'value'],
                        "Weekly pattern point structure"
                    )

    def test_scatter_data(self, engine):
        """Test 7: Scatter Plot Data."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 7: Scatter Plot Data")
        self.log("=" * 70)

        pairs = [
            ('temperature_sht', 'humidity'),
            ('pressure', 'temperature_sht'),
            ('light', 'sound_level')
        ]

        for sensor_x, sensor_y in pairs:
            result = engine.compute_scatter_data(sensor_x, sensor_y, '24h', max_points=100)

            test_name = f"Scatter: {sensor_x} vs {sensor_y}"

            if 'error' in result:
                if 'No data found' in result['error'] or 'No valid data' in result['error']:
                    self.log(f"⚪ {test_name}: No data (OK)")
                    continue
                else:
                    self.assert_true(False, test_name, result['error'])
                    continue

            self.assert_has_keys(result, ['count', 'points'], test_name)

            if 'count' in result:
                count = result['count']
                self.log(f"   {count} scatter points")

                # Validate we didn't exceed max_points
                self.assert_true(
                    count <= 100,
                    f"{test_name} - respects max_points",
                    f"Expected ≤100, got {count}"
                )

    def test_period_comparison(self, engine):
        """Test 8: Period Comparison."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 8: Period Comparison")
        self.log("=" * 70)

        result = engine.compare_periods('temperature_sht', '24h', '7d')

        if not self.assert_no_error(result, "Period comparison"):
            return False

        required_keys = ['period1', 'period2', 'differences']
        self.assert_has_keys(result, required_keys, "Period comparison structure")

        if 'differences' in result:
            diffs = result['differences']
            self.assert_has_keys(
                diffs,
                ['mean_diff', 'mean_pct_change', 'median_diff'],
                "Period comparison differences"
            )

            if 'mean_diff' in diffs:
                self.log(f"   Mean difference: {diffs['mean_diff']:.2f}")

    def test_performance(self, engine):
        """Test 9: Performance Benchmarks."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 9: Performance Benchmarks")
        self.log("=" * 70)

        # Test 1: Statistics performance
        start = time.time()
        result = engine.compute_statistics('temperature_sht', '30d')
        duration = time.time() - start

        self.log(f"Statistics (30d): {duration*1000:.2f} ms")
        self.assert_true(
            duration < 2.0,
            "Statistics performance",
            f"Expected < 2s, took {duration:.2f}s"
        )

        # Test 2: Cache effectiveness
        start = time.time()
        result2 = engine.compute_statistics('temperature_sht', '30d')
        cached_duration = time.time() - start

        self.log(f"Statistics (cached): {cached_duration*1000:.2f} ms")

        if cached_duration < duration:
            speedup = duration / cached_duration
            self.log(f"   Cache speedup: {speedup:.1f}x faster")
            self.assert_true(True, "Cache performance improvement")
        else:
            self.warn("Cache didn't improve performance")

        # Test 3: Correlation matrix performance
        start = time.time()
        result = engine.compute_correlation_matrix('7d')
        duration = time.time() - start

        self.log(f"Correlation matrix: {duration*1000:.2f} ms")
        self.assert_true(
            duration < 3.0,
            "Correlation performance",
            f"Expected < 3s, took {duration:.2f}s"
        )

    def test_edge_cases(self, engine):
        """Test 10: Edge Cases and Error Handling."""
        self.log("\n" + "=" * 70)
        self.log("TEST SUITE 10: Edge Cases & Error Handling")
        self.log("=" * 70)

        # Test invalid sensor
        result = engine.compute_statistics('invalid_sensor', '24h')
        self.assert_true(
            'error' in result,
            "Invalid sensor returns error",
            "Should return error for invalid sensor"
        )

        # Test invalid time range (should fallback gracefully)
        result = engine.compute_statistics('temperature_sht', 'invalid_range')
        self.log(f"Invalid time range result: {'error' in result}")

        # Test empty custom time range
        result = engine.compute_statistics('temperature_sht', {})
        self.log(f"Empty time range dict: {'error' in result or result.get('count', 0) > 0}")

        # Test very old date range (likely no data)
        result = engine.compute_statistics('temperature_sht', {
            'start': '2020-01-01T00:00:00Z',
            'end': '2020-01-02T00:00:00Z'
        })
        if 'error' in result:
            self.assert_true(
                'No data found' in result['error'],
                "Old date range - no data error"
            )

    def print_summary(self):
        """Print test summary."""
        duration = time.time() - self.start_time if self.start_time else 0

        self.log("\n" + "=" * 70)
        self.log("TEST SUMMARY")
        self.log("=" * 70)
        self.log(f"Tests run:  {self.tests_run}")
        self.log(f"Passed:     {self.passed} ✅")
        self.log(f"Failed:     {self.failed} ❌")
        self.log(f"Warnings:   {self.warnings} ⚠️")
        self.log(f"Duration:   {duration:.2f}s")
        self.log("=" * 70)

        if self.failed == 0:
            self.log("🎉 ALL TESTS PASSED!", 'PASS')
            return 0
        else:
            self.log(f"⚠️  {self.failed} TEST(S) FAILED", 'FAIL')
            return 1

    def run_all_tests(self, data_file):
        """Run all test suites."""
        self.start_time = time.time()

        self.log("=" * 70)
        self.log("AUTOMATED QA TEST SUITE - Analysis Engine Integration")
        self.log("=" * 70)
        self.log(f"Data file: {data_file}")
        self.log(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("")

        # Initialize engine
        engine = self.test_initialization(data_file)
        if not engine:
            self.log("FATAL: Cannot proceed without engine initialization", 'ERROR')
            return self.print_summary()

        # Run test suites
        self.test_data_summary(engine)
        self.test_statistics(engine)
        self.test_correlations(engine)
        self.test_anomaly_detection(engine)
        self.test_patterns(engine)
        self.test_scatter_data(engine)
        self.test_period_comparison(engine)
        self.test_performance(engine)
        self.test_edge_cases(engine)

        return self.print_summary()


def create_test_data(filepath):
    """Create sample test data."""
    import pandas as pd
    import numpy as np

    print(f"Creating test data at {filepath}...")

    now = datetime.now(timezone.utc)
    records = []

    # Generate 2000 sample records over 14 days
    for i in range(2000):
        timestamp = now - timedelta(days=14) + timedelta(minutes=i * 10)
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
        if i % 200 == 0:
            record['temperature_sht'] += 15

        records.append(record)

    df = pd.DataFrame(records)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"✅ Created {len(records)} test records")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Automated QA tests for Analysis Engine')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--create-data', action='store_true', help='Create test data if none exists')
    args = parser.parse_args()

    # Determine data file location
    data_dir = Path.home() / "Library" / "Application Support" / "ClueGatewayWebview"
    data_file = data_dir / "sensor_data.csv"

    # Create test data if requested or if file doesn't exist
    if args.create_data or not data_file.exists() or data_file.stat().st_size == 0:
        create_test_data(data_file)

    # Run tests
    runner = QATestRunner(verbose=args.verbose)
    exit_code = runner.run_all_tests(data_file)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
