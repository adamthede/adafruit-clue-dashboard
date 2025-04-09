# Adafruit CLUE Sensor Data Gateway & Web Viewer

This project provides a Python application that acts as a gateway for an Adafruit CLUE board running a compatible CircuitPython script. It receives sensor data (temperature, humidity, pressure, light, sound, color) over USB Serial, stores it locally, uploads it to Adafruit IO, and displays it in a local web-based graphical user interface (GUI) using `pywebview`.

## Features

*   **Serial Connection:** Connects to the CLUE device via a selected USB serial port.
*   **Web GUI:** Cross-platform GUI built with HTML, CSS, JavaScript, and `pywebview`.
*   **Live Data Chart:** Visualizes incoming sensor data using Chart.js.
*   **Tabular Data View:** Displays recent readings in a scrollable table.
*   **Adafruit IO Integration:** Uploads sensor data to configured Adafruit IO feeds.
*   **Persistent Local Storage:** Saves all received sensor data to a local CSV file (`sensor_data.csv`).
*   **Historical Data Loading:** Loads and displays historical data from the CSV file upon startup.
*   **Time Range Filtering:** Allows selecting the time range of historical data to load (Last Hour, 6 Hours, 24 Hours, 7 Days, 30 Days, All).
*   **Data Export:**
    *   Export currently viewed chart/table data (based on time range selection) to a CSV file.
    *   Export the *entire* historical data from `sensor_data.csv` to a new CSV file.
*   **Interval Control:** Sends commands to the CLUE device to change its data capture interval.
*   **Status Indicators:** Shows connection status and Adafruit IO status in the UI.
*   **Configuration File:** Reads Adafruit IO credentials from a separate `config.ini` file for security.
*   **Logging:** Logs application events and errors to a file.

## Requirements

1.  **Hardware:**
    *   Adafruit CLUE nRF52840 Express board.
    *   USB cable for connection.
2.  **Software (CLUE):**
    *   CircuitPython firmware installed on the CLUE.
    *   Required CircuitPython libraries (see `code_serial.py` imports) copied to the CLUE's `lib` folder.
    *   The provided `code_serial.py` script running on the CLUE.
3.  **Software (Computer):**
    *   Python 3.7+
    *   `pip` (Python package installer)

## Installation & Setup

1.  **Clone the Repository (Optional):**
    ```bash
    git clone <your-repository-url>
    cd adafruit-clue
    ```
2.  **Create Virtual Environment:** It's highly recommended to use a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: On macOS, `pywebview[cocoa]` is needed. For Windows, you might need `pywebview[edgechromium]` or `pywebview[mshtml]`. For Linux, `pywebview[gtk]` is common. Adjust `requirements.txt` accordingly or install `pywebview` and let it choose.)*
4.  **Prepare CLUE:**
    *   Ensure CircuitPython and necessary sensor libraries are on your CLUE board.
    *   Copy the `code_serial.py` file to the root directory of your CLUE's `CIRCUITPY` drive.
5.  **Configure Adafruit IO Credentials:**
    *   Create a file named `config.ini` in the project's root directory (where `gateway_webview.py` is).
    *   Add your Adafruit IO credentials to `config.ini`:
      ```ini
      [AdafruitIO]
      username = YOUR_AIO_USERNAME
      key = YOUR_AIO_KEY
      ```
    *   **Important:** Add `config.ini` to your `.gitignore` file to avoid committing credentials. The included `.gitignore` should already list it.
6.  **Set Up Adafruit IO Feeds:**
    *   Log in to your Adafruit IO account ([https://io.adafruit.com](https://io.adafruit.com)).
    *   Navigate to "Feeds".
    *   Ensure you have feeds created with the following **exact** keys (names can be different, but the keys must match):
        *   `temperature-sht`
        *   `humidity`
        *   `pressure`
        *   `light`
        *   `sound-level`
        *   `color-hex`
    *   If any of these feeds do not exist, create them. The application will fail to upload data for missing feed keys.

## Running the Application

1.  **Activate Virtual Environment:**
    ```bash
    source venv/bin/activate # Or `venv\Scripts\activate` on Windows
    ```
2.  **Connect CLUE:** Plug your CLUE board into your computer via USB.
3.  **Run the Script:**
    ```bash
    python gateway_webview.py
    ```

## Usage

1.  **Select Port:** Choose the correct serial port corresponding to your CLUE board from the dropdown menu. Click "Refresh" if it doesn't appear initially.
2.  **Select History Range:** Choose how much past data you want to load from the CSV file into the chart and table.
3.  **Connect:** Click the "Connect" button. The status should update, and live data should start appearing in the chart and table.
4.  **Set Interval:** Once connected, you can change the data capture interval (in seconds) on the CLUE device using the "Capture Interval" input and "Set Interval" button.
5.  **Interact with Chart:** Click items in the chart legend to toggle the visibility of specific data series and their corresponding Y-axes.
6.  **View History:** Change the "Load History" dropdown at any time to reload the chart and table with data from a different historical period.
7.  **Export Data:** Use the "Export Chart Data" button to save the currently displayed historical data, or "Export All History" to save the complete data log.
8.  **Disconnect:** Click the "Disconnect" button to stop communication with the CLUE.

## Data and Log Files

*   **Configuration:** `config.ini` (in the project directory).
*   **Persistent Data:** `sensor_data.csv` is stored in the standard application support directory:
    *   macOS: `~/Library/Application Support/ClueGatewayWebview/`
    *   Linux: `~/.local/share/ClueGatewayWebview/` (typically)
    *   Windows: `%APPDATA%\ClueGatewayWebview\` (typically `C:\\Users\\<user>\\AppData\\Roaming\\ClueGatewayWebview\\`)
*   **Log Files:** `gateway_webview.log` is stored in the standard application log directory:
    *   macOS: `~/Library/Logs/ClueGatewayWebview/`
    *   Linux: `~/.cache/ClueGatewayWebview/logs/` (or near data dir)
    *   Windows: `%LOCALAPPDATA%\ClueGatewayWebview\logs\` (typically `C:\\Users\\<user>\\AppData\\Local\\ClueGatewayWebview\\logs\\`)

## Packaging (Optional)

You can create a standalone executable using `pyinstaller`.

1.  **Install `pyinstaller`:**
    ```bash
    pip install pyinstaller
    ```
2.  **Run `pyinstaller`:** (Adjust `--windowed` or remove for non-macOS if needed)
    ```bash
    pyinstaller --noconfirm --log-level=INFO \
      --windowed \
      --add-data "index.html:." \
      --add-data "script.js:." \
      --name "CLUE_Gateway" \
      gateway_webview.py
    ```
3.  The application bundle (e.g., `CLUE_Gateway.app`) will be in the `dist` folder.
4.  When run for the first time, the packaged app will look for `config.ini` in the Application Support directory. If not found, it will create a default one there for you to edit.

## Future Enhancements

*   Integrate alternative data stores (e.g., InfluxDB, local databases).
*   Add chart zoom/pan capabilities.
*   Implement automatic serial reconnection.
*   Refine UI/UX further.
