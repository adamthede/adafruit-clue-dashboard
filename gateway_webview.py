# gateway_webview.py

import webview
import serial
import serial.tools.list_ports
import json
import time
import threading
import logging
import os
import sys
from datetime import datetime, timezone, timedelta, MINYEAR
from collections import deque
import csv
from pathlib import Path
import configparser
# --- Analysis Engine Import ---
from analysis_engine import AnalysisEngine
# --- Adafruit IO Imports --- (Re-enable import)
try:
    from Adafruit_IO import Client, Feed, RequestError, ThrottlingError
except ImportError:
    print("ERROR: Adafruit_IO library not found.")
    print("Please install it: pip install adafruit-io")
    # Define placeholders if import fails
    Client = None
    Feed = None
    RequestError = Exception
    ThrottlingError = Exception
    AIO_AVAILABLE = False
else:
    AIO_AVAILABLE = True
# REMOVE AIO_AVAILABLE = False # Manually disable AIO for testing
# REMOVE dummy definitions
# Client = None
# Feed = None
# RequestError = Exception
# ThrottlingError = Exception

# --- Constants ---
APP_NAME = "ClueGatewayWebview"
DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
DATA_FILE = DATA_DIR / "sensor_data.csv"
CSV_FIELDNAMES = [
    'gw_timestamp', 'timestamp_monotonic', 'timestamp_iso',
    'temperature_sht', 'humidity', 'pressure', 'light', 'sound_level', 'color_hex'
]
CONFIG_FILE = DATA_DIR / "config.ini" # MODIFIED: Use path in Application Support

# --- Global Variables / State ---
aio_client = None
serial_connection = None
serial_thread = None
stop_serial_event = threading.Event()
window = None
MAX_LOCAL_POINTS = 300 # Max points to load into memory/chart (even after filtering)
local_data_store = deque(maxlen=MAX_LOCAL_POINTS)
current_clue_interval = 30 # Default interval
initial_aio_status_text = "Unknown"
initial_aio_status_type = "info"
analysis_engine = None  # Will be initialized after DATA_FILE is ensured to exist

# --- Setup Logging & Data Directory ---
log_dir = Path.home() / "Library" / "Logs" / APP_NAME
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "gateway_webview.log"
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception
logging.info("--- Gateway Webview Application Started ---")

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.info(f"Using data file: {DATA_FILE}")

# --- Adafruit IO Client Initialization (Remove Debug Prints) ---
def initialize_aio_client():
    # print("DEBUG: Entered initialize_aio_client()")
    global aio_client, initial_aio_status_text, initial_aio_status_type
    initial_aio_status_text = "Initializing..." # Set initial status text
    initial_aio_status_type = "info"

    # print("DEBUG: Checking AIO_AVAILABLE...")
    if not AIO_AVAILABLE:
        # ... (handle missing lib)
        return False, "Disabled (Lib Missing)"
    # print("DEBUG: AIO_AVAILABLE is True")

    config = configparser.ConfigParser()
    config_created = False
    try:
        # print("DEBUG: Checking config file existence...")
        if not CONFIG_FILE.is_file():
            # --- Create Default Config File ---
            print(f"INFO: Config file '{CONFIG_FILE}' not found. Creating default.")
            logging.info(f"Config file '{CONFIG_FILE}' not found. Creating default.")
            try:
                config['AdafruitIO'] = {
                    'username': 'YOUR_AIO_USERNAME',
                    'key': 'YOUR_AIO_KEY'
                }
                with open(CONFIG_FILE, 'w') as configfile:
                    config.write(configfile)
                config_created = True
                log_to_frontend(f"Created default config file: {CONFIG_FILE}. Please edit it with your credentials.", 'warn')
            except Exception as create_err:
                err_msg = f"Error: Failed to create default config file '{CONFIG_FILE}': {create_err}"
                log_to_frontend(err_msg, 'error')
                logging.error(err_msg)
                initial_aio_status_text = "Error (Create Config)"
                initial_aio_status_type = "error"
                return False, initial_aio_status_text
            # --- End Create Default Config File ---
        else:
           # print("DEBUG: Config file found.")
            pass # File exists, proceed to read

        # print("DEBUG: Reading config file...")
        config.read(CONFIG_FILE)
        # ... (rest of config reading and client init logic)
        aio_username = config.get('AdafruitIO', 'username', fallback=None)
        aio_key = config.get('AdafruitIO', 'key', fallback=None)

        # Check for placeholder values AFTER potentially creating the file
        if config_created or not aio_username or not aio_key or aio_username == 'YOUR_AIO_USERNAME' or aio_key == 'YOUR_AIO_KEY':
            err_msg = "Error: Please set Adafruit IO username/key in config.ini."
            if config_created:
                 err_msg = "Default config.ini created. Please edit it with your Adafruit IO username/key."
            log_to_frontend(err_msg, 'warn') # Use warn level
            logging.warning(err_msg)
            initial_aio_status_text = "Error (Bad config)"
            initial_aio_status_type = "error"
            return False, initial_aio_status_text
        # ... (rest of init)
        # print("DEBUG: Calling Client(aio_username, aio_key)...")
        aio_client = Client(aio_username, aio_key)
        # print("DEBUG: Client(aio_username, aio_key) returned.")

        # Assume success (verification still commented out)
        status_text = f"OK ({aio_username})"
        logging.info(f"Adafruit IO Client created for user '{aio_username}' (Verification skipped)." )
        initial_aio_status_text = status_text
        initial_aio_status_type = "success"
        return True, status_text

    except configparser.Error as e:
        # ... (logging)
        status_text = "Error (Config Parse)"
        initial_aio_status_text = status_text
        initial_aio_status_type = "error"
        return False, status_text
    except Exception as e:
        # ... (logging)
        status_text = "Error (Unknown)"
        initial_aio_status_text = status_text
        initial_aio_status_type = "error"
        return False, status_text

