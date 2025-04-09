# Adafruit CLUE Environmental Data Logger Project Plan

## Overall Goal

Capture all sensor data from an Adafruit CLUE device every 5 minutes, buffer it locally on the CLUE's flash storage using a FIFO strategy if the gateway is unavailable, transmit buffered and current data via Bluetooth LE to a computer gateway when connected, upload the data to Adafruit IO, and visualize it on an Adafruit IO Dashboard.

## Components

### 1. Adafruit CLUE (Data Collector & Buffer)

*   **Hardware:** Adafruit CLUE (nRF52840)
*   **Language:** CircuitPython
*   **Task:**
    *   Initialize onboard sensors (Temp, Humidity, Pressure, Light, Color, Proximity, Gesture, Accel/Gyro, Magnetometer).
    *   Initialize onboard flash filesystem (`storage` module).
    *   Initialize and manage the Real-Time Clock (RTC), syncing with the gateway when possible.
    *   Manage a buffer file (e.g., `data_buffer.jsonl`) on the flash drive using JSON Lines format.
    *   **Main Loop (every 5 mins):**
        *   Read sensor values & get timestamp from RTC.
        *   Attempt BLE connection to the computer gateway.
        *   **If connection successful:**
            *   **(Synchronization Phase):** Send buffered data (oldest first) from `data_buffer.jsonl`. Wait for an acknowledgement message from the gateway for each record *after* the gateway confirms successful upload to Adafruit IO, then delete the acknowledged record from the buffer file.
            *   **(Current Data Phase):** Send the current timestamped sensor reading. Wait for acknowledgement from the gateway (post-Adafruit IO upload).
            *   **(Optional Time Sync):** Receive current time from the gateway to re-sync the CLUE's RTC.
        *   **If connection fails:**
            *   Format the current timestamped sensor reading (e.g., as a JSON string).
            *   **Buffer Management (FIFO):** Check available flash storage. If insufficient space for the new reading, read and discard the oldest line(s) from `data_buffer.jsonl` until enough space is freed.
            *   Append the new reading as a new line to the `data_buffer.jsonl` file.
*   **Libraries:** Adafruit CircuitPython sensor libraries (LSM6DS3TR, LIS3MDL, APDS9960, SHT31D, BMP280, etc.), `_bleio`, `storage`, `os`, `json`, `rtc`, `time`, `adafruit_datetime`.

### 2. Computer (Gateway & Uploader)

*   **Hardware:** User's computer (macOS, Windows, or Linux) with Bluetooth LE capability and internet access.
*   **Language:** Python 3
*   **Task:**
    *   Run a script continuously in the background.
    *   Use a Bluetooth LE library (e.g., `bleak`) to listen for and accept connections from the specific Adafruit CLUE device.
    *   **On connection:**
        *   **(Synchronization Phase):** Receive historical data records from the CLUE's buffer. For each record received:
            *   Parse the data.
            *   Attempt to upload the data to the corresponding Adafruit IO feeds (using REST API or MQTT).
            *   *Only if the Adafruit IO upload is successful*, send an acknowledgement message back to the CLUE (e.g., containing the timestamp of the acknowledged record).
        *   **(Current Data Phase):** Receive the current data record from the CLUE.
            *   Parse the data.
            *   Attempt to upload to Adafruit IO.
            *   *Only if the Adafruit IO upload is successful*, send an acknowledgement back to the CLUE.
        *   **(Optional Time Sync):** Send the current accurate time back to the CLUE upon successful connection establishment or periodically.
*   **Libraries:** `bleak` (for BLE communication), `requests` (for Adafruit IO REST API) or `paho-mqtt` (for Adafruit IO MQTT), `asyncio` (likely needed for `bleak`), `json`, `datetime`.

### 3. Adafruit IO (Datastore & Visualization)

