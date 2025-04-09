// script.js

// DOM Elements
const portSelect = document.getElementById('port-select');
const refreshBtn = document.getElementById('refresh-btn');
const connectBtn = document.getElementById('connect-btn');
const disconnectBtn = document.getElementById('disconnect-btn');
const logArea = document.getElementById('log-area');
const statusBar = document.getElementById('status-bar');
const intervalControlDiv = document.getElementById('interval-control');
const intervalInput = document.getElementById('interval-input');
const setIntervalBtn = document.getElementById('set-interval-btn');
const chartCanvas = document.getElementById('sensorChart');
const statusBarText = document.getElementById('status-text'); // Target status text span
const timeRangeSelect = document.getElementById('time-range-select');
const timeRangeSelectorDiv = document.getElementById('time-range-selector');
const aioStatusText = document.getElementById('aio-status-text'); // ADDED
const exportChartBtn = document.getElementById('export-chart-btn');
const exportAllBtn = document.getElementById('export-all-btn');
const dataTableBody = document.getElementById('data-table-body'); // ADDED

// State
let selectedPort = null;
let isConnected = false;
let sensorChart = null; // Chart.js instance
const MAX_CHART_POINTS = 60; // Max points to show on chart
let selectedTimeRange = '1h'; // Default value
const MAX_TABLE_ROWS = 50; // Max rows to keep in the recent readings table

// --- Chart Initialization ---
function initializeChart(initialData) {
    if (sensorChart) {
        sensorChart.destroy(); // Destroy previous chart if reconnecting
    }
    const ctx = chartCanvas.getContext('2d');

    // Check if initialData and its properties are valid
    const labels = initialData?.labels || [];
    const datasets = initialData?.datasets || {};
    const temp = datasets.temperature || [];
    const humidity = datasets.humidity || [];
    const pressure = datasets.pressure || [];
    const light = datasets.light || [];
    const sound = datasets.sound || [];


    sensorChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels, // Timestamps
            datasets: [
                {
                    label: 'Temperature (°F)',
                    data: temp,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    yAxisID: 'y', // Use the primary y-axis
                    tension: 0.1
                },
                {
                    label: 'Humidity (%)',
                    data: humidity,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    yAxisID: 'y1', // Use the secondary y-axis
                     tension: 0.1
                },
                 {
                    label: 'Pressure (hPa)',
                    data: pressure,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    yAxisID: 'y2', // Use a third y-axis
                     tension: 0.1,
                     hidden: true // Start hidden
                },
                 {
                    label: 'Light',
                    data: light,
                    borderColor: 'rgb(255, 205, 86)',
                    backgroundColor: 'rgba(255, 205, 86, 0.5)',
                    yAxisID: 'y3', // Use a fourth y-axis
                     tension: 0.1,
                     hidden: true // Start hidden
                },
                 {
                    label: 'Sound Level',
                    data: sound,
                    borderColor: 'rgb(153, 102, 255)',
                    backgroundColor: 'rgba(153, 102, 255, 0.5)',
                    yAxisID: 'y4', // Use a fifth y-axis
                     tension: 0.1,
                     hidden: true // Start hidden
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                 mode: 'index', // Show tooltips for all datasets at that index
                 intersect: false,
             },
             stacked: false,
            scales: {
                x: {
                    type: 'time',
                     time: {
                         // Luxon format required by Chart.js v3+ with adapter
                        // tooltipFormat: 'YYYY-MM-DD HH:mm:ss',
                         unit: 'minute' // Adjust based on expected data frequency
                     },
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: { // Primary axis (Temperature)
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temperature (°F)'
                     }
                },
                 y1: { // Secondary axis (Humidity)
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                         display: true,
                         text: 'Humidity (%)'
                    },
                    grid: { // Only draw grid for primary axis
                         drawOnChartArea: false,
                    },
                 },
                  y2: { // Third axis (Pressure)
                    type: 'linear',
                    display: false,
                    position: 'right',
                    title: {
                         display: true,
                         text: 'Pressure (hPa)'
                    },
                    grid: { drawOnChartArea: false },
                 },
                  y3: { // Fourth axis (Light)
                    type: 'linear',
                    display: false,
                    position: 'right',
                    title: {
                         display: true,
                         text: 'Light'
                    },
                    grid: { drawOnChartArea: false },
                 },
                  y4: { // Fifth axis (Sound)
                    type: 'linear',
                    display: false,
                    position: 'right',
                    title: {
                         display: true,
                         text: 'Sound Level'
                    },
                    grid: { drawOnChartArea: false },
                 },
            },
             plugins: {
                 legend: {
                     position: 'top',
                     onClick: function(e, legendItem, legend) {
                        // 1. Default legend click behavior
                        Chart.defaults.plugins.legend.onClick.call(this, e, legendItem, legend);

                        // 2. Update corresponding Y-axis visibility
                        const chart = legend.chart;
                        const datasetIndex = legendItem.datasetIndex;
                        const dataset = chart.data.datasets[datasetIndex];
                        const yAxisID = dataset.yAxisID;

                        if (yAxisID && chart.options.scales[yAxisID]) {
                            // legendItem.hidden reflects the state *after* the click
                            chart.options.scales[yAxisID].display = !legendItem.hidden;
                            // Optional: Log the change
                            // console.log(`JS: Toggled axis ${yAxisID} display to ${!legendItem.hidden}`);
                        }

                        // 3. Update the chart to apply axis changes
                        chart.update();
                    }
                 },
                 title: { display: true, text: 'Live Sensor Data' }
             }
        }
    });
    console.log("JS: Chart initialized with dynamic axis visibility.");
}

