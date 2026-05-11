import pandas as pd
import numpy as np

file_path = 'clue_full_history_20260422_214756.csv'

# Read the data
df = pd.read_csv(file_path)

# 1. Inventory/Schema
print(f"Total Rows: {len(df)}")
print("\nSchema Analysis:")
stats = []
for col in df.columns:
    col_data = df[col]
    null_rate = col_data.isnull().mean()
    unique_count = col_data.nunique()
    dtype = col_data.dtype
    example = col_data.dropna().iloc[0] if not col_data.dropna().empty else "N/A"
    
    col_stats = {
        "Column": col,
        "Type": str(dtype),
        "Null Rate": f"{null_rate:.2%}",
        "Unique": unique_count,
        "Example": example
    }
    
    if np.issubdtype(dtype, np.number):
        col_stats["Min"] = col_data.min()
        col_stats["Max"] = col_data.max()
    elif "timestamp" in col or "date" in col:
        try:
            ts_data = pd.to_datetime(col_data.dropna())
            col_stats["Min"] = ts_data.min()
            col_stats["Max"] = ts_data.max()
        except:
            pass
            
    stats.append(col_stats)

stats_df = pd.DataFrame(stats)
print(stats_df.to_string(index=False))

# 2. Time Analysis
df['gw_timestamp'] = pd.to_datetime(df['gw_timestamp'])
df = df.sort_values('gw_timestamp')
df['gap'] = df['gw_timestamp'].diff().dt.total_seconds()

print("\nTime Analysis:")
print(f"Start: {df['gw_timestamp'].min()}")
print(f"End: {df['gw_timestamp'].max()}")
print(f"Median Gap: {df['gap'].median()} seconds")
print(f"Max Gap: {df['gap'].max() / 3600:.2f} hours")

# 3. Quality Flags
print("\nQuality Issues:")
print(f"Duplicate Rows: {df.duplicated().sum()}")
print(f"Negative Temperature: {(df['temperature_sht'] < 0).sum()}")
print(f"Zero Light: {(df['light'] == 0).sum()}")
print(f"High Sound Levels (>100): {(df['sound_level'] > 100).sum()}")

# 4. Sampling for inferences
print("\nFirst 5 rows (sorted by time):")
print(df.head())