*   **Platform:** Adafruit IO ([https://io.adafruit.com/](https://io.adafruit.com/))
*   **Task:**
    *   Create an Adafruit IO account.
    *   Set up "Feeds" for each piece of sensor data to be stored (e.g., `temperature`, `humidity`, `pressure`, `light-level`, `accel-x`, `accel-y`, `accel-z`, `gyro-x`, `gyro-y`, `gyro-z`, `mag-x`, `mag-y`, `mag-z`, `color-r`, `color-g`, `color-b`, `proximity`, `gesture`).
    *   Obtain Adafruit IO Username and AIO Key for use in the gateway script.
    *   Create a "Dashboard" to visualize the data. Add blocks like line charts, gauges, indicators, etc., linked to the created feeds.

## Deviation from Original Plan: Communication Method

The initial project plan detailed using Bluetooth Low Energy (BLE) for communication between the Adafruit CLUE device and the computer gateway. The goal was wireless data transfer, including buffered data synchronization with acknowledgements.

However, during development, several challenges were encountered with the BLE approach:

1.  **Complexity:** Implementing reliable, acknowledged data transfer and buffer synchronization over BLE proved complex within the CircuitPython environment and the chosen gateway libraries (like `bleak`). Managing connection states, characteristics, and data streams required significant overhead.
2.  **Reliability:** Achieving consistent connections and data transfer without errors or stalls was difficult.
3.  **Debugging:** Debugging BLE interactions between the device and the gateway was time-consuming.

Due to these challenges, a decision was made to **deviate from the BLE plan and switch to USB Serial communication.**

**Current Implementation (Serial Communication):**

*   The CLUE device (`code_serial.py`) now runs a loop that reads sensors and prints the data as a JSON string to the USB Serial output.
*   It also listens for commands (like setting the interval) sent over Serial from the gateway.
*   The computer gateway (`gateway_webview.py`) connects directly to the CLUE's designated Serial port.
*   The gateway reads the incoming JSON data lines, processes them (adds timestamps, converts units), displays them in the web UI, appends them to a local CSV file, and uploads them to Adafruit IO.
*   The concept of onboard buffering on the CLUE was removed for simplicity in the Serial model, relying instead on the gateway application being active to capture and store data.

This Serial approach significantly simplified the communication logic, improved reliability, and made debugging more straightforward, while still achieving the core goals of data capture, logging, and cloud upload.

## Workflow Diagram

```mermaid
sequenceDiagram
    participant CLUE
    participant Computer (Gateway)
    participant Adafruit IO

    CLUE->>Computer (Gateway): Initial Connection (for RTC set)
    Computer (Gateway)->>CLUE: Send current time
    CLUE->>CLUE: Set RTC

    loop Every 5 minutes
        CLUE->>CLUE: Read sensors & get timestamp
        CLUE->>Computer (Gateway): Attempt BLE Connection
        alt Connection Successful
            CLUE->>CLUE: Read buffered data (if any)
            loop While buffered data exists
                CLUE->>Computer (Gateway): Send oldest buffered record
                Computer (Gateway)->>Adafruit IO: Upload buffered record
                alt Upload Successful
                    Computer (Gateway)->>CLUE: Send Acknowledgement (e.g., timestamp)
                    CLUE->>CLUE: Delete acknowledged record from buffer
                else Upload Failed
                    Computer (Gateway)->>CLUE: Send Negative Acknowledgement / Timeout
                    Note over CLUE, Computer (Gateway): Record remains in buffer, retry later
                    break # Exit buffer loop for now
                end
            end
            CLUE->>Computer (Gateway): Send current sensor record
            Computer (Gateway)->>Adafruit IO: Upload current record
            alt Upload Successful
                 Computer (Gateway)->>CLUE: Send Acknowledgement
            else Upload Failed
                 Note over CLUE, Computer (Gateway): Current record NOT buffered (or add logic to buffer it now)
            end
            Computer (Gateway)->>CLUE: (Optional) Send current time for RTC sync
        else Connection Failed
            CLUE->>CLUE: Format current record
            CLUE->>CLUE: Check available space for record
            alt Insufficient Space
                CLUE->>CLUE: Read & discard oldest record(s) from buffer until space is sufficient (FIFO)
            end
            CLUE->>CLUE: Append current record to buffer file (data_buffer.jsonl)
        end
    end