// --- Data Table Functions ---
function addTableRow(dataPoint, prepend = true) {
    if (!dataTableBody || !dataPoint) return;

    const row = dataTableBody.insertRow(prepend ? 0 : -1); // Insert at top (0) or bottom (-1)

    // Format timestamp (optional: format more nicely)
    let displayTime = dataPoint.gw_timestamp || dataPoint.label || '';
    if (displayTime) {
        try {
            // Attempt to show just the time if it's recent, otherwise date+time
            const dt = new Date(displayTime);
            const now = new Date();
            if (dt.toDateString() === now.toDateString()) {
                displayTime = dt.toLocaleTimeString(); // Just time if today
            } else {
                displayTime = dt.toLocaleString(); // Date and time if older
            }
        } catch (e) { /* Ignore formatting errors, use original string */ }
    }

    // Create cells
    const cellTime = row.insertCell();
    const cellTemp = row.insertCell();
    const cellHum = row.insertCell();
    const cellPress = row.insertCell();
    const cellLight = row.insertCell();
    const cellSound = row.insertCell();
    const cellColor = row.insertCell();

    // Populate cells (handle null/undefined)
    cellTime.textContent = displayTime;
    cellTemp.textContent = dataPoint.temperature_sht ?? '--';
    cellHum.textContent = dataPoint.humidity ?? '--';
    cellPress.textContent = dataPoint.pressure ?? '--';
    cellLight.textContent = dataPoint.light ?? '--';
    cellSound.textContent = dataPoint.sound_level ?? '--';
    cellColor.textContent = ''; // Clear text content
    if (dataPoint.color_hex && dataPoint.color_hex.startsWith('#')) {
         // cellColor.style.display = 'flex'; // No need for flex if only swatch
         // cellColor.style.alignItems = 'center';
         const swatch = document.createElement('span');
         swatch.style.display = 'inline-block';
         swatch.style.width = '1.5em'; // Make swatch bigger
         swatch.style.height = '1.5em';
         swatch.style.backgroundColor = dataPoint.color_hex;
         // swatch.style.marginRight = '5px'; // Not needed if only swatch
         swatch.style.border = '1px solid #ccc';
         // cellColor.insertBefore(swatch, cellColor.firstChild);
         cellColor.appendChild(swatch); // Just add the swatch
         cellColor.style.textAlign = 'center'; // Center the swatch
    } else {
        cellColor.textContent = '--'; // Show placeholder if no valid hex
    }

    // Limit rows
    while (dataTableBody.rows.length > MAX_TABLE_ROWS) {
        dataTableBody.deleteRow(dataTableBody.rows.length - 1); // Remove oldest row (at the bottom)
    }
}

