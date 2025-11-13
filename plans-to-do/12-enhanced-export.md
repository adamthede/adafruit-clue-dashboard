# Implementation Plan: Enhanced Export with Reports

**Priority:** MEDIUM
**Phase:** 4
**Estimated Effort:** 3-4 hours
**Dependencies:** 02-tabbed-ui-architecture, multiple analysis features

---

## Overview

Transform the basic CSV export into a comprehensive reporting system that exports data along with visualizations, statistics, and insights in multiple formats (CSV, JSON, PDF reports).

---

## Goals

1. **Multiple Formats**: CSV, JSON, PDF report
2. **Include Visualizations**: Export charts as images in reports
3. **Statistical Summaries**: Include computed stats
4. **Customizable**: Select which data/metrics to include
5. **Professional**: PDF reports are presentation-ready

---

## Export Options

### Enhanced CSV Export
```
- Filter by time range
- Select specific sensors
- Include computed columns (z-scores, moving averages)
- Custom filename with timestamp
```

### JSON Export
```json
{
  "metadata": {
    "export_date": "2024-07-15T10:30:00",
    "time_range": "2024-06-01 to 2024-07-15",
    "sensors": ["temperature_sht", "humidity"]
  },
  "statistics": {
    "temperature_sht": {"mean": 72.3, "min": 68.5, ...},
    "humidity": {"mean": 45.2, "min": 38.1, ...}
  },
  "data": [
    {"timestamp": "2024-06-01T00:00:00", "temperature_sht": 71.2, ...},
    ...
  ],
  "insights": [
    "Temperature averaged 2.5°F higher than last month",
    ...
  ]
}
```

### PDF Report
```
┌────────────────────────────────────┐
│  Environmental Monitoring Report   │
│  June 1 - July 15, 2024           │
├────────────────────────────────────┤
│                                    │
│  Executive Summary                 │
│  • 43 days monitored               │
│  • 123,840 data points             │
│  • 6 sensors active                │
│                                    │
│  Temperature Summary               │
│  [Chart image]                     │
│  Average: 72.3°F                   │
│  Range: 68.5-76.2°F               │
│                                    │
│  Key Insights                      │
│  • Temperature was stable          │
│  • 3 anomalies detected            │
│                                    │
│  [More charts and data...]         │
└────────────────────────────────────┘
```

---

## Implementation

### Backend (gateway_webview.py)
```python
import json
from fpdf import FPDF  # or reportlab

class ReportGenerator:
    """Generate exportable reports"""

    def export_json(self, sensors, time_range, include_stats=True, include_insights=True):
        """Export data as structured JSON"""
        data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "time_range": time_range,
                "sensors": sensors
            }
        }

        # Add statistics
        if include_stats:
            data["statistics"] = {}
            for sensor in sensors:
                stats = analysis_engine.compute_statistics(sensor, time_range)
                data["statistics"][sensor] = stats

        # Add insights
        if include_insights:
            insights = analysis_engine.generate_insights(time_range)
            data["insights"] = [i["description"] for i in insights["insights"]]

        # Add raw data
        df = analysis_engine.load_data(time_range, sensors=sensors)
        data["data"] = df.to_dict('records')

        return json.dumps(data, indent=2)

    def export_pdf_report(self, time_range):
        """Generate PDF report with charts and statistics"""
        pdf = FPDF()
        pdf.add_page()

        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Environmental Monitoring Report', ln=True, align='C')

        # Date range
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Period: {time_range}', ln=True, align='C')

        pdf.ln(10)

        # Executive Summary
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Executive Summary', ln=True)

        pdf.set_font('Arial', '', 11)
        # Add summary stats...

        # Charts (save as temp images, insert into PDF)
        # Use matplotlib or Chart.js export

        # Statistics tables
        # ...

        return pdf.output(dest='S').encode('latin1')  # Return as bytes
```

### Frontend (js/export.js - new file)
```javascript
/**
 * Enhanced Export functionality
 */

function initializeExportTab() {
    setupExportControls();
}

function setupExportControls() {
    // CSV Export
    document.getElementById('export-csv-btn').addEventListener('click', async () => {
        const options = getExportOptions();
        const csv = await window.pywebview.api.export_csv(options);

        downloadFile(csv, 'data.csv', 'text/csv');
    });

    // JSON Export
    document.getElementById('export-json-btn').addEventListener('click', async () => {
        const options = getExportOptions();
        const json = await window.pywebview.api.export_json(options);

        downloadFile(json, 'data.json', 'application/json');
    });

    // PDF Report
    document.getElementById('export-pdf-btn').addEventListener('click', async () => {
        const options = getExportOptions();
        const pdfBytes = await window.pywebview.api.export_pdf(options);

        downloadFile(pdfBytes, 'report.pdf', 'application/pdf');
    });
}

function getExportOptions() {
    return {
        sensors: getSelectedSensors(),
        time_range: document.getElementById('export-time-range').value,
        include_stats: document.getElementById('include-stats').checked,
        include_insights: document.getElementById('include-insights').checked,
        include_charts: document.getElementById('include-charts').checked
    };
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

window.initializeExportTab = initializeExportTab;
```

---

## Success Criteria

- [ ] CSV export works with filtering options
- [ ] JSON export includes metadata, stats, and data
- [ ] PDF report generates successfully
- [ ] PDF includes charts (as images)
- [ ] Export options are customizable
- [ ] Large exports don't freeze UI
- [ ] Files download correctly in native app

---

## Notes

PDF generation in pywebview can be tricky. Consider using matplotlib to generate chart images, then embed in PDF using FPDF or ReportLab. Alternatively, use weasyprint to render HTML to PDF.