# --- Adafruit IO Feed Mapping ---
FEED_MAP = {
    "temperature_sht": "temperature-sht",
    "humidity": "humidity",
    "pressure": "pressure",
    "light": "light",
    "sound_level": "sound-level",
    "color_hex": "color-hex",
}

# --- CSV Handling Functions ---
def append_to_csv(filepath, data_dict):
    """Appends a row to the CSV file."""
    try:
        # Ensure file exists and has header if it's new/empty
        file_exists = filepath.is_file()
        is_empty = not file_exists or filepath.stat().st_size == 0

        with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES, extrasaction='ignore')
            if is_empty:
                writer.writeheader()
            writer.writerow(data_dict)
    except IOError as e:
        logging.error(f"Error appending to CSV file {filepath}: {e}")
        log_to_frontend(f"Error saving data to CSV: {e}", 'error')
    except Exception as e:
        logging.exception(f"Unexpected error appending to CSV: {e}")
        log_to_frontend(f"Error saving data to CSV: {e}", 'error')

def load_initial_data(filepath, max_points, time_range_filter="1h"):
    # Note: max_points argument is now ignored here, but kept for potential future use elsewhere
    loaded_data = []
    start_time_utc = None
    now_utc = datetime.now(timezone.utc)

    # Calculate start time based on filter
    if time_range_filter == "1h": start_time_utc = now_utc - timedelta(hours=1)
    elif time_range_filter == "6h": start_time_utc = now_utc - timedelta(hours=6)
    elif time_range_filter == "24h": start_time_utc = now_utc - timedelta(days=1)
    elif time_range_filter == "7d": start_time_utc = now_utc - timedelta(days=7)
    elif time_range_filter == "30d": start_time_utc = now_utc - timedelta(days=30)
    elif time_range_filter == "all": start_time_utc = datetime(MINYEAR, 1, 1, tzinfo=timezone.utc)
    else: start_time_utc = now_utc - timedelta(hours=1)

    logging.info(f"Loading data from {filepath} since {start_time_utc} (filter: {time_range_filter})" )

    try:
        if filepath.is_file() and filepath.stat().st_size > 0:
            with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        record_time_utc = datetime.fromisoformat(row['gw_timestamp'])
                        if record_time_utc.tzinfo is None: record_time_utc = record_time_utc.replace(tzinfo=timezone.utc)
                        if record_time_utc >= start_time_utc:
                            loaded_data.append(row)
                    except (ValueError, KeyError, TypeError) as e:
                         logging.warning(f"Skipping CSV row due to parse error ('{row.get('gw_timestamp')}'): {e}")
                         continue
        else:
            logging.info(f"Data file {filepath} not found or empty.")
    except Exception as e:
        logging.exception(f"Error reading or filtering data from CSV {filepath}: {e}")
        log_to_frontend(f"Error loading previous data: {e}", 'error')

    # Log the number of points *actually* loaded based on the filter
    logging.info(f"Loaded {len(loaded_data)} records matching time range ' {time_range_filter}'.")
    log_to_frontend(f"Loaded {len(loaded_data)} records for selected time range.", 'info')

    # Return the FULL list of filtered records
    return loaded_data

