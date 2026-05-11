import pandas as pd
import numpy as np
import json
from datetime import datetime

file_path = 'clue_full_history_20260422_214756.csv'

df = pd.read_csv(file_path, low_memory=False)
df['gw_timestamp'] = pd.to_datetime(df['gw_timestamp'])
df = df.dropna(subset=['gw_timestamp'])

# Timezone Inference
df['hour_utc'] = df['gw_timestamp'].dt.hour
peak_light_utc = int(df.groupby('hour_utc')['light'].median().idxmax())
inferred_offset = 12 - peak_light_utc
df['local_time'] = df['gw_timestamp'] + pd.Timedelta(hours=inferred_offset)
df['hour'] = df['local_time'].dt.hour
df['month'] = df['local_time'].dt.strftime('%Y-%m')
df['date'] = df['local_time'].dt.date

# Cleaning
df = df[df['pressure'] > 500] 
df = df[df['light'] < 1000000] 

def to_native(obj):
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, (datetime, pd.Timestamp)): return obj.isoformat()
    return obj

# Q1: Workday Pulse
workday_pulse = df.groupby('hour').agg({
    'sound_level': ['median', 'std'],
    'light': 'median'
}).reset_index()
workday_pulse.columns = ['hour', 'sound_median', 'sound_std', 'light_median']

# Q2: Seasonal Light Shift - Fix: Use explicit peak finding
daily_peaks = []
for date, group in df.groupby('date'):
    if group['light'].max() > 10: # Only days with some light
        peak_row = group.loc[group['light'].idxmax()]
        daily_peaks.append({
            'date': date,
            'peak_hour': peak_row['local_time'].hour + peak_row['local_time'].minute/60,
            'month': peak_row['month']
        })
seasonal_light = pd.DataFrame(daily_peaks).groupby('month')['peak_hour'].median().reset_index()

# Q3: Thermal
thermal_profile = df.groupby('hour')['temperature_sht'].mean().reset_index()

# Q4: Sound Floor
sound_floor = df.groupby('month')['sound_level'].quantile(0.1).reset_index()
sound_floor.columns = ['month', 'sound_floor']

# Q6: Color Palette - Fix: Exclude #000000
def get_top_vibrant_color(series):
    vibrant = series[series != "#000000"].dropna()
    return vibrant.value_counts().index[0] if not vibrant.empty else "#000000"

monthly_colors = df.groupby('month')['color_hex'].apply(get_top_vibrant_color).reset_index()

results = {
    "workday_pulse": workday_pulse.map(to_native).to_dict(orient='records'),
    "seasonal_light": seasonal_light.map(to_native).to_dict(orient='records'),
    "thermal_profile": thermal_profile.map(to_native).to_dict(orient='records'),
    "sound_floor": sound_floor.map(to_native).to_dict(orient='records'),
    "monthly_colors": monthly_colors.map(to_native).to_dict(orient='records'),
    "meta": {
        "row_count": int(len(df)),
        "start_date": df['local_time'].min().isoformat(),
        "end_date": df['local_time'].max().isoformat(),
        "inferred_offset": int(inferred_offset)
    }
}

with open('analysis_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Analysis complete.")
