import json
import math
from colorsys import rgb_to_hls
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


TZ_NAME = "America/Chicago"
INPUT_CSV = Path("2026-04-22-data-analysis/clue_full_history_20260422_214756.csv")
WEATHER_JSON = Path("2026-04-22-data-analysis/nashville_weather_20250407_20260423.json")
OUTPUT_HTML = Path("2026-04-22-data-analysis/clue_quantified_self_dashboard.html")


def fmt_num(value, digits=1):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    if digits == 0:
        return f"{int(round(value)):,}"
    return f"{value:,.{digits}f}"


def hour_label(hour_value):
    if hour_value is None or (isinstance(hour_value, float) and math.isnan(hour_value)):
        return "n/a"
    hour = int(hour_value) % 24
    minute = int(round((hour_value - math.floor(hour_value)) * 60)) % 60
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    if minute == 0:
        return f"{hour12} {suffix}"
    return f"{hour12}:{minute:02d} {suffix}"


def month_label(month_str):
    return pd.Period(month_str, freq="M").strftime("%b %Y")


def local_hour(series):
    return series.dt.hour + series.dt.minute / 60.0


def safe_quantile(series, q):
    series = series.dropna()
    if series.empty:
        return np.nan
    return float(series.quantile(q))


def parse_hex(value):
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        return None
    try:
        return (
            int(value[1:3], 16),
            int(value[3:5], 16),
            int(value[5:7], 16),
        )
    except ValueError:
        return None


def blend_colors(colors):
    if not colors:
        return "#000000"
    arr = np.array(colors, dtype=float)
    mean = np.clip(np.round(arr.mean(axis=0)), 0, 255).astype(int)
    return "#{:02X}{:02X}{:02X}".format(*mean.tolist())


