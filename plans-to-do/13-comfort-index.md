# Implementation Plan: Environmental Comfort Index & Derived Metrics

**Priority:** LOW-MEDIUM
**Phase:** 4
**Estimated Effort:** 3-4 hours
**Dependencies:** 01-backend-analysis-engine

---

## Overview

Combine multiple sensor readings into derived metrics that provide holistic environmental assessments, such as a "Comfort Index" that considers temperature, humidity, light, and sound together.

---

## Goals

1. **Holistic Metrics**: Combine sensors into meaningful derived values
2. **Comfort Scoring**: 0-100 scale for overall comfort
3. **Actionable**: Show what's out of optimal range
4. **Historical Tracking**: Track comfort over time
5. **Personalization**: Allow users to define their preferences

---

## Derived Metrics

### 1. **Comfort Index** (0-100)
Combines:
- Temperature (ideal: 68-74°F)
- Humidity (ideal: 40-50%)
- Light (enough but not harsh)
- Sound (quiet enough for focus)

### 2. **Heat Index**
Feels-like temperature combining temp + humidity
```
HI = c1 + c2*T + c3*RH + c4*T*RH + c5*T² + c6*RH² + ...
```

### 3. **Sleep Quality Index**
For nighttime hours:
- Temperature (cooler is better)
- Darkness (light should be low)
- Quiet (sound should be minimal)

### 4. **Productivity Index**
For daytime work hours:
- Temperature (not too hot/cold)
- Adequate light
- Low noise
- Stable conditions

### 5. **Air Quality Indicator**
Based on pressure trends:
- Stable pressure = good
- Falling pressure = weather changing

---

## Implementation

### Backend (analysis_engine.py)
```python
class ComfortCalculator:
    """Calculate derived environmental comfort metrics"""

    def calculate_comfort_index(self, temperature, humidity, light, sound):
        """
        Calculate overall comfort score (0-100)

        Higher = more comfortable
        """
        scores = []

        # Temperature score (ideal: 68-74°F)
        if 68 <= temperature <= 74:
            temp_score = 100
        elif 65 <= temperature <= 77:
            temp_score = 80
        elif 60 <= temperature <= 80:
            temp_score = 60
        else:
            temp_score = max(0, 100 - abs(temperature - 71) * 5)

        scores.append(temp_score * 0.4)  # 40% weight

        # Humidity score (ideal: 40-50%)
        if 40 <= humidity <= 50:
            humid_score = 100
        elif 35 <= humidity <= 55:
            humid_score = 80
        elif 30 <= humidity <= 60:
            humid_score = 60
        else:
            humid_score = max(0, 100 - abs(humidity - 45) * 3)

        scores.append(humid_score * 0.3)  # 30% weight

        # Light score (context-dependent, but generally moderate is good)
        if 500 <= light <= 2000:
            light_score = 100
        elif 200 <= light <= 3000:
            light_score = 80
        else:
            light_score = 60

        scores.append(light_score * 0.15)  # 15% weight

        # Sound score (quieter is usually better)
        if sound < 100:
            sound_score = 100
        elif sound < 200:
            sound_score = 80
        elif sound < 400:
            sound_score = 60
        else:
            sound_score = max(0, 100 - (sound - 400) / 5)

        scores.append(sound_score * 0.15)  # 15% weight

        comfort_index = sum(scores)

        return {
            "overall": round(comfort_index, 1),
            "temperature_score": round(temp_score, 1),
            "humidity_score": round(humid_score, 1),
            "light_score": round(light_score, 1),
            "sound_score": round(sound_score, 1),
            "rating": self._get_comfort_rating(comfort_index)
        }

    def _get_comfort_rating(self, score):
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Very Poor"

    def calculate_heat_index(self, temperature_f, humidity_percent):
        """
        Calculate heat index (feels-like temperature)
        Using Rothfusz regression
        """
        T = temperature_f
        RH = humidity_percent

        # Simplified formula for moderate conditions
        if T < 80:
            return T  # Heat index not applicable

        HI = (-42.379 +
              2.04901523 * T +
              10.14333127 * RH -
              0.22475541 * T * RH -
              6.83783e-3 * T**2 -
              5.481717e-2 * RH**2 +
              1.22874e-3 * T**2 * RH +
              8.5282e-4 * T * RH**2 -
              1.99e-6 * T**2 * RH**2)

        return round(HI, 1)

    def get_comfort_timeline(self, time_range='7d'):
        """Get comfort index over time"""
        df = self.load_data(time_range)

        df['comfort_index'] = df.apply(
            lambda row: self.calculate_comfort_index(
                row['temperature_sht'],
                row['humidity'],
                row['light'],
                row['sound_level']
            )['overall'],
            axis=1
        )

        return df[['gw_timestamp', 'comfort_index']].to_dict('records')
```