function initializeTable(rawDataList) {
    if (!dataTableBody) return;
    dataTableBody.innerHTML = ''; // Clear existing table rows

    if (!rawDataList || !Array.isArray(rawDataList) || rawDataList.length === 0) {
         console.warn("JS: No raw data provided for table initialization.");
         // Add placeholder row?
         const row = dataTableBody.insertRow();
         const cell = row.insertCell();
         cell.colSpan = 7; // Span all columns
         cell.textContent = "No historical data loaded for table.";
         cell.style.textAlign = "center";
         cell.style.fontStyle = "italic";
         cell.style.color = "#888";
         return;
    }

    // Use the rawDataList directly
    rawDataList.forEach(point => { // Iterate oldest to newest
         addTableRow(point, true); // Prepend rows (newest will end up at top)
     });
}

// --- Functions to interact with Python API ---
async function refreshPorts() {
    console.log("JS: Requesting port list from Python...");
    try {
        const ports = await window.pywebview.api.list_serial_ports();
        console.log("JS: Received ports", ports);
        portSelect.innerHTML = ''; // Clear existing options
        if (ports && ports.length > 0) {
            ports.forEach(port => {
                const option = document.createElement('option');
                option.value = port.device;
                option.textContent = `${port.device} - ${port.description || 'No description'}`;
                portSelect.appendChild(option);
            });
            portSelect.disabled = false;
            connectBtn.disabled = isConnected; // Only enable if not connected
            selectedPort = portSelect.value;
        } else {
             addLogMessage("No serial ports found.", 'warn');
             const option = document.createElement('option');
             option.textContent = "No ports found";
             portSelect.appendChild(option);
             portSelect.disabled = true;
             connectBtn.disabled = true;
             selectedPort = null;
        }
    } catch (error) {
        console.error("JS: Error refreshing ports:", error);
        addLogMessage(`Error refreshing ports: ${error}`, 'error');
        portSelect.disabled = true;
        connectBtn.disabled = true;
    }
}

async function connectPort() {
     if (!selectedPort) { addLogMessage("Please select a port first.", 'warn'); return; }
     console.log(`JS: Requesting connect to ${selectedPort}`);
     addLogMessage(`Attempting to connect to ${selectedPort}...`, 'info');
     try {
         const result = await window.pywebview.api.connect(selectedPort);
         console.log("JS: Connect result", result);
         if (!result.success) { addLogMessage(`Connection failed: ${result.message}`, 'error'); }
         // Backend will call setConnectionState(true) via evaluate_js on success
     } catch (error) {
         console.error("JS: Error connecting:", error);
         addLogMessage(`Error connecting: ${error}`, 'error');
     }
 }

async function disconnectPort() {
     console.log("JS: Requesting disconnect");
     addLogMessage("Attempting to disconnect...", 'info');
     try {
         const result = await window.pywebview.api.disconnect();
         console.log("JS: Disconnect result", result);
         if (!result.success) { addLogMessage(`Disconnect failed: ${result.message}`, 'warn');}
         // Backend will call setConnectionState(false) via evaluate_js
     } catch (error) {
         console.error("JS: Error disconnecting:", error);
         addLogMessage(`Error disconnecting: ${error}`, 'error');
     }
 }

 async function setClueInterval() {
      const interval = intervalInput.value;
      if (!interval || parseInt(interval) < 1) {
          addLogMessage("Please enter a valid interval (>= 1 second).", 'warn');
          return;
      }
      console.log(`JS: Requesting set interval to ${interval}s`);
      addLogMessage(`Sending command to set interval to ${interval}s...`, 'info');
      try {
          const result = await window.pywebview.api.set_interval(interval);
          console.log("JS: Set interval result", result);
          if (result.success) {
              addLogMessage(result.message, 'info');
          } else {
              addLogMessage(`Failed to set interval: ${result.message}`, 'error');
          }
      } catch (error) {
          console.error("JS: Error setting interval:", error);
          addLogMessage(`Error setting interval: ${error}`, 'error');
      }
 }


// --- Functions called by Python via evaluate_js ---
function addLogMessage(message, level = 'info') {
    const p = document.createElement('p');
    p.textContent = message;
    p.className = level;
    logArea.appendChild(p);
    logArea.scrollTop = logArea.scrollHeight;
}

