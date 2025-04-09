# Adafruit CLUE Environmental Data Logger - CircuitPython Code (Serial Output Version)

import time
import board
import busio
import storage
import os
import json
import rtc
# import adafruit_datetime # Not strictly needed if only using rtc.RTC().datetime
# import _bleio              # REMOVED
# import adafruit_ble        # REMOVED
import audiobusio
import audiocore
import array
import math
import supervisor # For checking serial input
import sys       # For reading serial input
# from adafruit_ble.advertising.standard import ProvideServicesAdvertisement # REMOVED
# from adafruit_ble.services import Service                               # REMOVED
# from adafruit_ble.characteristics import Characteristic                 # REMOVED
# from adafruit_ble.characteristics.stream import StreamOut, StreamIn       # REMOVED
# from adafruit_ble.uuid import VendorUUID, StandardUUID                # REMOVED

# --- Sensor Libraries ---
# Import specific sensor libraries (ensure these are in the lib folder)
try:
    import adafruit_lsm6ds
except ImportError:
    print("LSM6DS library not found.")
    adafruit_lsm6ds = None

try:
    import adafruit_lis3mdl              # Magnetometer
except ImportError:
    print("LIS3MDL library not found.")
    adafruit_lis3mdl = None

try:
    from adafruit_apds9960.apds9960 import APDS9960 # Proximity, Light, Color, Gesture
except ImportError:
    print("APDS9960 library not found.")
    APDS9960 = None

try:
    import adafruit_sht31d               # Humidity, Temp
except ImportError:
    print("SHT31D library not found.")
    adafruit_sht31d = None

try:
    import adafruit_bmp280               # Pressure, Temp, Altitude
except ImportError:
    print("BMP280 library not found.")
    adafruit_bmp280 = None

# --- Configuration ---
# Default interval, can be changed by gateway command
DATA_CAPTURE_INTERVAL_SECONDS = 30  # Start with 30 seconds default
# BUFFER_FILE = "/data_buffer.jsonl" # REMOVED
# MAX_BUFFER_SIZE_BYTES = 1 * 1024 * 1024 # REMOVED

# --- Global Variables ---
# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize Sensors (add error handling for missing sensors)
lsm6ds = None
if adafruit_lsm6ds:
    try:
        # Try accessing the class via the imported module name
        lsm6ds = adafruit_lsm6ds.LSM6DS33(i2c) # Access class via module
        print("Successfully initialized LSM6DS33.")
    except AttributeError: # Catch if LSM6DS33 doesn't exist in the module
         print("LSM6DS33 class not found within adafruit_lsm6ds module.")
    except Exception as e:
        print(f"Failed to initialize LSM6DS33: {e}")
else:
    print("Skipping LSM6DS initialization because import failed.")

lis3mdl = None
if adafruit_lis3mdl:
    try:
        lis3mdl = adafruit_lis3mdl.LIS3MDL(i2c)
        print("Successfully initialized LIS3MDL.")
    except Exception as e:
        print(f"Failed to initialize LIS3MDL: {e}")

apds9960 = None
if APDS9960:
    try:
        apds9960 = APDS9960(i2c)
        apds9960.enable_proximity = True
        apds9960.enable_color = True
        # apds9960.enable_gesture = True # Disable gesture unless needed (saves power)
        apds9960.enable_light = True
        print("Successfully initialized APDS9960.")
    except Exception as e:
        print(f"Failed to initialize APDS9960: {e}")

sht31d = None
if adafruit_sht31d:
    try:
        sht31d = adafruit_sht31d.SHT31D(i2c)
        print("Successfully initialized SHT31D.")
    except Exception as e:
        print(f"Failed to initialize SHT31D: {e}")

bmp280 = None
if adafruit_bmp280:
    try:
        bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
        # bmp280.sea_level_pressure = 1013.25 # Optional
        print("Successfully initialized BMP280.")
    except Exception as e:
        print(f"Failed to initialize BMP280: {e}")

# Initialize Microphone
mic = None
samples = None
try:
    mic = audiobusio.PDMIn(
        board.MICROPHONE_CLOCK,
        board.MICROPHONE_DATA,
        sample_rate=16000,
        bit_depth=16
    )
    samples = array.array('H', [0] * 160) # 10ms buffer
    print("Successfully initialized PDMIn Microphone.")