### Frontend Display (js/analysis.js)
```javascript
async function displayComfortMetrics() {
    // Get latest reading
    const latest = await window.pywebview.api.get_latest_reading();

    const comfort = await window.pywebview.api.calculate_comfort_index(
        latest.temperature_sht,
        latest.humidity,
        latest.light,
        latest.sound_level
    );

    // Display comfort score
    document.getElementById('comfort-score').textContent = comfort.overall;
    document.getElementById('comfort-rating').textContent = comfort.rating;

    // Color code based on score
    const scoreEl = document.getElementById('comfort-score');
    if (comfort.overall >= 75) {
        scoreEl.className = 'score excellent';
    } else if (comfort.overall >= 60) {
        scoreEl.className = 'score good';
    } else {
        scoreEl.className = 'score poor';
    }

    // Show component scores
    document.getElementById('temp-component').textContent = comfort.temperature_score;
    document.getElementById('humid-component').textContent = comfort.humidity_score;
    document.getElementById('light-component').textContent = comfort.light_score;
    document.getElementById('sound-component').textContent = comfort.sound_score;

    // Load historical comfort
    const timeline = await window.pywebview.api.get_comfort_timeline('7d');
    renderComfortChart(timeline);
}
```

### UI Display
```html
<div class="comfort-dashboard">
    <div class="comfort-score-display">
        <div class="score-circle">
            <span id="comfort-score" class="score">--</span>
            <span class="score-label">/100</span>
        </div>
        <div id="comfort-rating" class="rating">--</div>
    </div>

    <div class="comfort-components">
        <div class="component">
            <span class="component-icon">🌡️</span>
            <span class="component-label">Temperature</span>
            <span id="temp-component" class="component-score">--</span>
        </div>
        <div class="component">
            <span class="component-icon">💧</span>
            <span class="component-label">Humidity</span>
            <span id="humid-component" class="component-score">--</span>
        </div>
        <div class="component">
            <span class="component-icon">💡</span>
            <span class="component-label">Light</span>
            <span id="light-component" class="component-score">--</span>
        </div>
        <div class="component">
            <span class="component-icon">🔊</span>
            <span class="component-label">Sound</span>
            <span id="sound-component" class="component-score">--</span>
        </div>
    </div>

    <div class="comfort-timeline">
        <h4>Comfort Over Time</h4>
        <canvas id="comfort-chart" width="600" height="200"></canvas>
    </div>

    <div class="comfort-recommendations">
        <h4>Recommendations</h4>
        <ul id="comfort-suggestions">
            <!-- Auto-generated based on low scores -->
        </ul>
    </div>
</div>
```

---

## Success Criteria

- [ ] Comfort index calculates correctly
- [ ] Score reflects intuitive comfort levels
- [ ] Historical comfort tracking works
- [ ] Heat index calculation is accurate
- [ ] UI is visually appealing
- [ ] Recommendations are actionable

---

## Future Enhancements

- Allow users to customize ideal ranges
- Add "Personalized Comfort Profile"
- Track "uncomfortable hours" per day
- Alert when comfort drops below threshold
- Compare comfort across different rooms (if multiple sensors)

---

## Notes

Comfort is subjective! Consider allowing users to adjust weights and ideal ranges. What's comfortable for one person may not be for another. Start with reasonable defaults, then add customization.