def robust_zscore(series):
    median = series.median()
    mad = (series - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return pd.Series(0.0, index=series.index)
    return 0.6745 * (series - median) / mad


def json_ready_records(frame):
    def convert(value):
        if isinstance(value, (pd.Timestamp, datetime, date)):
            return value.isoformat()
        return value

    converted = frame.copy()
    for col in converted.columns:
        converted[col] = converted[col].map(convert)
    return converted.to_dict(orient="records")


def load_weather_frame():
    if not WEATHER_JSON.exists():
        return None, None
    weather_obj = json.loads(WEATHER_JSON.read_text())
    weather = pd.DataFrame(weather_obj["hourly"])
    weather["local_ts"] = pd.to_datetime(weather["time"]).dt.tz_localize(
        TZ_NAME,
        ambiguous=True,
        nonexistent="shift_forward",
    )
    weather["local_date"] = weather["local_ts"].dt.date
    weather["month"] = weather["local_ts"].dt.strftime("%Y-%m")
    weather["outdoor_temp_f"] = weather["temperature_2m"] * 9 / 5 + 32
    weather = weather.drop(columns=["time"]).set_index("local_ts")
    return weather, weather_obj


def metric_summary(frame, column):
    series = frame[column]
    numeric = pd.to_numeric(series, errors="coerce")
    examples = [str(v) for v in series.dropna().head(3).tolist()]
    summary = {
        "name": column,
        "null_rate": round(float(series.isna().mean() * 100), 3),
        "unique_nonnull": int(series.nunique(dropna=True)),
        "examples": examples,
    }
    if column == "gw_timestamp":
        dt = pd.to_datetime(series, utc=True, errors="coerce")
        summary.update(
            {
                "type": "datetime",
                "date_min": dt.min().isoformat() if dt.notna().any() else None,
                "date_max": dt.max().isoformat() if dt.notna().any() else None,
            }
        )
    elif numeric.notna().sum() > 0 and numeric.notna().sum() >= max(3, len(series) * 0.5):
        summary.update(
            {
                "type": "numeric",
                "min": float(numeric.min()),
                "max": float(numeric.max()),
            }
        )
    else:
        summary["type"] = "categorical"
    return summary


def build_rollups():
    raw = pd.read_csv(INPUT_CSV, low_memory=False)
    weather, weather_obj = load_weather_frame()
    raw["gw_ts_utc"] = pd.to_datetime(raw["gw_timestamp"], utc=True, errors="coerce")
    raw["local_ts"] = raw["gw_ts_utc"].dt.tz_convert(TZ_NAME)
    raw["local_date"] = raw["local_ts"].dt.date
    raw["local_hour"] = local_hour(raw["local_ts"])
    raw["local_month"] = raw["local_ts"].dt.strftime("%Y-%m")

    numeric_columns = [
        "timestamp_monotonic",
        "timestamp_iso",
        "temperature_sht",
        "humidity",
        "pressure",
        "light",
        "sound_level",
    ]
    for col in numeric_columns:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    schema = [metric_summary(raw, col) for col in raw.columns[:9]]

    cleaned = raw.copy()
    dropped_counts = {
        "invalid_gw_timestamp": int(cleaned["gw_ts_utc"].isna().sum()),
        "pressure_lt_900_hpa": int((cleaned["pressure"] < 900).sum()),
        "light_gt_70000_clear_counts": int((cleaned["light"] > 70000).sum()),
        "corrupt_monotonic_non_numeric": int(raw["timestamp_monotonic"].isna().sum()),
    }
    cleaned.loc[cleaned["pressure"] < 900, "pressure"] = np.nan
    cleaned.loc[cleaned["light"] > 70000, "light"] = np.nan
    cleaned = cleaned[cleaned["gw_ts_utc"].notna()].copy()
    cleaned = cleaned.sort_values("local_ts").reset_index(drop=True)
    cleaned["gw_gap_s"] = cleaned["gw_ts_utc"].diff().dt.total_seconds()
    cleaned["mono_gap_s"] = cleaned["timestamp_monotonic"].diff()

    gap_rows = cleaned.loc[cleaned["gw_gap_s"] > 3600, ["local_ts", "gw_gap_s"]].copy()
    gap_rows["gap_hours"] = gap_rows["gw_gap_s"] / 3600.0
    gap_rows["local_ts"] = gap_rows["local_ts"].astype(str)

    reboot_rows = cleaned.loc[cleaned["mono_gap_s"] < 0, ["local_ts", "mono_gap_s"]].copy()
    reboot_rows["local_ts"] = reboot_rows["local_ts"].astype(str)

    headline_shift_source = []
    for local_date, group in cleaned.groupby("local_date"):
        group = group[group["light"].notna()]
        if len(group) < 50 or safe_quantile(group["light"], 0.95) < 100:
            continue
        peak_row = group.loc[group["light"].idxmax()]
        p90 = group["light"].quantile(0.9)
        bright = group[group["light"] >= p90]
        headline_shift_source.append(
            {
                "date": str(local_date),
                "month": str(pd.Period(local_date, freq="M")),
                "peak_hour": float(peak_row["local_hour"]),
                "peak_light": float(peak_row["light"]),
                "bright_start": float(local_hour(pd.Series([bright["local_ts"].min()])).iloc[0]),
                "bright_end": float(local_hour(pd.Series([bright["local_ts"].max()])).iloc[0]),
                "bright_span_h": float(
                    (bright["local_ts"].max() - bright["local_ts"].min()).total_seconds() / 3600.0
                ),
            }
        )
    light_days = pd.DataFrame(headline_shift_source)
    monthly_light = (
        light_days.groupby("month")
        .agg(
            peak_hour=("peak_hour", "median"),
            bright_span_h=("bright_span_h", "median"),
            peak_light=("peak_light", "median"),
            days=("date", "count"),
        )
        .reset_index()
    )
    peak_shift_hours = float(monthly_light["peak_hour"].max() - monthly_light["peak_hour"].min())

    byday = (
        cleaned.groupby("local_date")
        .agg(
            light_p75=("light", lambda s: s.quantile(0.75)),
            sound_p75=("sound_level", lambda s: s.quantile(0.75)),
            light_p90=("light", lambda s: s.quantile(0.9)),
            sound_p90=("sound_level", lambda s: s.quantile(0.9)),
            rows=("gw_timestamp", "size"),
        )
        .reset_index()
    )
    byday["light_rank"] = byday["light_p75"].rank(pct=True)
    byday["sound_rank"] = byday["sound_p75"].rank(pct=True)
    byday["activity_score"] = (byday["light_rank"] + byday["sound_rank"]) / 2.0
    q1 = float(byday["activity_score"].quantile(0.25))
    q3 = float(byday["activity_score"].quantile(0.75))
    byday["activity_class"] = np.where(
        byday["activity_score"] >= q3,
        "active",
        np.where(byday["activity_score"] <= q1, "quiet", "middle"),
    )
    class_counts = byday["activity_class"].value_counts().to_dict()
    merged_day_class = cleaned.merge(
        byday[["local_date", "activity_class", "activity_score"]],
        on="local_date",
        how="left",
    )
    daily_profiles = (
        merged_day_class.groupby(["activity_class", merged_day_class["local_ts"].dt.hour])
        .agg(
            light_median=("light", "median"),
            sound_median=("sound_level", "median"),
            temp_median=("temperature_sht", "median"),
        )
        .reset_index(names=["activity_class", "hour"])
    )
    activity_profile = []
    for hour in range(24):
        row = {"hour": hour}
        for label in ["quiet", "active"]:
            subset = daily_profiles[
                (daily_profiles["activity_class"] == label) & (daily_profiles["hour"] == hour)
            ]
            if subset.empty:
                row[f"{label}_light"] = None
                row[f"{label}_sound"] = None
                row[f"{label}_temp"] = None
            else:
                row[f"{label}_light"] = float(subset["light_median"].iloc[0])
                row[f"{label}_sound"] = float(subset["sound_median"].iloc[0])
                row[f"{label}_temp"] = float(subset["temp_median"].iloc[0])
        activity_profile.append(row)

    hourly = (
        cleaned.set_index("local_ts")
        .resample("1h")
        .agg(
            light=("light", "median"),
            temp=("temperature_sht", "median"),
            humidity=("humidity", "median"),
            pressure=("pressure", "median"),
            sound=("sound_level", lambda s: s.quantile(0.95)),
            rows=("gw_timestamp", "size"),
        )
    )
    hourly_weather = hourly.join(weather, how="inner") if weather is not None else hourly.copy()
    lag_results = []
    light_norm = (hourly["light"] - hourly["light"].mean()) / hourly["light"].std()
    temp_norm = (hourly["temp"] - hourly["temp"].mean()) / hourly["temp"].std()
    for lag in range(-12, 13):
        corr = light_norm.corr(temp_norm.shift(-lag))
        lag_results.append({"lag_hours": lag, "correlation": None if pd.isna(corr) else float(corr)})
    best_positive_lag = max(
        [row for row in lag_results if row["lag_hours"] >= 0 and row["correlation"] is not None],
        key=lambda row: row["correlation"],
    )
    outdoor_lag_results = []
    weather_temp_corr = None
    best_outdoor_lag = None
    if weather is not None:
        outdoor_norm = (
            (hourly_weather["outdoor_temp_f"] - hourly_weather["outdoor_temp_f"].mean())
            / hourly_weather["outdoor_temp_f"].std()
        )
        indoor_norm = (
            (hourly_weather["temp"] - hourly_weather["temp"].mean()) / hourly_weather["temp"].std()
        )
        for lag in range(-24, 25, 2):
            corr = outdoor_norm.corr(indoor_norm.shift(-lag))
            outdoor_lag_results.append(
                {"lag_hours": lag, "correlation": None if pd.isna(corr) else float(corr)}
            )
        candidates = [
            row for row in outdoor_lag_results if row["lag_hours"] >= 0 and row["correlation"] is not None
        ]
        if candidates:
            best_outdoor_lag = max(candidates, key=lambda row: row["correlation"])
            weather_temp_corr = best_outdoor_lag["correlation"]
    typical_day = (
        cleaned.groupby(cleaned["local_ts"].dt.hour)
        .agg(light_median=("light", "median"), temp_median=("temperature_sht", "median"))
        .reset_index(names=["hour"])
    )

    color_rows = []
    color_frame = cleaned[cleaned["color_hex"].notna()].copy()
    rgb_values = color_frame["color_hex"].apply(parse_hex)
    color_frame = color_frame[rgb_values.notna()].copy()
    color_frame["rgb"] = list(rgb_values[rgb_values.notna()])
    color_frame["r"] = color_frame["rgb"].str[0]
    color_frame["g"] = color_frame["rgb"].str[1]
    color_frame["b"] = color_frame["rgb"].str[2]
    color_frame["brightness"] = (color_frame["r"] + color_frame["g"] + color_frame["b"]) / 3.0
    color_frame["warm_cool_delta"] = color_frame["r"] - color_frame["b"]
    color_frame["color_mode"] = np.select(
        [
            color_frame["brightness"] < 20,
            color_frame["warm_cool_delta"] > 20,
            color_frame["warm_cool_delta"] < -20,
        ],
        ["dark", "warm", "cool"],
        default="neutral",
    )
    monthly_color_modes = (
        color_frame.groupby(["local_month", "color_mode"]).size().unstack(fill_value=0).reset_index()
    )
    for _, row in monthly_color_modes.iterrows():
        total = int(row[["dark", "warm", "cool", "neutral"]].sum())
        swatches = color_frame[color_frame["local_month"] == row["local_month"]]
        dominant = blend_colors(swatches["rgb"].head(200).tolist())
        color_rows.append(
            {
                "month": row["local_month"],
                "dark_share": float(row.get("dark", 0) / total),
                "warm_share": float(row.get("warm", 0) / total),
                "cool_share": float(row.get("cool", 0) / total),
                "neutral_share": float(row.get("neutral", 0) / total),
                "dominant_color": dominant,
                "mean_brightness": float(swatches["brightness"].mean()),
            }
        )

    cleaned["heat_discomfort"] = np.clip(cleaned["temperature_sht"] - 88.0, 0, None)
    cleaned["dry_discomfort"] = np.clip(22.0 - cleaned["humidity"], 0, None)
    cleaned["noise_discomfort"] = np.clip(cleaned["sound_level"] - 120.0, 0, None)
    cleaned["discomfort"] = (
        cleaned["heat_discomfort"] * 0.5
        + cleaned["dry_discomfort"] * 1.0
        + cleaned["noise_discomfort"] * 0.03
    )
    discomfort_by_hour = (
        cleaned.groupby(cleaned["local_ts"].dt.hour)
        .agg(
            discomfort_p95=("discomfort", lambda s: s.quantile(0.95)),
            temperature_p95=("temperature_sht", lambda s: s.quantile(0.95)),
            humidity_p05=("humidity", lambda s: s.quantile(0.05)),
            sound_p95=("sound_level", lambda s: s.quantile(0.95)),
        )
        .reset_index(names=["hour"])
    )
    discomfort_days = (
        cleaned.groupby("local_date")
        .agg(
            discomfort_p95=("discomfort", lambda s: s.quantile(0.95)),
            temp_max=("temperature_sht", "max"),
            humidity_min=("humidity", "min"),
            sound_p95=("sound_level", lambda s: s.quantile(0.95)),
        )
        .reset_index()
        .sort_values("discomfort_p95", ascending=False)
        .head(8)
    )

    anomaly = hourly.copy()
    anomaly["temp_rz"] = robust_zscore(anomaly["temp"])
    anomaly["humidity_rz"] = robust_zscore(anomaly["humidity"])
    anomaly["pressure_rz"] = robust_zscore(anomaly["pressure"])
    anomaly["light_rz"] = robust_zscore(anomaly["light"])
    anomaly["sound_rz"] = robust_zscore(anomaly["sound"])
    anomaly["anomaly_score"] = anomaly[
        ["temp_rz", "humidity_rz", "pressure_rz", "light_rz", "sound_rz"]
    ].abs().sum(axis=1)
    threshold = float(anomaly["anomaly_score"].quantile(0.995))
    anomaly["is_event"] = anomaly["anomaly_score"] >= threshold

    episodes = []
    current = None
    for timestamp, row in anomaly.iterrows():
        if row["is_event"]:
            if current is None:
                current = {
                    "start": timestamp,
                    "end": timestamp,
                    "scores": [float(row["anomaly_score"])],
                    "temp": [row["temp"]],
                    "humidity": [row["humidity"]],
                    "pressure": [row["pressure"]],
                    "light": [row["light"]],
                    "sound": [row["sound"]],
                }
            elif (timestamp - current["end"]).total_seconds() <= 7200:
                current["end"] = timestamp
                current["scores"].append(float(row["anomaly_score"]))
                for key in ["temp", "humidity", "pressure", "light", "sound"]:
                    current[key].append(row[key])
            else:
                episodes.append(current)
                current = {
                    "start": timestamp,
                    "end": timestamp,
                    "scores": [float(row["anomaly_score"])],
                    "temp": [row["temp"]],
                    "humidity": [row["humidity"]],
                    "pressure": [row["pressure"]],
                    "light": [row["light"]],
                    "sound": [row["sound"]],
                }
        elif current is not None:
            episodes.append(current)
            current = None
    if current is not None:
        episodes.append(current)

    anomaly_events = []
    for event in episodes:
        peak_light = np.nanmax(event["light"])
        peak_sound = np.nanmax(event["sound"])
        temp_span = np.nanmax(event["temp"]) - np.nanmin(event["temp"])
        humidity_min = np.nanmin(event["humidity"])
        reasons = []
        if peak_light >= 10000:
            reasons.append("extreme brightness")
        if peak_sound >= 400:
            reasons.append("sound spike")
        if humidity_min <= 18:
            reasons.append("very dry air")
        if temp_span >= 5:
            reasons.append("fast temperature swing")
        if weather is not None:
            weather_slice = weather.loc[event["start"] : event["end"]]
            if not weather_slice.empty:
                if float(weather_slice["precipitation"].sum()) >= 5:
                    reasons.append("storm rain outside")
                if float(weather_slice["wind_gusts_10m"].max()) >= 50:
                    reasons.append("high gusts outside")
        anomaly_events.append(
            {
                "start": event["start"].isoformat(),
                "end": event["end"].isoformat(),
                "duration_h": float((event["end"] - event["start"]).total_seconds() / 3600.0 + 1.0),
                "score": float(max(event["scores"])),
                "peak_light": None if np.isnan(peak_light) else float(peak_light),
                "peak_sound": None if np.isnan(peak_sound) else float(peak_sound),
                "min_humidity": None if np.isnan(humidity_min) else float(humidity_min),
                "temp_span": None if np.isnan(temp_span) else float(temp_span),
                "label": ", ".join(reasons) if reasons else "mixed sensor anomaly",
            }
        )
    anomaly_events.sort(key=lambda row: row["score"], reverse=True)
    anomaly_events = anomaly_events[:10]

    routine = (
        hourly.assign(month=hourly.index.strftime("%Y-%m"))
        .groupby("month")
        .agg(
            active_hours_per_day=("light", lambda s: float((((s > 300) | (hourly.loc[s.index, "sound"] > 20)).mean()) * 24)),
            light_median=("light", "median"),
            sound_p75=("sound", lambda s: s.quantile(0.75)),
            temp_median=("temp", "median"),
            sampled_hours=("rows", lambda s: int((s > 0).sum())),
        )
        .reset_index()
    )

    weather_compare = {}
    monthly_coupling = pd.DataFrame()
    if weather is not None:
        monthly_coupling = (
            hourly_weather.assign(month=hourly_weather.index.strftime("%Y-%m"))
            .groupby("month")
            .agg(
                indoor_temp_f=("temp", "median"),
                outdoor_temp_f=("outdoor_temp_f", "median"),
                indoor_pressure=("pressure", "median"),
                outdoor_pressure=("pressure_msl", "median"),
                indoor_light=("light", "median"),
                precipitation_mm=("precipitation", "sum"),
            )
            .reset_index()
        )
        monthly_coupling["temp_delta_f"] = (
            monthly_coupling["indoor_temp_f"] - monthly_coupling["outdoor_temp_f"]
        )
        monthly_coupling["pressure_gap_hpa"] = (
            monthly_coupling["indoor_pressure"] - monthly_coupling["outdoor_pressure"]
        )
        weather_daily = (
            hourly_weather.groupby(hourly_weather.index.date)
            .agg(
                rain_mm=("rain", "sum"),
                precip_hours=("precipitation", lambda s: int((s > 0).sum())),
                outdoor_temp_f=("outdoor_temp_f", "mean"),
                indoor_temp_f=("temp", "median"),
                indoor_light=("light", "median"),
                indoor_sound=("sound", "median"),
                indoor_pressure=("pressure", "median"),
                outdoor_pressure=("pressure_msl", "median"),
            )
            .reset_index(names=["date"])
        )
        weather_daily["rainy"] = weather_daily["rain_mm"] > 0
        rainy_medians = (
            weather_daily.groupby("rainy")[
                ["indoor_light", "indoor_sound", "indoor_temp_f", "outdoor_temp_f"]
            ]
            .median()
            .reset_index()
        )
        rainy_lookup = {
            bool(row["rainy"]): row for _, row in rainy_medians.iterrows()
        }
        weather_compare = {
            "merged_hours": int(len(hourly_weather)),
            "indoor_outdoor_temp_corr": float(
                hourly_weather[["temp", "outdoor_temp_f"]].corr().iloc[0, 1]
            ),
            "indoor_outdoor_pressure_corr": float(
                hourly_weather[["pressure", "pressure_msl"]].corr().iloc[0, 1]
            ),
            "pressure_gap_median_hpa": float(
                (hourly_weather["pressure"] - hourly_weather["pressure_msl"]).median()
            ),
            "rainy_day_indoor_light_median": float(
                rainy_lookup.get(True, {}).get("indoor_light", np.nan)
            ),
            "dry_day_indoor_light_median": float(
                rainy_lookup.get(False, {}).get("indoor_light", np.nan)
            ),
            "rainy_day_indoor_sound_median": float(
                rainy_lookup.get(True, {}).get("indoor_sound", np.nan)
            ),
            "dry_day_indoor_sound_median": float(
                rainy_lookup.get(False, {}).get("indoor_sound", np.nan)
            ),
            "rainy_days": int(weather_daily["rainy"].sum()),
            "dry_days": int((~weather_daily["rainy"]).sum()),
        }

    daily_pressure = (
        cleaned.set_index("local_ts")
        .resample("1D")
        .agg(
            pressure=("pressure", "median"),
            temp=("temperature_sht", "median"),
            humidity=("humidity", "median"),
            light=("light", "median"),
            sound=("sound_level", "median"),
        )
        .dropna(subset=["pressure"])
        .reset_index()
    )
    pressure_corr = daily_pressure[["pressure", "temp", "humidity", "light", "sound"]].corr()[
        "pressure"
    ].to_dict()
    pressure_monthly = (
        daily_pressure.assign(month=daily_pressure["local_ts"].dt.strftime("%Y-%m"))
        .groupby("month")
        .agg(pressure=("pressure", "median"))
        .reset_index()
    )

    active_dates = int(cleaned["local_date"].nunique())
    total_span_days = int((cleaned["local_ts"].max() - cleaned["local_ts"].min()).days + 1)

    data = {
        "meta": {
            "title": "Office Pulse",
            "subtitle": "Adafruit CLUE office environment, joined to Nashville hourly weather in America/Chicago local time unless noted.",
            "headline_value": round(peak_shift_hours, 1),
            "headline_unit": "hours",
            "headline_label": "seasonal drift in the brightest hour of the room",
            "kpis": [
                {"label": "Active Dates", "value": active_dates, "unit": f"of {total_span_days} calendar days"},
                {"label": "Median Cadence", "value": round(float(cleaned["gw_gap_s"].median()), 1), "unit": "seconds"},
                {"label": "Median Temperature", "value": round(float(cleaned["temperature_sht"].median()), 1), "unit": "deg F"},
                {"label": "Outages > 1 hour", "value": int((cleaned["gw_gap_s"] > 3600).sum()), "unit": "gaps"},
            ],
        },
        "schema": schema,
        "sections": {
            "seasonal_light": monthly_light.to_dict(orient="records"),
            "activity_profile": activity_profile,
            "activity_class_counts": class_counts,
            "lag_profile": lag_results,
            "typical_day": typical_day.to_dict(orient="records"),
            "color_modes": color_rows,
            "discomfort_by_hour": discomfort_by_hour.to_dict(orient="records"),
            "discomfort_days": json_ready_records(discomfort_days),
            "anomaly_events": anomaly_events,
            "routine": routine.to_dict(orient="records"),
            "pressure_monthly": json_ready_records(pressure_monthly),
            "pressure_corr": pressure_corr,
            "monthly_coupling": json_ready_records(monthly_coupling),
            "weather_compare": weather_compare,
            "outdoor_lag_profile": outdoor_lag_results,
        },
        "provenance": {
            "source_file": str(INPUT_CSV),
            "weather_file": str(WEATHER_JSON) if weather is not None else None,
            "source_rows": int(len(raw)),
            "rows_after_timestamp_cleaning": int(len(cleaned)),
            "date_range_utc": {
                "start": cleaned["gw_ts_utc"].min().isoformat(),
                "end": cleaned["gw_ts_utc"].max().isoformat(),
            },
            "date_range_local": {
                "start": cleaned["local_ts"].min().isoformat(),
                "end": cleaned["local_ts"].max().isoformat(),
            },
            "rows_with_any_null_sensor": int(
                cleaned[["temperature_sht", "humidity", "pressure", "light", "sound_level", "color_hex"]]
                .isna()
                .any(axis=1)
                .sum()
            ),
            "dropped_or_masked": dropped_counts,
            "major_gaps": gap_rows.nlargest(8, "gw_gap_s").to_dict(orient="records"),
            "device_reboots": reboot_rows.head(12).to_dict(orient="records"),
        },
        "insights": {
            "seasonal_light": (
                f"The room's brightest moment moved by {fmt_num(peak_shift_hours, 1)} hours across the observed months, "
                f"from roughly {hour_label(monthly_light['peak_hour'].min())} at the earliest to {hour_label(monthly_light['peak_hour'].max())} at the latest."
            ),
            "activity_profile": (
                f"On active days, the midday pulse is obvious: median light reaches {fmt_num(max(row['active_light'] or 0 for row in activity_profile), 0)} clear counts "
                f"and median sound {fmt_num(max(row['active_sound'] or 0 for row in activity_profile), 0)} RMS, while quiet days stay far flatter."
            ),
            "heat_lag": (
                f"Temperature trails light rather than moving in lockstep: the strongest hourly correlation appears about {best_positive_lag['lag_hours']} hours later "
                f"(r={fmt_num(best_positive_lag['correlation'], 2)}), which is consistent with the room warming after it brightens."
            ),
            "color_modes": (
                "The color sensor behaves less like a single dominant hue tracker and more like a regime detector: early months skew warm-and-dark, "
                "while autumn and winter show more neutral and cool episodes plus more clipped white readings."
            ),
            "discomfort": (
                f"Discomfort is mostly a tail event, not the everyday baseline: the median score stays near zero all day, but the 95th percentile rises highest around "
                f"{hour_label(discomfort_by_hour.sort_values('discomfort_p95', ascending=False).iloc[0]['hour'])} when heat, dryness, and noise occasionally stack."
            ),
            "anomalies": (
                f"The strongest anomaly episodes are dominated by sensor extremes rather than subtle drift, with the top events driven by brightness saturation, loud spikes, unusually dry air, and in a few cases storm conditions outside."
            ),
            "routine": (
                f"The office routine changed regime at least twice: activity intensifies through summer, then drops sharply from October into December, with long collection outages afterward."
            ),
            "pressure": (
                f"Pressure mostly reads as weather backdrop here. Its strongest daily correlation is modest and negative with temperature (r={fmt_num(pressure_corr.get('temp', float('nan')), 2)}), "
                f"and it has almost no daily relationship with sound (r={fmt_num(pressure_corr.get('sound', float('nan')), 2)})."
            ),
            "weather": (
                f"Outdoor weather explains some of the room's behavior much better than the raw indoor-only view did: indoor temperature tracks outdoor temperature strongly "
                f"(r={fmt_num(weather_compare.get('indoor_outdoor_temp_corr', float('nan')), 2)}) and peaks about {best_outdoor_lag['lag_hours'] if best_outdoor_lag else 'n/a'} hours later, "
                f"while indoor pressure follows outdoor pressure with a stable offset of about {fmt_num(weather_compare.get('pressure_gap_median_hpa', float('nan')), 1)} hPa."
            ),
        },
    }
    return data


def build_html(data):
    payload = json.dumps(data, separators=(",", ":"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Office Pulse Dashboard</title>
  <style>
    :root {{
      --bg: #1c1917;
      --panel: #292524;
      --panel-soft: #231f1d;
      --text: #f5f5f4;
      --muted: #d6d3d1;
      --subtle: #a8a29e;
      --grid: #44403c;
      --orange: #FF8F3B;
      --orange-soft: #FDAD57;
      --orange-pale: #FFCE9D;
      --amber: #f59e0b;
      --teal: #14b8a6;
      --rose: #fb7185;
      --emerald: #34d399;
      --cyan: #22d3ee;
      --indigo: #818cf8;
      --purple: #c084fc;
      --gray: #78716c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif;
      line-height: 1.45;
    }}
    .page {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 40px 28px 64px;
    }}
    .eyebrow {{
      color: var(--orange-pale);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(40px, 7vw, 88px);
      line-height: 0.96;
      font-weight: 400;
      max-width: 10ch;
    }}
    .subtitle {{
      max-width: 62ch;
      color: var(--muted);
      font-size: 17px;
      margin-top: 18px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 2.1fr 1fr;
      gap: 24px;
      align-items: end;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--grid);
    }}
    .headline-card {{
      min-height: 220px;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
    }}
    .headline-stat {{
      font-size: clamp(68px, 14vw, 164px);
      line-height: 0.9;
      font-weight: 300;
      color: var(--text);
    }}
    .headline-unit {{
      color: var(--orange-soft);
      font-size: clamp(20px, 3vw, 32px);
      margin-left: 6px;
    }}
    .headline-label {{
      margin-top: 8px;
      color: var(--orange-pale);
      font-size: 14px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }}
    .kpi-strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 26px;
    }}
    .kpi {{
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      padding: 14px 16px 16px;
      min-height: 110px;
    }}
    .kpi-label {{
      color: var(--subtle);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 11px;
    }}
    .kpi-value {{
      font-size: 44px;
      line-height: 1;
      margin-top: 10px;
    }}
    .kpi-unit {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 14px;
    }}
    .section {{
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 28px;
      padding: 28px 0;
      border-bottom: 1px solid var(--grid);
    }}
    .section-meta {{
      position: sticky;
      top: 24px;
      align-self: start;
    }}
    .section-index {{
      color: var(--orange-soft);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }}
    .section h2 {{
      margin: 0 0 10px;
      font-size: 32px;
      font-weight: 400;
      line-height: 1.05;
    }}
    .section p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .viz-wrap {{
      display: grid;
      gap: 18px;
    }}
    .viz {{
      background: var(--panel-soft);
      border: 1px solid rgba(255,255,255,0.08);
      padding: 16px;
      min-height: 320px;
    }}
    .finding {{
      color: var(--text);
      font-size: 17px;
      max-width: 72ch;
    }}
    .method {{
      color: var(--subtle);
      font-size: 13px;
      max-width: 74ch;
    }}
    .footer {{
      padding-top: 26px;
      color: var(--muted);
    }}
    .footer-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-top: 14px;
    }}
    .footer-card {{
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      padding: 16px;
    }}
    .footer-card h3 {{
      margin: 0 0 10px;
      font-size: 13px;
      color: var(--orange-pale);
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-weight: 400;
    }}
    .footer-card p, .footer-card li {{
      margin: 0 0 8px;
      font-size: 14px;
      color: var(--muted);
    }}
    .footer-card ul {{
      padding-left: 18px;
      margin: 0;
    }}
    .pill-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }}
    .pill {{
      padding: 8px 12px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      color: var(--muted);
    }}
    .table th, .table td {{
      padding: 8px 6px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      text-align: left;
      vertical-align: top;
    }}
    .table th {{
      color: var(--orange-pale);
      font-weight: 400;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 11px;
    }}
    .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; }}
    @media (max-width: 980px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .kpi-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .section {{ grid-template-columns: 1fr; }}
      .section-meta {{ position: static; }}
      .footer-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .page {{ padding: 24px 16px 42px; }}
      .kpi-strip {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="page" id="app"></div>
  <script>
    const data = {payload};

    const colors = {{
      amber: getCss('--amber'),
      teal: getCss('--teal'),
      rose: getCss('--rose'),
      emerald: getCss('--emerald'),
      cyan: getCss('--cyan'),
      indigo: getCss('--indigo'),
      purple: getCss('--purple'),
      gray: getCss('--gray'),
      orange: getCss('--orange'),
      orangeSoft: getCss('--orange-soft'),
      orangePale: getCss('--orange-pale'),
      text: getCss('--text'),
      muted: getCss('--muted'),
      grid: getCss('--grid'),
      panel: getCss('--panel-soft'),
      bg: getCss('--bg')
    }};

    function getCss(name) {{
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }}

    function el(tag, className, text) {{
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }}

    function svgEl(tag, attrs = {{}}) {{
      const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
      return node;
    }}

    function fmt(value, digits = 1) {{
      if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
      return Number(value).toLocaleString(undefined, {{
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
      }});
    }}

    function fmtInt(value) {{
      if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
      return Math.round(Number(value)).toLocaleString();
    }}

    function hourLabel(hourValue) {{
      if (hourValue === null || hourValue === undefined || Number.isNaN(hourValue)) return 'n/a';
      const hour = Math.floor(hourValue) % 24;
      const minute = Math.round((hourValue - Math.floor(hourValue)) * 60) % 60;
      const suffix = hour < 12 ? 'AM' : 'PM';
      const hour12 = hour % 12 || 12;
      return minute ? `${{hour12}}:${{String(minute).padStart(2, '0')}} ${{suffix}}` : `${{hour12}} ${{suffix}}`;
    }}

    function monthLabel(monthStr) {{
      const [year, month] = monthStr.split('-').map(Number);
      return new Date(year, month - 1, 1).toLocaleDateString(undefined, {{ month: 'short', year: 'numeric' }});
    }}

    function isoLocal(iso) {{
      return new Date(iso).toLocaleString(undefined, {{
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric'
      }});
    }}

    function scaleLinear(domainMin, domainMax, rangeMin, rangeMax) {{
      const span = domainMax - domainMin || 1;
      return value => rangeMin + ((value - domainMin) / span) * (rangeMax - rangeMin);
    }}

    function makeBaseSvg(width, height) {{
      return svgEl('svg', {{ viewBox: `0 0 ${{width}} ${{height}}`, width: '100%', height: '100%', role: 'img' }});
    }}

    function addText(svg, x, y, text, attrs = {{}}) {{
      const t = svgEl('text', Object.assign({{
        x, y,
        fill: colors.muted,
        'font-size': 11,
        'font-family': 'system-ui, sans-serif'
      }}, attrs));
      t.textContent = text;
      svg.appendChild(t);
      return t;
    }}

    function drawAxes(svg, plot, xTicks, yTicks, xFormatter, yFormatter) {{
      const {{ x, y, w, h }} = plot;
      svg.appendChild(svgEl('line', {{ x1: x, y1: y + h, x2: x + w, y2: y + h, stroke: colors.grid }}));
      svg.appendChild(svgEl('line', {{ x1: x, y1: y, x2: x, y2: y + h, stroke: colors.grid }}));
      xTicks.forEach(tick => {{
        const px = plot.xScale(tick);
        svg.appendChild(svgEl('line', {{ x1: px, y1: y + h, x2: px, y2: y + h + 5, stroke: colors.grid }}));
        addText(svg, px, y + h + 18, xFormatter(tick), {{ 'text-anchor': 'middle' }});
      }});
      yTicks.forEach(tick => {{
        const py = plot.yScale(tick);
        svg.appendChild(svgEl('line', {{ x1: x, y1: py, x2: x + w, y2: py, stroke: 'rgba(255,255,255,0.08)' }}));
        addText(svg, x - 10, py + 4, yFormatter(tick), {{ 'text-anchor': 'end' }});
      }});
    }}

    function drawLineChart(container, series, opts) {{
      const width = opts.width || 900;
      const height = opts.height || 280;
      const margin = Object.assign({{ top: 16, right: 24, bottom: 34, left: 48 }}, opts.margin || {{}});
      const svg = makeBaseSvg(width, height);
      const plot = {{
        x: margin.left,
        y: margin.top,
        w: width - margin.left - margin.right,
        h: height - margin.top - margin.bottom
      }};
      const xVals = series.flatMap(line => line.data.map(d => d.x)).filter(v => v !== null && v !== undefined);
      const yVals = series.flatMap(line => line.data.map(d => d.y)).filter(v => v !== null && v !== undefined);
      plot.xScale = scaleLinear(Math.min(...xVals), Math.max(...xVals), plot.x, plot.x + plot.w);
      plot.yScale = scaleLinear(Math.min(...yVals), Math.max(...yVals), plot.y + plot.h, plot.y);
      drawAxes(svg, plot, opts.xTicks, opts.yTicks, opts.xFormatter, opts.yFormatter);
      series.forEach(line => {{
        const path = [];
        line.data.forEach((point, idx) => {{
          if (point.y === null || point.y === undefined || Number.isNaN(point.y)) return;
          const cmd = idx === 0 || path.length === 0 ? 'M' : 'L';
          path.push(`${{cmd}}${{plot.xScale(point.x)}},${{plot.yScale(point.y)}}`);
        }});
        svg.appendChild(svgEl('path', {{
          d: path.join(' '),
          fill: 'none',
          stroke: line.color,
          'stroke-width': line.strokeWidth || 2.5,
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round'
        }}));
      }});
      if (opts.legend) {{
        let lx = plot.x;
        const ly = 16;
        opts.legend.forEach(item => {{
          svg.appendChild(svgEl('line', {{ x1: lx, y1: ly, x2: lx + 18, y2: ly, stroke: item.color, 'stroke-width': 3 }}));
          addText(svg, lx + 24, ly + 4, item.label, {{ fill: colors.muted }});
          lx += item.label.length * 7 + 52;
        }});
      }}
      container.appendChild(svg);
    }}

    function drawBarChart(container, dataRows, opts) {{
      const width = opts.width || 900;
      const height = opts.height || 280;
      const margin = Object.assign({{ top: 16, right: 16, bottom: 42, left: 48 }}, opts.margin || {{}});
      const svg = makeBaseSvg(width, height);
      const plot = {{
        x: margin.left,
        y: margin.top,
        w: width - margin.left - margin.right,
        h: height - margin.top - margin.bottom
      }};
      const maxY = Math.max(...dataRows.map(d => d.value));
      const barWidth = plot.w / dataRows.length;
      const yScale = scaleLinear(0, maxY, plot.y + plot.h, plot.y);
      [0, maxY * 0.25, maxY * 0.5, maxY * 0.75, maxY].forEach(tick => {{
        const py = yScale(tick);
        svg.appendChild(svgEl('line', {{ x1: plot.x, y1: py, x2: plot.x + plot.w, y2: py, stroke: 'rgba(255,255,255,0.08)' }}));
        addText(svg, plot.x - 8, py + 4, opts.yFormatter(tick), {{ 'text-anchor': 'end' }});
      }});
      dataRows.forEach((row, idx) => {{
        const x = plot.x + idx * barWidth + barWidth * 0.14;
        const y = yScale(row.value);
        const h = plot.y + plot.h - y;
        svg.appendChild(svgEl('rect', {{
          x, y,
          width: barWidth * 0.72,
          height: h,
          rx: 2,
          fill: row.color || opts.color
        }}));
        addText(svg, x + barWidth * 0.36, plot.y + plot.h + 18, opts.xFormatter(row.label), {{
          'text-anchor': 'middle'
        }});
      }});
      container.appendChild(svg);
    }}

    function drawStackedBarChart(container, rows, opts) {{
      const width = opts.width || 900;
      const height = opts.height || 280;
      const margin = Object.assign({{ top: 20, right: 18, bottom: 42, left: 18 }}, opts.margin || {{}});
      const svg = makeBaseSvg(width, height);
      const plot = {{
        x: margin.left,
        y: margin.top,
        w: width - margin.left - margin.right,
        h: height - margin.top - margin.bottom
      }};
      const barWidth = plot.w / rows.length;
      rows.forEach((row, idx) => {{
        let yCursor = plot.y + plot.h;
        opts.keys.forEach(key => {{
          const value = row[key];
          const h = plot.h * value;
          yCursor -= h;
          svg.appendChild(svgEl('rect', {{
            x: plot.x + idx * barWidth + barWidth * 0.18,
            y: yCursor,
            width: barWidth * 0.64,
            height: h,
            fill: opts.colors[key]
          }}));
        }});
        svg.appendChild(svgEl('rect', {{
          x: plot.x + idx * barWidth + barWidth * 0.18,
          y: plot.y,
          width: barWidth * 0.64,
          height: plot.h,
          fill: 'none',
          stroke: 'rgba(255,255,255,0.08)'
        }}));
        addText(svg, plot.x + idx * barWidth + barWidth * 0.5, plot.y + plot.h + 18, monthLabel(row.month), {{
          'text-anchor': 'middle'
        }});
        svg.appendChild(svgEl('rect', {{
          x: plot.x + idx * barWidth + barWidth * 0.26,
          y: plot.y + plot.h + 24,
          width: barWidth * 0.48,
          height: 8,
          fill: row.dominant_color
        }}));
      }});
      const legendY = 14;
      let legendX = plot.x;
      opts.keys.forEach(key => {{
        svg.appendChild(svgEl('rect', {{ x: legendX, y: legendY - 9, width: 14, height: 14, fill: opts.colors[key] }}));
        addText(svg, legendX + 20, legendY + 2, key.replace('_share', ''), {{ fill: colors.muted }});
        legendX += 88;
      }});
      container.appendChild(svg);
    }}

    function drawScatterTimeline(container, rows, opts) {{
      const width = opts.width || 900;
      const height = opts.height || 280;
      const margin = Object.assign({{ top: 16, right: 18, bottom: 40, left: 40 }}, opts.margin || {{}});
      const svg = makeBaseSvg(width, height);
      const plot = {{
        x: margin.left,
        y: margin.top,
        w: width - margin.left - margin.right,
        h: height - margin.top - margin.bottom
      }};
      const xs = rows.map(r => new Date(r.start).getTime());
      const ys = rows.map(r => r.score);
      const xScale = scaleLinear(Math.min(...xs), Math.max(...xs), plot.x, plot.x + plot.w);
      const yScale = scaleLinear(0, Math.max(...ys) * 1.1, plot.y + plot.h, plot.y);
      [0, 0.25, 0.5, 0.75, 1].forEach(part => {{
        const tickValue = Math.max(...ys) * part;
        const py = yScale(tickValue);
        svg.appendChild(svgEl('line', {{ x1: plot.x, y1: py, x2: plot.x + plot.w, y2: py, stroke: 'rgba(255,255,255,0.08)' }}));
        addText(svg, plot.x - 8, py + 4, fmt(tickValue, 0), {{ 'text-anchor': 'end' }});
      }});
      rows.forEach(row => {{
        const cx = xScale(new Date(row.start).getTime());
        const cy = yScale(row.score);
        const r = 4 + Math.min(16, row.duration_h * 2);
        svg.appendChild(svgEl('circle', {{ cx, cy, r, fill: opts.color, opacity: 0.82 }}));
      }});
      rows.forEach((row, idx) => {{
        if (idx > 4) return;
        const cx = xScale(new Date(row.start).getTime());
        const cy = yScale(row.score);
        addText(svg, cx + 8, cy - 8, row.label, {{ fill: colors.text }});
      }});
      const tickTimes = [0, 0.25, 0.5, 0.75, 1].map(part => Math.min(...xs) + (Math.max(...xs) - Math.min(...xs)) * part);
      tickTimes.forEach(ms => {{
        addText(svg, xScale(ms), plot.y + plot.h + 18, new Date(ms).toLocaleDateString(undefined, {{ month: 'short', year: '2-digit' }}), {{
          'text-anchor': 'middle'
        }});
      }});
      container.appendChild(svg);
    }}

    function drawPressureLine(container, rows) {{
      const series = [{{
        color: colors.indigo,
        data: rows.map(row => ({{
          x: new Date(row.month + '-01').getTime(),
          y: row.pressure
        }}))
      }}];
      const ticks = rows.map(row => new Date(row.month + '-01').getTime());
      drawLineChart(container, series, {{
        width: 900,
        height: 260,
        xTicks: ticks,
        yTicks: [990, 995, 1000, 1005, 1010, 1015],
        xFormatter: value => monthLabel(new Date(value).toISOString().slice(0, 7)),
        yFormatter: value => fmt(value, 0) + ' hPa'
      }});
    }}

    function buildSection(index, title, question, finding, methodText, renderViz) {{
      const section = el('section', 'section');
      const meta = el('div', 'section-meta');
      meta.appendChild(el('div', 'section-index', index));
      meta.appendChild(el('h2', '', title));
      meta.appendChild(el('p', '', question));
      section.appendChild(meta);
      const vizWrap = el('div', 'viz-wrap');
      const viz = el('div', 'viz');
      renderViz(viz);
      vizWrap.appendChild(viz);
      vizWrap.appendChild(el('p', 'finding', finding));
      vizWrap.appendChild(el('p', 'method', methodText));
      section.appendChild(vizWrap);
      return section;
    }}

    function render() {{
      const app = document.getElementById('app');
      const hero = el('section', 'hero');
      const left = el('div', 'headline-card');
      left.appendChild(el('div', 'eyebrow', 'Quantified Self Environmental Archive'));
      left.appendChild(el('h1', '', data.meta.title));
      left.appendChild(el('p', 'subtitle', data.meta.subtitle));
      hero.appendChild(left);
      const right = el('div', 'headline-card');
      const stat = el('div', 'headline-stat');
      stat.innerHTML = `${{fmt(data.meta.headline_value, 1)}}<span class="headline-unit">${{data.meta.headline_unit}}</span>`;
      right.appendChild(stat);
      right.appendChild(el('div', 'headline-label', data.meta.headline_label));
      hero.appendChild(right);
      app.appendChild(hero);

      const kpis = el('div', 'kpi-strip');
      data.meta.kpis.forEach(kpi => {{
        const card = el('div', 'kpi');
        card.appendChild(el('div', 'kpi-label', kpi.label));
        card.appendChild(el('div', 'kpi-value', fmt(kpi.value, kpi.unit === 'seconds' ? 1 : 0)));
        card.appendChild(el('div', 'kpi-unit', kpi.unit));
        kpis.appendChild(card);
      }});
      app.appendChild(kpis);

      app.appendChild(buildSection(
        '01',
        'Seasonal Light',
        'How does the office light signature move across the year?',
        data.insights.seasonal_light,
        'Aggregation: per local day with at least 50 samples and meaningful brightness, take the brightest moment and the span covered by that day\\'s top 10% light readings; summarize by month. Light is APDS9960 clear-channel counts, not lux.',
        viz => {{
          drawLineChart(viz, [
            {{
              color: colors.amber,
              data: data.sections.seasonal_light.map(row => ({{
                x: new Date(row.month + '-01').getTime(),
                y: row.peak_hour
              }}))
            }},
            {{
              color: colors.cyan,
              data: data.sections.seasonal_light.map(row => ({{
                x: new Date(row.month + '-01').getTime(),
                y: row.bright_span_h + 7
              }}))
            }}
          ], {{
            width: 900,
            height: 300,
            xTicks: data.sections.seasonal_light.map(row => new Date(row.month + '-01').getTime()),
            yTicks: [8, 10, 12, 14, 16],
            xFormatter: value => monthLabel(new Date(value).toISOString().slice(0, 7)),
            yFormatter: value => hourLabel(value),
            legend: [
              {{ label: 'Median brightest hour', color: colors.amber }},
              {{ label: 'Bright-window span, offset upward', color: colors.cyan }}
            ]
          }});
        }}
      ));

      app.appendChild(buildSection(
        '02',
        'Office Pulse',
        'What does a typical active day feel like compared with a quiet one?',
        data.insights.activity_profile,
        `Aggregation: classify days by the mean percentile rank of daily light and sound (top quartile = active, bottom quartile = quiet), then plot hourly medians within each class. Active days: ${{data.sections.activity_class_counts.active || 0}}. Quiet days: ${{data.sections.activity_class_counts.quiet || 0}}.`,
        viz => {{
          drawLineChart(viz, [
            {{
              color: colors.emerald,
              data: data.sections.activity_profile.map(row => ({{ x: row.hour, y: row.active_light }}))
            }},
            {{
              color: colors.gray,
              data: data.sections.activity_profile.map(row => ({{ x: row.hour, y: row.quiet_light }}))
            }},
            {{
              color: colors.teal,
              data: data.sections.activity_profile.map(row => ({{ x: row.hour, y: row.active_sound * 20 }}))
            }},
            {{
              color: colors.rose,
              data: data.sections.activity_profile.map(row => ({{ x: row.hour, y: row.quiet_sound * 20 }}))
            }}
          ], {{
            width: 900,
            height: 300,
            xTicks: [0, 4, 8, 12, 16, 20, 23],
            yTicks: [0, 500, 1000, 1500, 2000],
            xFormatter: value => hourLabel(value),
            yFormatter: value => fmt(value, 0),
            legend: [
              {{ label: 'Active-day light', color: colors.emerald }},
              {{ label: 'Quiet-day light', color: colors.gray }},
              {{ label: 'Active-day sound x20', color: colors.teal }},
              {{ label: 'Quiet-day sound x20', color: colors.rose }}
            ]
          }});
        }}
      ));

      app.appendChild(buildSection(
        '03',
        'Heat Lag',
        'Does the room warm after it brightens, and how long does that lag seem to be?',
        data.insights.heat_lag,
        'Aggregation: resample to 1-hour local bins, compare median light to median temperature at lags from -12 to +12 hours, and plot the resulting correlation profile. Positive lag means temperature follows light later.',
        viz => {{
          drawBarChart(viz, data.sections.lag_profile.map(row => ({{
            label: row.lag_hours,
            value: Math.max(0, row.correlation || 0),
            color: row.lag_hours >= 0 ? colors.orange : colors.gray
          }})), {{
            width: 900,
            height: 280,
            xFormatter: value => `${{value}}h`,
            yFormatter: value => fmt(value, 2),
            color: colors.orange
          }});
        }}
      ));

      app.appendChild(buildSection(
        '04',
        'Color Regimes',
        'Are there distinct lighting regimes over time rather than one stable room color?',
        data.insights.color_modes,
        'Aggregation: classify each valid hex color as dark, warm, cool, or neutral using brightness and red-vs-blue balance, then compute monthly shares. The thin strip under each month is the mean of that month\\'s first 200 valid colors.',
        viz => {{
          drawStackedBarChart(viz, data.sections.color_modes, {{
            width: 900,
            height: 320,
            keys: ['dark_share', 'warm_share', 'neutral_share', 'cool_share'],
            colors: {{
              dark_share: colors.gray,
              warm_share: colors.orange,
              neutral_share: colors.orangePale,
              cool_share: colors.cyan
            }}
          }});
        }}
      ));

      app.appendChild(buildSection(
        '05',
        'Stress Windows',
        'When does the room become least comfortable if we only count obvious heat, dryness, and noise stressors?',
        data.insights.discomfort,
        'Aggregation: discomfort = max(temp - 88 F, 0) * 0.5 + max(22 - humidity, 0) + max(sound - 120, 0) * 0.03, summarized by local hour using the 95th percentile. This is an engineering heuristic, not a physiological index.',
        viz => {{
          drawLineChart(viz, [
            {{
              color: colors.rose,
              data: data.sections.discomfort_by_hour.map(row => ({{ x: row.hour, y: row.discomfort_p95 }}))
            }}
          ], {{
            width: 900,
            height: 280,
            xTicks: [0, 4, 8, 12, 16, 20, 23],
            yTicks: [0, 1, 2, 3, 4],
            xFormatter: value => hourLabel(value),
            yFormatter: value => fmt(value, 1)
          }});
        }}
      ));

      app.appendChild(buildSection(
        '06',
        'Anomaly Episodes',
        'Which moments were genuinely strange rather than just slightly above average?',
        data.insights.anomalies,
        'Aggregation: resample to 1-hour bins, compute robust z-scores for temperature, humidity, pressure, light, and sound, sum the absolute values, then merge adjacent extreme hours into episodes.',
        viz => {{
          drawScatterTimeline(viz, data.sections.anomaly_events, {{ color: colors.rose }});
        }}
      ));

      app.appendChild(buildSection(
        '07',
        'Routine Shifts',
        'Did the office routine itself change over the year?',
        data.insights.routine,
        'Aggregation: by month, estimate active hours per day from hourly bins where median light exceeds 300 clear counts or upper-quartile sound exceeds 20 RMS, then track median light, sound, and temperature context.',
        viz => {{
          drawLineChart(viz, [
            {{
              color: colors.emerald,
              data: data.sections.routine.map(row => ({{
                x: new Date(row.month + '-01').getTime(),
                y: row.active_hours_per_day
              }}))
            }}
          ], {{
            width: 900,
            height: 280,
            xTicks: data.sections.routine.map(row => new Date(row.month + '-01').getTime()),
            yTicks: [0, 4, 8, 12, 16, 20],
            xFormatter: value => monthLabel(new Date(value).toISOString().slice(0, 7)),
            yFormatter: value => fmt(value, 0) + ' h'
          }});
        }}
      ));

      app.appendChild(buildSection(
        '08',
        'Pressure Context',
        'Is barometric pressure telling us anything beyond slow background weather drift?',
        data.insights.pressure,
        'Aggregation: daily median pressure by month plus daily correlation checks against temperature, humidity, light, and sound. Pressure is useful here mostly as context, not as an explanation for occupancy-like behavior.',
        viz => {{
          drawPressureLine(viz, data.sections.pressure_monthly);
          const pills = el('div', 'pill-row');
          Object.entries(data.sections.pressure_corr).forEach(([key, value]) => {{
            if (key === 'pressure') return;
            pills.appendChild(el('div', 'pill', `${{key}} r=${{fmt(value, 2)}}`));
          }});
          viz.appendChild(pills);
        }}
      ));

      app.appendChild(buildSection(
        '09',
        'Weather Coupling',
        'What does the outdoor weather actually explain about the room, and what stays stubbornly indoor?',
        data.insights.weather,
        'Aggregation: join hourly indoor rollups to hourly Nashville weather, then compare monthly indoor and outdoor median temperature, daily rainy-vs-dry medians, and hourly lag correlation. Outdoor temperature is in degrees Fahrenheit converted from the source Celsius feed; outdoor pressure is mean sea level pressure in hPa.',
        viz => {{
          drawLineChart(viz, [
            {{
              color: colors.orange,
              data: data.sections.monthly_coupling.map(row => ({{
                x: new Date(row.month + '-01').getTime(),
                y: row.indoor_temp_f
              }}))
            }},
            {{
              color: colors.cyan,
              data: data.sections.monthly_coupling.map(row => ({{
                x: new Date(row.month + '-01').getTime(),
                y: row.outdoor_temp_f
              }}))
            }}
          ], {{
            width: 900,
            height: 280,
            xTicks: data.sections.monthly_coupling.map(row => new Date(row.month + '-01').getTime()),
            yTicks: [20, 40, 60, 80, 100],
            xFormatter: value => monthLabel(new Date(value).toISOString().slice(0, 7)),
            yFormatter: value => fmt(value, 0) + ' F',
            legend: [
              {{ label: 'Indoor median', color: colors.orange }},
              {{ label: 'Outdoor median', color: colors.cyan }}
            ]
          }});
          const pills = el('div', 'pill-row');
          pills.appendChild(el('div', 'pill', `temp r=${{fmt(data.sections.weather_compare.indoor_outdoor_temp_corr, 2)}}`));
          pills.appendChild(el('div', 'pill', `pressure r=${{fmt(data.sections.weather_compare.indoor_outdoor_pressure_corr, 2)}}`));
          pills.appendChild(el('div', 'pill', `pressure gap ${{fmt(data.sections.weather_compare.pressure_gap_median_hpa, 1)}} hPa`));
          pills.appendChild(el('div', 'pill', `rainy-day light ${{fmt(data.sections.weather_compare.rainy_day_indoor_light_median, 0)}} vs dry ${{fmt(data.sections.weather_compare.dry_day_indoor_light_median, 0)}}`));
          pills.appendChild(el('div', 'pill', `rainy-day sound ${{fmt(data.sections.weather_compare.rainy_day_indoor_sound_median, 0)}} vs dry ${{fmt(data.sections.weather_compare.dry_day_indoor_sound_median, 0)}}`));
          viz.appendChild(pills);
        }}
      ));

      const footer = el('section', 'footer');
      footer.appendChild(el('div', 'eyebrow', 'Provenance'));
      footer.appendChild(el('p', '', `Sources: ${{data.provenance.source_file}}${{data.provenance.weather_file ? ' and ' + data.provenance.weather_file : ''}}. Rows after timestamp cleaning: ${{fmtInt(data.provenance.rows_after_timestamp_cleaning)}}. UTC range: ${{data.provenance.date_range_utc.start}} to ${{data.provenance.date_range_utc.end}}.`));
      const grid = el('div', 'footer-grid');

      const leftCard = el('div', 'footer-card');
      leftCard.appendChild(el('h3', '', 'Cleaning'));
      const cleanList = el('ul', '');
      Object.entries(data.provenance.dropped_or_masked).forEach(([key, value]) => {{
        const li = el('li', '', `${{key.replaceAll('_', ' ')}}: ${{fmtInt(value)}}`);
        cleanList.appendChild(li);
      }});
      leftCard.appendChild(cleanList);
      grid.appendChild(leftCard);

      const rightCard = el('div', 'footer-card');
      rightCard.appendChild(el('h3', '', 'Largest Gaps'));
      const gapTable = el('table', 'table');
      gapTable.innerHTML = '<thead><tr><th>Restart / gap</th><th>When</th><th>Duration</th></tr></thead>';
      const gapBody = el('tbody', '');
      data.provenance.major_gaps.slice(0, 6).forEach((row, idx) => {{
        const tr = el('tr', '');
        tr.innerHTML = `<td>${{idx + 1}}</td><td class="mono">${{row.local_ts}}</td><td>${{fmt(row.gap_hours, 1)}} hours</td>`;
        gapBody.appendChild(tr);
      }});
      gapTable.appendChild(gapBody);
      rightCard.appendChild(gapTable);
      grid.appendChild(rightCard);

      const schemaCard = el('div', 'footer-card');
      schemaCard.appendChild(el('h3', '', 'Schema'));
      const schemaTable = el('table', 'table');
      schemaTable.innerHTML = '<thead><tr><th>Field</th><th>Type</th><th>Null %</th><th>Range / notes</th></tr></thead>';
      const schemaBody = el('tbody', '');
      data.schema.forEach(row => {{
        const range = row.type === 'numeric'
          ? `${{fmt(row.min, 1)}} to ${{fmt(row.max, 1)}}`
          : row.type === 'datetime'
            ? `${{row.date_min.slice(0, 10)}} to ${{row.date_max.slice(0, 10)}}`
            : `${{row.unique_nonnull.toLocaleString()}} unique`;
        const tr = el('tr', '');
        tr.innerHTML = `<td class="mono">${{row.name}}</td><td>${{row.type}}</td><td>${{fmt(row.null_rate, 3)}}</td><td>${{range}}</td>`;
        schemaBody.appendChild(tr);
      }});
      schemaTable.appendChild(schemaBody);
      grid.appendChild(schemaCard);

      const anomalyCard = el('div', 'footer-card');
      anomalyCard.appendChild(el('h3', '', 'Top Episodes'));
      const anomalyTable = el('table', 'table');
      anomalyTable.innerHTML = '<thead><tr><th>When</th><th>Score</th><th>Why it stands out</th></tr></thead>';
      const anomalyBody = el('tbody', '');
      data.sections.anomaly_events.slice(0, 6).forEach(row => {{
        const tr = el('tr', '');
        tr.innerHTML = `<td>${{isoLocal(row.start)}}</td><td>${{fmt(row.score, 0)}}</td><td>${{row.label}}</td>`;
        anomalyBody.appendChild(tr);
      }});
      anomalyTable.appendChild(anomalyBody);
      anomalyCard.appendChild(anomalyTable);
      grid.appendChild(anomalyCard);

      footer.appendChild(grid);
      app.appendChild(footer);
    }}

    render();
  </script>
</body>
</html>
"""


def main():
    data = build_rollups()
    html = build_html(data)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