function updateStatus(statusText, statusType = 'info') {
    statusBarText.textContent = `Status: ${statusText}`; // Update only the text part
    statusBar.className = 'status-bar'; // Reset classes
    statusBar.classList.add(statusType);
}

// Update to handle countdown timer start/stop AND remove initial chart loading
function setConnectionState(connected) {
     console.log(`JS: Setting connection state: ${connected}`);
     isConnected = connected;
     connectBtn.disabled = connected || !selectedPort;
     disconnectBtn.disabled = !connected;
     portSelect.disabled = connected;
     refreshBtn.disabled = connected;
     intervalControlDiv.style.display = connected ? 'flex' : 'none';

     if (!connected) {
           // REMOVE stopCountdownTimer(true);
     } else {
          // Fallback load removed as initial load is now reliable in pywebviewready
          // if (!sensorChart) { ... }
     }
}

// Modified updateChart to also update the table
function updateChart(newDataPointJson) {
    if (!sensorChart) {
        console.warn("JS: updateChart called but chart is not initialized.");
        return;
    }
    try {
        const newDataPoint = JSON.parse(newDataPointJson);
        console.log("JS: Updating chart with data", newDataPoint);

        // Add to Table (prepend for newest at top)
        addTableRow(newDataPoint, true);

        // Add to Chart
        sensorChart.data.labels.push(newDataPoint.label);
        sensorChart.data.datasets[0].data.push(newDataPoint.temperature_sht);
        sensorChart.data.datasets[1].data.push(newDataPoint.humidity);
        sensorChart.data.datasets[2].data.push(newDataPoint.pressure);
        sensorChart.data.datasets[3].data.push(newDataPoint.light);
        sensorChart.data.datasets[4].data.push(newDataPoint.sound_level);

        // Limit chart points
        if (sensorChart.data.labels.length > MAX_CHART_POINTS) {
            sensorChart.data.labels.shift();
            sensorChart.data.datasets.forEach((dataset) => {
                dataset.data.shift();
            });
        }

        sensorChart.update();
    } catch (error) {
        console.error("JS: Error updating chart:", error, "Data received:", newDataPointJson);
        addLogMessage(`Error updating chart: ${error}`, 'error');
    }
}

// --- Function to Reload Chart Data & Table ---
function reloadChartWithTimeRange() {
    if (!window.pywebview || !window.pywebview.api) {
        console.error("JS: Pywebview API not ready for reload.");
        addLogMessage("Cannot reload chart: API not ready.", "error");
        return;
    }
    const newRange = timeRangeSelect.value;
    selectedTimeRange = newRange; // Update state variable
    console.log(`JS: Reloading chart data for time range: ${newRange}`);
    addLogMessage(`Reloading chart history & table for: ${timeRangeSelect.options[timeRangeSelect.selectedIndex].text}`, "info");

    // Disable selector during load?
    timeRangeSelect.disabled = true;

    window.pywebview.api.get_initial_chart_data(newRange)
        .then(response => { // Handle the new response structure
            console.log(`JS: Received reloaded data for range '${newRange}'`);
            initializeChart(response.chartData); // Use chartData for chart
            initializeTable(response.rawData); // Use rawData for table
            addLogMessage("Chart history & table reloaded.", "info");
        }).catch(err => {
            console.error(`JS: Error reloading chart data for range '${newRange}'`, err);
            addLogMessage(`Error reloading chart history: ${err}`, 'error');
            // Don't clear chart on error, keep existing view?
            // initializeChart(null);
        }).finally(() => {
            // Re-enable selector regardless of success/failure
            // Only disable if *not* currently connected? No, keep enabled.
            timeRangeSelect.disabled = false; // Re-enable selector
        });
}

// --- Event Listeners ---
refreshBtn.addEventListener('click', refreshPorts);
connectBtn.addEventListener('click', connectPort);
disconnectBtn.addEventListener('click', disconnectPort);
portSelect.addEventListener('change', (event) => {
     selectedPort = event.target.value;
     console.log(`JS: Port selection changed to ${selectedPort}`);
     if (!isConnected) { connectBtn.disabled = !selectedPort; }
});
// Listener for the new button
setIntervalBtn.addEventListener('click', setClueInterval);

// Update listener for time range changes to trigger reload
timeRangeSelect.addEventListener('change', reloadChartWithTimeRange);