# --- Helper Functions for Backend ---
def log_to_frontend(message, level='info'):
    global window
    try:
        escaped_message = message.replace('\\', '\\\\').replace('`', '\\`').replace('\n', '\\n')
        if window:
            window.evaluate_js(f"addLogMessage(`{escaped_message}`, '{level}');")
    except Exception as e:
        logging.error(f"Error logging to frontend: {e}")

# ADDED Helper to update AIO status specifically
def set_aio_status(status_text, status_type='info'):
    global window
    if window:
        try:
            escaped_text = json.dumps(status_text) # Basic escaping for JS string
            window.evaluate_js(f'updateAioStatus({escaped_text}, "{status_type}");')
        except Exception as e:
            logging.error(f"Error calling updateAioStatus in JS: {e}")

def update_status(status_text, status_type='info'):
    global window
    log_to_frontend(f"Status changed: {status_text}", status_type)
    try:
        if window:
            window.evaluate_js(f"updateStatus(`{status_text}`, '{status_type}');")
    except Exception as e:
        logging.error(f"Error updating status: {e}")

def upload_to_aio(data_dict):
    global aio_client
    if not aio_client:
        # Status already set during init if failed
        # log_to_frontend("Adafruit IO not available/initialized. Skipping upload.", 'warn')
        return False

    # Revert to individual uploads with delay
    log_to_frontend("Attempting to upload data to Adafruit IO (individual feeds)...", 'info')
    success_count = 0
    fail_count = 0
    rate_limit_delay = 1.1 # Delay between sends to avoid rate limits
    all_success = True # Track overall success

    for sensor_key, feed_key in FEED_MAP.items():
        if stop_serial_event.is_set():
             log_to_frontend("Upload aborted (stop event).", 'warn')
             return False # Stop the whole process
        if sensor_key in data_dict and data_dict[sensor_key] is not None:
            value = data_dict[sensor_key]
            try:
                set_aio_status(f"Sending {feed_key}...", 'info') # Indicate sending
                aio_client.send_data(feed_key, value)
                set_aio_status(f"OK ({feed_key})", 'success') # Indicate success for this feed
                success_count += 1
                time.sleep(rate_limit_delay)
            except ThrottlingError: # Catch specific throttling error
                log_to_frontend(f"     ...AIO ThrottlingError for '{feed_key}'", 'warn')
                logging.warning(f"Adafruit IO ThrottlingError for {feed_key}")
                set_aio_status(f"Throttled ({feed_key})", 'warn') # Specific status
                fail_count += 1
                all_success = False
                time.sleep(rate_limit_delay * 2) # Wait longer after throttle
            except RequestError as e:
                log_to_frontend(f"     ...AIO RequestError for '{feed_key}': {e}", 'error')
                logging.error(f"Adafruit IO RequestError for {feed_key}: {e}")
                set_aio_status(f"Error ({feed_key}: Req)", 'error') # Indicate request error
                fail_count += 1
                all_success = False
            except Exception as e:
                log_to_frontend(f"     ...Error sending to '{feed_key}': {e}", 'error')
                logging.exception(f"Upload exception for {feed_key}")
                set_aio_status(f"Error ({feed_key}: Send)", 'error') # Indicate other send error
                fail_count += 1
                all_success = False

    log_to_frontend(f"Upload attempt finished. Success: {success_count}, Failed: {fail_count}", 'info')
    # Set final status after loop if needed (e.g., if last status was an error)
    if fail_count > 0:
        set_aio_status("Finished (with errors)", 'warn')
    elif success_count > 0 :
        set_aio_status("OK (Idle)", 'success')
    # Else status remains from the last operation

    return all_success # Return True only if ALL sends succeeded