except Exception as e:
    print(f"Failed to initialize PDMIn microphone: {e}")

# Initialize Real-Time Clock (RTC)
# RTC time is needed for timestamps if the gateway isn't setting it.
# CLUE doesn't have a battery-backed RTC, so it resets on power loss.
r = rtc.RTC()
try:
    # Set the RTC source explicitly (good practice)
    rtc.set_time_source(r)
    print(f"Initial RTC time: {r.datetime}")
except Exception as e:
    print(f"Error setting RTC source: {e}")


# --- BLE Setup ---         # REMOVED ENTIRE SECTION
# --- Global BLE State ---    # REMOVED
# --- Buffer Functions ---    # REMOVED
# --- ACK Function ---        # REMOVED

# --- Helper Functions ---

def scale_clamp(value, sensor_max, target_max=255):
    """Scales sensor value to 0-target_max and clamps."""
    try:
        scaled = int(value / sensor_max * target_max)
        return max(0, min(target_max, scaled)) # Clamp between 0 and target_max
    except (TypeError, ValueError):
        return 0 # Return 0 if value is invalid

def rgb_to_hex(r, g, b):
    """Converts raw RGB sensor values to a hex color string."""
    assumed_max = 786 # MODIFIED from 4096 based on observed raw values
    r_scaled = scale_clamp(r, assumed_max)
    g_scaled = scale_clamp(g, assumed_max)
    b_scaled = scale_clamp(b, assumed_max)
    return f"#{r_scaled:02X}{g_scaled:02X}{b_scaled:02X}"

def get_sound_level(num_samples=160):
    """Samples the microphone and returns the RMS sound level."""
    if not mic or not samples:
        return None
    try:
        mic.record(samples, len(samples))
        sum_sq = 0
        for s in samples:
            sample_signed = s - 32768 # Convert unsigned 16-bit to signed
            sum_sq += sample_signed * sample_signed
        mean_sq = sum_sq / num_samples
        rms = math.sqrt(mean_sq)
        return round(rms)
    except Exception as e:
        print(f"Error reading microphone: {e}")
        return None

def get_sensor_data():
    """Reads data from required sensors and returns a dictionary."""
    data = {}
    monotonic_time = time.monotonic() # Use monotonic time for intervals
    rtc_time = r.datetime # Get current RTC time

    # Format RTC time as ISO 8601 string if RTC is plausible (year > 2000)
    try:
        if rtc_time.tm_year > 2000:
             data["timestamp_iso"] = f"{rtc_time.tm_year:04d}-{rtc_time.tm_mon:02d}-{rtc_time.tm_mday:02d}T{rtc_time.tm_hour:02d}:{rtc_time.tm_min:02d}:{rtc_time.tm_sec:02d}Z"
        else:
             data["timestamp_iso"] = None # Indicate RTC not set reliably
    except Exception as e:
        print(f"Error formatting RTC time: {e}")
        data["timestamp_iso"] = None

    data["timestamp_monotonic"] = monotonic_time # Keep monotonic time

    # --- Read only the required sensors ---

    # Read APDS9960 for Color and Light
    if apds9960:
        try:
            r_val, g_val, b_val, c_val = apds9960.color_data
            # print(f"Raw RGB: r={r_val}, g={g_val}, b={b_val} | Clear: c={c_val}") # REMOVED/COMMENTED OUT Debug Print
            data["color_hex"] = rgb_to_hex(r_val, g_val, b_val)
            data["light"] = c_val
        except Exception as e:
            print(f"Error reading APDS9960: {e}")

    # Read SHT31D for Temperature and Humidity
    if sht31d:
        try:
            data["humidity"] = sht31d.relative_humidity
            data["temperature_sht"] = sht31d.temperature
        except Exception as e:
            print(f"Error reading SHT31D: {e}")

    # Read BMP280 for Pressure
    if bmp280:
        try:
            data["pressure"] = bmp280.pressure
        except Exception as e:
            print(f"Error reading BMP280: {e}")

    # Read Sound Level from Microphone
    data["sound_level"] = get_sound_level()

    # --- Skip unused sensors ---
    # if lsm6ds:
    #     try: ... # Skip LSM6DS
    # if lis3mdl:
    #     try: ... # Skip LIS3MDL

    # Round floats for the values we did collect
    for key, value in data.items():
        if isinstance(value, float):
            try:
                data[key] = round(value, 2) # Adjust precision if needed
            except OverflowError:
                 data[key] = None # Handle potential NaN/Inf values
                 print(f"Warning: OverflowError rounding {key}. Setting to None.")

    return data