// ADD Export Button Listeners
exportChartBtn.addEventListener('click', async () => {
    console.log("JS: Export Chart Data button clicked.");
    addLogMessage("Starting chart data export...", "info");
    try {
        // Pass the currently selected time range
        const result = await window.pywebview.api.export_chart_data(selectedTimeRange);
        if (result.success) {
            addLogMessage(result.message, "success");
        } else {
            addLogMessage(result.message, "warn");
        }
    } catch (err) {
        console.error("JS: Error calling export_chart_data", err);
        addLogMessage(`Export failed: ${err}`, "error");
    }
});

exportAllBtn.addEventListener('click', async () => {
    console.log("JS: Export All History button clicked.");
    addLogMessage("Starting full history export...", "info");
    try {
        const result = await window.pywebview.api.export_all_data();
        if (result.success) {
            addLogMessage(result.message, "success");
        } else {
            addLogMessage(result.message, "warn"); // Use warn for cancellations or known issues
        }
    } catch (err) {
        console.error("JS: Error calling export_all_data", err);
        addLogMessage(`Export failed: ${err}`, "error");
    }
});

// --- Initial Setup ---
window.addEventListener('pywebviewready', () => {
    console.log('JS: pywebview ready');
    selectedTimeRange = timeRangeSelect.value;
    console.log(`JS: Initial time range selected: ${selectedTimeRange}`);

    // --- Modified Initial Loading ---
    // 1. Get initial chart data
    window.pywebview.api.get_initial_chart_data(selectedTimeRange)
        .then(response => { // Handle the new response structure
            console.log(`JS: Received initial data on load for range '${selectedTimeRange}'`);
            initializeChart(response.chartData); // Use chartData for chart
            initializeTable(response.rawData); // Use rawData for table
        }).catch(err => {
            console.error("JS: Error getting initial chart data on load", err);
            addLogMessage(`Error loading chart data: ${err}`, 'error');
            initializeChart(null);
            initializeTable(null); // Clear table on error
        }).finally(() => {
            // 2. Get initial status *after* chart attempt
            console.log("JS: Attempting to get initial status info..."); // Added debug log
            window.pywebview.api.get_initial_status()
                .then(statusInfo => {
                    console.log("JS: Received initial status info", statusInfo);
                    updateStatus(statusInfo.main_status, statusInfo.main_status_type); // Update main status bar
                    updateAioStatus(statusInfo.aio_status, statusInfo.aio_status_type); // Update AIO status
                }).catch(err => {
                    console.error("JS: Error getting initial status info", err);
                    updateStatus("Error getting status", "error");
                    updateAioStatus("Error", "error");
                }).finally(() => {
                     // 3. Set initial connection state UI (buttons etc.)
                     console.log("JS: Setting final initial UI state..."); // Added debug log
                     setConnectionState(false);
                     // 4. Populate ports
                     refreshPorts();
                     // 5. Expose JS functions
                     window.addLogMessage = addLogMessage;
                     window.updateStatus = updateStatus;
                     window.setConnectionState = setConnectionState;
                     window.updateChart = updateChart;
                     window.updateAioStatus = updateAioStatus;
                     console.log("JS: pywebviewready setup complete."); // Added debug log
                });
        });
    // --- End Modified Initial Loading ---
});

// Remove setup from DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
     console.log("JS: DOMContentLoaded");
     // NO calls to pywebview API here anymore
});

// ADDED Function to update AIO status
function updateAioStatus(statusText, statusType = 'info') {
    if (aioStatusText) {
        aioStatusText.textContent = statusText;
        // Remove previous color classes if any
        aioStatusText.parentElement.classList.remove('info', 'warn', 'error', 'success');
        // Add new color class based on type (using parent styling)
        if (statusType === 'error') {
            aioStatusText.parentElement.style.color = '#dc3545'; // Red
        } else if (statusType === 'warn') {
            aioStatusText.parentElement.style.color = '#ffc107'; // Yellow/Orange
        } else if (statusType === 'success') {
            aioStatusText.parentElement.style.color = '#28a745'; // Green
        } else {
            aioStatusText.parentElement.style.color = '#555'; // Default grey
        }
    }
}