# --- Serial Worker Thread ---
def serial_worker(port):
    global serial_connection, stop_serial_event, aio_client, local_data_store, window, current_clue_interval
    logging.info(f"Serial worker thread started for port {port}.")
    log_to_frontend(f"[Worker] Started for {port}", 'debug')
    update_status("Connecting...", 'info')

    ser = None
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        logging.info(f"Successfully opened serial port {port}.")
        log_to_frontend(f"[Worker] Serial port {port} opened.", 'debug')
        update_status("Connected", 'success')
        if window: window.evaluate_js(f"setConnectionState(true);")
        serial_connection = ser

        while not stop_serial_event.is_set():
            line_bytes = None
            try:
                if ser.in_waiting > 0:
                    line_bytes = ser.readline()
                else:
                    time.sleep(0.1)
                    continue
            except serial.SerialException as read_err:
                 logging.error(f"Serial error during read on {port}: {read_err}")
                 log_to_frontend(f"[Worker] Serial read error: {read_err}", 'error')
                 update_status("Read Error", 'error')
                 break

            if line_bytes:
                try:
                    line_str = line_bytes.decode('utf-8', errors='ignore').strip()
                    if line_str:
                        try:
                            sensor_data = json.loads(line_str)
                            if isinstance(sensor_data, dict) and "timestamp_monotonic" in sensor_data:
                                log_to_frontend(f"Received valid sensor JSON.", 'info')

                                # --- BEGIN MOVED CONVERSION ---
                                if "temperature_sht" in sensor_data and sensor_data["temperature_sht"] is not None:
                                    try:
                                        celsius = sensor_data["temperature_sht"]
                                        fahrenheit = (celsius * 9/5) + 32
                                        sensor_data["temperature_sht"] = round(fahrenheit, 2) # Update the dict directly
                                        log_to_frontend(f"Converted temp: {celsius}°C -> {sensor_data['temperature_sht']}°F", 'debug')
                                    except Exception as e:
                                        log_to_frontend(f"Error converting temperature: {e}", 'error')
                                        logging.error(f"Error converting temp: {e} for value {sensor_data['temperature_sht']}")
                                # --- END MOVED CONVERSION ---

                                # Add gateway timestamp for charting
                                gw_timestamp = datetime.now(timezone.utc).isoformat()
                                sensor_data['gw_timestamp'] = gw_timestamp # Add timestamp

                                # Add to local storage (NOW WITH FAHRENHEIT)
                                local_data_store.append(sensor_data.copy()) # Append a copy

                                # Append to persistent CSV storage (NOW WITH FAHRENHEIT)
                                append_to_csv(DATA_FILE, sensor_data)

                                # Log dictionary content nicely
                                for key, val in sensor_data.items():
                                    log_to_frontend(f"  {key}: {val}", 'debug')

                                # Update chart with the new data point (NOW WITH FAHRENHEIT)
                                if window:
                                    try:
                                        # Send only the necessary data for the chart update
                                        chart_data_point = {
                                            'label': gw_timestamp, # Use gateway time for label
                                            'temperature_sht': sensor_data.get('temperature_sht'),
                                            'humidity': sensor_data.get('humidity'),
                                            'pressure': sensor_data.get('pressure'),
                                            'light': sensor_data.get('light'),
                                            'sound_level': sensor_data.get('sound_level'),
                                            'color_hex': sensor_data.get('color_hex')
                                        }
                                        # Convert to JSON string to pass to JS
                                        chart_data_json = json.dumps(chart_data_point)
                                        # Escape potentially problematic chars in JSON string for JS eval
                                        escaped_chart_data = chart_data_json.replace('\\', '\\\\').replace('`', '\\`')
                                        window.evaluate_js(f'updateChart(`{escaped_chart_data}`);')
                                    except Exception as chart_err:
                                         logging.error(f"Error calling updateChart in JS: {chart_err}")

                                # Trigger AIO upload (NOW WITH FAHRENHEIT)
                                upload_to_aio(sensor_data)

                        except json.JSONDecodeError:
                            logging.debug(f"Ignoring non-JSON line: {line_str}")
                except Exception as process_err:
                    logging.exception(f"Error processing line: {line_str}")
                    log_to_frontend(f"[Worker] Processing error: {process_err}", 'error')

        logging.info("Serial worker loop exiting.")
        log_to_frontend("[Worker] Worker loop exited.", 'debug')

    except serial.SerialException as conn_err:
        logging.error(f"Failed to open serial port {port}: {conn_err}")
        log_to_frontend(f"[Worker] Failed to open {port}: {conn_err}", 'error')
        update_status("Connection Failed", 'error')
    except Exception as e:
        logging.exception(f"Unexpected error in serial worker for {port}")
        log_to_frontend(f"[Worker] Error: {e}", 'error')
        update_status("Worker Error", 'error')
    finally:
        if ser and ser.is_open:
            ser.close()
            logging.info(f"Serial port {port} closed by worker thread.")
            log_to_frontend(f"[Worker] Port {port} closed.", 'debug')
        serial_connection = None # Clear global reference
        update_status("Disconnected", 'info')
        try:
            if window:
                 window.evaluate_js(f"setConnectionState(false);")
        except Exception as e:
            logging.error(f"Error evaluating JS on disconnect: {e}")
    logging.info(f"Serial worker thread for {port} finished.")
    log_to_frontend("[Worker] Worker thread finished.", 'debug')