# --- Function to handle incoming commands ---
serial_buffer = ""
def handle_serial_commands():
    global DATA_CAPTURE_INTERVAL_SECONDS, serial_buffer
    # Check if there's any data waiting in the USB CDC serial buffer
    num_bytes = supervisor.runtime.serial_bytes_available
    if num_bytes > 0:
        # print(f"-- DBG: Serial bytes available: {num_bytes}")
        # Read only the available bytes
        new_data = sys.stdin.read(num_bytes)
        # print(f"-- DBG: Read data: {new_data!r}") # Use repr to see control chars
        if new_data:
             serial_buffer += new_data

        # print("-- DBG: Processing serial buffer loop...")
        # Process complete lines (ending in newline)
        while '\n' in serial_buffer:
            line, serial_buffer = serial_buffer.split('\n', 1)
            line = line.strip()
            # print(f"-- DBG: Processing line: {line!r}")
            if not line:
                # print("-- DBG: Skipping empty line.")
                continue
            try:
                command_data = json.loads(line)
                if isinstance(command_data, dict):
                    command = command_data.get("command")
                    value = command_data.get("value")
                    # print(f"-- DBG: Parsed command: {command}, value: {value}")

                    if command == "set_interval" and value is not None:
                        try:
                            new_interval = int(value)
                            if new_interval >= 1: # Basic validation
                                DATA_CAPTURE_INTERVAL_SECONDS = new_interval
                                print(f"COMMAND OK: Set data capture interval to {DATA_CAPTURE_INTERVAL_SECONDS} seconds")
                            else:
                                print(f"COMMAND ERR: Invalid interval value {new_interval}")
                        except ValueError:
                            print(f"COMMAND ERR: Interval value '{value}' is not a valid integer.")
                    else:
                         print(f"COMMAND ERR: Unknown or incomplete command: {command_data}")
                # else:
                    # print(f"-- DBG: Parsed JSON is not a dict: {command_data!r}")

            except json.JSONDecodeError:
                print(f"COMMAND ERR: Received non-JSON data: {line}")
            except Exception as e:
                 print(f"COMMAND ERR: Error processing command '{line}': {e}")
        # print("-- DBG: Exiting serial buffer loop.")

    # print("-- DBG: Exiting handle_serial_commands function.")

# --- Main Loop ---
print("\n--- Starting Data Logger (Serial Output Mode) ---")
print(f"Initial data capture interval: {DATA_CAPTURE_INTERVAL_SECONDS} seconds")
print("Sensor data will be printed as JSON strings over USB Serial.")
print("Listening for commands (e.g., {'command':'set_interval', 'value':10})")
print("-------------------------------------------------------\n")
last_capture_time = time.monotonic()
# loop_count = 0 # Removed loop counter

while True:
    # loop_count += 1
    # print(f"-- DBG: Main loop iteration {loop_count} --")

    # --- Check for commands frequently ---
    # print("-- DBG: Checking for serial commands...")
    try:
        handle_serial_commands()
    except Exception as e_serial:
        print(f"ERROR in handle_serial_commands: {e_serial}") # Keep this error print
    # print("-- DBG: Finished checking serial commands.")

    current_time = time.monotonic()

    # Check if it's time to capture data
    # print(f"-- DBG: Checking time... Now={current_time:.1f}, Last={last_capture_time:.1f}, Interval={DATA_CAPTURE_INTERVAL_SECONDS}")
    if current_time - last_capture_time >= DATA_CAPTURE_INTERVAL_SECONDS:
        last_capture_time = current_time
        # print(f"\nCapturing sensor data (Interval: {DATA_CAPTURE_INTERVAL_SECONDS}s)...") # <-- Commented out this line
        sensor_data = get_sensor_data()
        try:
            json_string = json.dumps(sensor_data)
            print(json_string)
        except Exception as e:
            print(f"Error converting/printing data to JSON: {e}")
    # else:
        # print("-- DBG: Not time to capture yet.")

    # Small delay
    # print("-- DBG: Main loop sleep.")
    time.sleep(0.1) # Restore original sleep time