# --- MOVE THE ENTIRE API CLASS HERE ---
class Api:
    def __init__(self):
        self._selected_port = None
        self._current_interval = 30
        # Data store is initialized empty, will be populated by live data

    def list_serial_ports(self):
        logging.debug("JS requested port list")
        ports = serial.tools.list_ports.comports()
        port_list = [{'device': p.device, 'description': p.description} for p in ports]
        logging.debug(f"Returning ports: {port_list}")
        return port_list

    def connect(self, port):
        global serial_thread, stop_serial_event, current_clue_interval
        current_clue_interval = self._current_interval
        log_to_frontend(f"Connect requested for port: {port}", 'info')
        if serial_thread and serial_thread.is_alive():
            log_to_frontend("Already connected or worker running.", 'warn')
            return {'success': False, 'message': 'Already connected'}
        if not port:
            log_to_frontend("No serial port selected.", 'warn')
            return {'success': False, 'message': 'No port selected'}
        stop_serial_event.clear()
        serial_thread = threading.Thread(target=serial_worker, args=(port,), daemon=True, name=f"SerialWorker-{port.split('/')[-1]}")
        serial_thread.start()
        return {'success': True, 'message': 'Connection process started'}

    def disconnect(self):
        global serial_thread, stop_serial_event
        log_to_frontend("Disconnect requested.", 'info')
        if serial_thread and serial_thread.is_alive():
            stop_serial_event.set()
            return {'success': True, 'message': 'Disconnect signal sent'}
        else:
            log_to_frontend("Not currently connected.", 'warn')
            update_status("Disconnected", 'info')
            return {'success': False, 'message': 'Not connected'}

    def log_from_js(self, message):
        logging.info(f"[JS LOG] {message}")

    def set_interval(self, interval_str):
        global serial_connection, current_clue_interval
        log_to_frontend(f"Request to set interval to: {interval_str}s", 'info')
        if not serial_connection or not serial_connection.is_open:
            log_to_frontend("Cannot set interval: Not connected.", 'warn')
            return {'success': False, 'message': 'Not connected'}
        try:
            interval_val = int(interval_str)
            if interval_val < 1:
                 log_to_frontend("Invalid interval: Must be >= 1 second.", 'error')
                 return {'success': False, 'message': 'Interval too low'}

            command = {"command": "set_interval", "value": interval_val}
            command_json = json.dumps(command) + '\n'
            serial_connection.write(command_json.encode('utf-8'))
            log_to_frontend(f"Sent command to CLUE: {command_json.strip()}", 'debug')

            self._current_interval = interval_val
            current_clue_interval = interval_val
            logging.info(f"Updated current_clue_interval to: {current_clue_interval}")

            return {'success': True, 'message': f'Interval command sent ({interval_val}s)'}
        except ValueError:
            log_to_frontend(f"Invalid interval value: '{interval_str}'. Must be an integer.", 'error')
            return {'success': False, 'message': 'Invalid interval format'}
        except serial.SerialException as e:
             log_to_frontend(f"Serial error sending interval command: {e}", 'error')
             logging.error(f"Serial error sending interval: {e}")
             return {'success': False, 'message': 'Serial write error'}
        except Exception as e:
            log_to_frontend(f"Error sending interval command: {e}", 'error')
            logging.exception("Error sending interval command")
            return {'success': False, 'message': 'Unexpected error'}

    def get_initial_chart_data(self, time_range_filter="1h"):
        # Load data based on the requested filter - this returns a LIST
        logging.info(f"API: Loading initial data with filter: {time_range_filter}")
        initial_records_list = load_initial_data(DATA_FILE, MAX_LOCAL_POINTS, time_range_filter)

        logging.debug(f"JS requested initial chart data. Processing {len(initial_records_list)} records from list." )
        # Format data for the Chart
        labels = []
        temp_data = []
        humidity_data = []
        pressure_data = []
        light_data = []
        sound_data = []
        for data_point in initial_records_list:
            labels.append(data_point.get('gw_timestamp', ''))
            try: temp_data.append(float(data_point['temperature_sht']) if data_point.get('temperature_sht') not in [None, ''] else None)
            except (ValueError, TypeError): temp_data.append(None)
            try: humidity_data.append(float(data_point['humidity']) if data_point.get('humidity') not in [None, ''] else None)
            except (ValueError, TypeError): humidity_data.append(None)
            try: pressure_data.append(float(data_point['pressure']) if data_point.get('pressure') not in [None, ''] else None)
            except (ValueError, TypeError): pressure_data.append(None)
            try: light_data.append(int(data_point['light']) if data_point.get('light') not in [None, ''] else None)
            except (ValueError, TypeError): light_data.append(None)
            try: sound_data.append(int(data_point['sound_level']) if data_point.get('sound_level') not in [None, ''] else None)
            except (ValueError, TypeError): sound_data.append(None)

        # Return BOTH the chart-formatted data and the original raw data list
        chart_data = {
            'labels': labels,
            'datasets': {
                'temperature': temp_data,
                'humidity': humidity_data,
                'pressure': pressure_data,
                'light': light_data,
                'sound': sound_data,
            }
        }
        return {
             'chartData': chart_data,      # Data formatted for Chart.js
             'rawData': initial_records_list # Original list of dictionaries
         }

    # ADDED Method to get initial status info
    def get_initial_status(self):
        global initial_aio_status_text, initial_aio_status_type
        logging.debug("JS requested initial status")
        # Return both main and AIO status determined during startup
        return {
            "main_status": "Disconnected", # Initial main status
            "main_status_type": "info",
            "aio_status": initial_aio_status_text,
            "aio_status_type": initial_aio_status_type
        }

    # --- MODIFIED EXPORT METHOD ---
    def export_chart_data(self, time_range_filter="1h"): # Accept filter
        """Exports the data corresponding to the currently selected time range."""
        global window, DATA_FILE, MAX_LOCAL_POINTS # MAX_LOCAL_POINTS is ignored by load_initial_data
        log_to_frontend(f"Export chart data requested (Range: {time_range_filter})...", 'info')

        try:
            # Load the data for the specified range, similar to get_initial_chart_data
            data_to_export = load_initial_data(DATA_FILE, MAX_LOCAL_POINTS, time_range_filter)

            if not data_to_export:
                 log_to_frontend(f"No data found for time range '{time_range_filter}' to export.", 'warn')
                 return {"success": False, "message": "No data available for selected range"}

            # Ask user for save location
            default_filename = f"clue_chart_data_{time_range_filter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            result = window.create_file_dialog(webview.SAVE_DIALOG, directory=str(Path.home()), save_filename=default_filename)

            if result:
                save_path = result[0] if isinstance(result, (list, tuple)) else result
                log_to_frontend(f"Saving chart data ({time_range_filter}) to: {save_path}", 'info')
                try:
                    with open(save_path, 'w', newline='', encoding='utf-8') as csvfile:
                        # Use defined fieldnames for consistency
                        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(data_to_export) # Write the list of dicts
                    log_to_frontend(f"Successfully exported {len(data_to_export)} points for range '{time_range_filter}'.", 'success')
                    return {"success": True, "message": f"Exported {len(data_to_export)} points to {save_path}"}
                except Exception as e:
                    log_to_frontend(f"Error writing export file: {e}", 'error')
                    logging.exception(f"Error writing export file {save_path}")
                    return {"success": False, "message": f"Error writing file: {e}"}
            else:
                log_to_frontend("Export cancelled by user.", 'info')
                return {"success": False, "message": "Export cancelled"}

        except Exception as e:
            log_to_frontend(f"Error preparing chart data for export: {e}", 'error')
            logging.exception("Error preparing chart data export")
            return {"success": False, "message": f"Error: {e}"}

    def export_all_data(self):
        """Exports the entire contents of the main sensor_data.csv file."""
        global window, DATA_FILE
        log_to_frontend("Export all history requested...", 'info')

        if not DATA_FILE.is_file() or DATA_FILE.stat().st_size == 0:
            log_to_frontend("No history data file found or file is empty.", 'warn')
            return {"success": False, "message": "No history data available"}

        try:
            # Ask user for save location
            default_filename = f"clue_full_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            result = window.create_file_dialog(webview.SAVE_DIALOG, directory=str(Path.home()), save_filename=default_filename)

            if result:
                save_path = result[0] if isinstance(result, (list, tuple)) else result
                log_to_frontend(f"Exporting full history from {DATA_FILE} to {save_path}", 'info')
                try:
                    # Simple file copy might be fastest for large files
                    import shutil
                    shutil.copyfile(DATA_FILE, save_path)
                    # Could also read/write row by row if transformation needed
                    log_to_frontend(f"Successfully exported full history.", 'success')
                    return {"success": True, "message": f"Full history exported to {save_path}"}
                except Exception as e:
                    log_to_frontend(f"Error copying history file: {e}", 'error')
                    logging.exception(f"Error copying {DATA_FILE} to {save_path}")
                    return {"success": False, "message": f"Error copying file: {e}"}
            else:
                log_to_frontend("Export cancelled by user.", 'info')
                return {"success": False, "message": "Export cancelled"}

        except Exception as e:
            log_to_frontend(f"Error during full export process: {e}", 'error')
            logging.exception("Error during full export")
            return {"success": False, "message": f"Error: {e}")

    # --- Analysis Engine API Methods ---

    def get_statistics(self, sensor, time_range=None):
        """
        Get statistical summary for a sensor.

        Args:
            sensor: Sensor name
            time_range: Optional time range filter (e.g., "1h", "24h", "7d")

        Returns:
            Dict with statistics
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Computing statistics for {sensor} (range: {time_range})...", 'info')
        result = analysis_engine.compute_statistics(sensor, time_range)
        if "error" not in result:
            log_to_frontend(f"Statistics computed: mean={result.get('mean', 'N/A')}", 'success')
        return result

    def get_correlation_matrix(self, time_range=None):
        """
        Get correlation matrix for all sensors.

        Args:
            time_range: Optional time range filter

        Returns:
            Dict with correlation matrix
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Computing correlation matrix (range: {time_range})...", 'info')
        result = analysis_engine.compute_correlation_matrix(time_range)
        if "error" not in result:
            log_to_frontend("Correlation matrix computed successfully.", 'success')
        return result

    def get_daily_pattern(self, sensor, date):
        """
        Get hourly pattern for a specific day.

        Args:
            sensor: Sensor name
            date: Date as ISO string (e.g., "2024-06-15")

        Returns:
            Dict with daily aggregates
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Computing daily pattern for {sensor} on {date}...", 'info')
        result = analysis_engine.compute_daily_aggregates(sensor, date)
        if "error" not in result:
            log_to_frontend("Daily pattern computed successfully.", 'success')
        return result

    def get_weekly_pattern(self, sensor, weeks_back=4):
        """
        Get hourly pattern across week.

        Args:
            sensor: Sensor name
            weeks_back: Number of weeks to analyze (default: 4)

        Returns:
            Dict with weekly pattern (168 data points)
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Computing weekly pattern for {sensor} ({weeks_back} weeks)...", 'info')
        result = analysis_engine.compute_weekly_pattern(sensor, weeks_back)
        if "error" not in result:
            log_to_frontend("Weekly pattern computed successfully.", 'success')
        return result

    def get_anomalies(self, sensor, threshold=2.5, time_range=None):
        """
        Detect and return anomalous readings.

        Args:
            sensor: Sensor name
            threshold: Z-score threshold for anomaly detection (default: 2.5)
            time_range: Optional time range filter

        Returns:
            Dict with detected anomalies
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Detecting anomalies for {sensor} (threshold: {threshold})...", 'info')
        result = analysis_engine.detect_anomalies(sensor, threshold, time_range)
        if "error" not in result:
            count = result.get('total_count', 0)
            log_to_frontend(f"Found {count} anomalies.", 'success')
        return result

    def get_scatter_data(self, sensor_x, sensor_y, time_range=None, max_points=1000):
        """
        Get scatter plot data for two sensors.

        Args:
            sensor_x: X-axis sensor
            sensor_y: Y-axis sensor
            time_range: Optional time range filter
            max_points: Maximum points to return (default: 1000)

        Returns:
            Dict with scatter plot data
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Computing scatter data: {sensor_x} vs {sensor_y}...", 'info')
        result = analysis_engine.compute_scatter_data(sensor_x, sensor_y, time_range, max_points)
        if "error" not in result:
            count = result.get('count', 0)
            log_to_frontend(f"Scatter data computed: {count} points.", 'success')
        return result

    def compare_periods(self, sensor, period1, period2):
        """
        Compare statistics between two time periods.

        Args:
            sensor: Sensor name
            period1: First time period (e.g., "24h" or dict with start/end)
            period2: Second time period

        Returns:
            Dict with comparison statistics
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend(f"Comparing periods for {sensor}...", 'info')
        result = analysis_engine.compare_periods(sensor, period1, period2)
        if "error" not in result:
            log_to_frontend("Period comparison completed.", 'success')
        return result

    def get_data_summary(self):
        """
        Get overall summary of available data.

        Returns:
            Dict with data summary (date range, record count, sensors)
        """
        global analysis_engine
        if not analysis_engine:
            return {"error": "Analysis engine not initialized"}

        log_to_frontend("Getting data summary...", 'info')
        result = analysis_engine.get_data_summary()
        if "error" not in result:
            records = result.get('total_records', 0)
            days = result.get('date_range', {}).get('days', 0)
            log_to_frontend(f"Data summary: {records} records over {days} days.", 'success')
        return result

# --- Main Application Setup (Remove Debug Prints) ---
if __name__ == '__main__':
    # print("DEBUG: Starting main execution block...")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # print("DEBUG: Log and data directories ensured.")
        logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        logging.info("--- Gateway Webview Application Started ---")
        # print("DEBUG: Logging configured.")
    except Exception as e:
        print(f"FATAL: Error setting up directories or logging: {e}") # Keep fatal print
        sys.exit(1)

    # Initialize Analysis Engine
    try:
        analysis_engine = AnalysisEngine(csv_filepath=DATA_FILE)
        logging.info("Analysis Engine initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Analysis Engine: {e}")
        print(f"WARNING: Analysis Engine initialization failed: {e}")
        # Continue anyway, analysis features will return errors

    current_clue_interval = 30
    # print("DEBUG: Creating Api instance...")
    api = Api()
    # print("DEBUG: Api instance created.")

    try:
        # print("DEBUG: Calling webview.create_window()...")
        window = webview.create_window(
            'CLUE Gateway',
            'index.html',
            js_api=api,
            width=1000,
            height=750,
            resizable=True
        )
        # print("DEBUG: webview.create_window() finished.")
    except Exception as e:
        print(f"FATAL: Error creating webview window: {e}") # Keep fatal print
        logging.exception("FATAL: Error creating webview window")
        sys.exit(1)

    # print("DEBUG: Calling initialize_aio_client() AFTER window creation...")
    aio_init_success, aio_final_status_text = initialize_aio_client()
    # print(f"DEBUG: initialize_aio_client() finished. Stored AIO Status: {initial_aio_status_text}")
    # print(f"DEBUG: Setting final AIO status UI before webview.start(): {aio_final_status_text}")
    status_type = 'success' if aio_init_success else 'error' if "Error" in aio_final_status_text else 'warn'
    set_aio_status(aio_final_status_text, status_type)
    # print("DEBUG: Final AIO status set.")

    def on_closing():
        logging.info("Window closing signal received.")
        # print("DEBUG: On closing called.")
        api.disconnect()

    try:
        # print("DEBUG: Calling webview.start()...")
        webview.start(on_closing, debug=True)
        # print("DEBUG: webview.start() finished.")
    except Exception as e:
        print(f"FATAL: Error starting webview: {e}") # Keep fatal print
        logging.exception("FATAL: Error starting webview")
        sys.exit(1)

    logging.info("--- Gateway Webview Application Finished ---")
    # print("DEBUG: Application finished normally.")