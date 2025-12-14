#!/usr/bin/env python3
"""Extract running workouts from Apple Health CSV export

Reads an Apple Health export CSV (the one produced by `script.py`) and
produces a CSV with one line per run including date, duration (min),
distance (km), energy burned (Cal), average heart rate (bpm), and pace
(min/km).

Usage:
    python workouts.py input.csv output.csv

"""
from __future__ import annotations

import argparse
import math
from typing import Optional

import pandas as pd


def _to_km(v, unit: str) -> float:
    """Normalize a distance value to kilometers.

    Returns the distance in kilometers, or raises ValueError for invalid numeric input.
    """
    unit = (unit or "").lower()
    if pd.isna(v):
        raise ValueError("value is NaN")
    v = float(v)
    if "km" in unit:
        return v
    if unit in ("m", "meter", "metre", "meters", "metres"):
        return v / 1000.0
    if unit in ("mi", "mile", "miles"):
        return v * 1.60934
    return v


def _get_numeric_from_row(r, candidates):
    """Return the first numeric value found in `r` from the list of candidate column names.

    Returns float or None if none found.
    """
    for c in candidates:
        if c in r.index:
            try:
                v = pd.to_numeric(r.get(c), errors="coerce")
            except Exception:
                v = None
            if pd.notna(v):
                return float(v)
    return None


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    # Try to parse startDate and endDate into datetimes. Accept multiple formats.
    for col in ("startDate", "endDate"):
        if col in df.columns:
            # 'infer_datetime_format' is deprecated; pandas will use a strict parser by default
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df



def get_overlapping_rows(df: pd.DataFrame, dtype: str, start, end) -> pd.DataFrame:
    """Return rows of given type whose time intervals overlap the workout interval.

    Overlap rules:
    - If a row has both startDate and endDate: overlap when row.start <= workout.end and row.end >= workout.start
    - If a row only has startDate: treat as a point and include when row.start is between workout.start and workout.end
    """
    subset = df[df["type"] == dtype].copy()
    # Require a valid startDate for matching
    subset = subset[pd.notna(subset["startDate"])]
    if subset.empty:
        return subset.iloc[0:0]

    both_dates = pd.notna(subset["endDate"])
    overlap_both = both_dates & (subset["startDate"] <= end) & (subset["endDate"] >= start)
    point_rows = (~both_dates) & (subset["startDate"] >= start) & (subset["startDate"] <= end)
    mask = overlap_both | point_rows
    return subset[mask]


def extract_runs(in_csv: str) -> pd.DataFrame:
    df = pd.read_csv(in_csv, dtype=str)
    df = parse_dates(df)

    # Normalize type column (some exports include the HK prefix)
    if "type" in df.columns:
        df["type"] = df["type"].str.replace("HKQuantityTypeIdentifier", "", regex=False)
        df["type"] = df["type"].str.replace("HKCategoryTypeIdentifier", "", regex=False)

    runs = []

    # Identify running workouts
    if "workoutActivityType" not in df.columns:
        raise ValueError("Input CSV does not contain 'workoutActivityType' column")

    workouts = df[df["workoutActivityType"].str.contains("HKWorkoutActivityTypeRunning", na=False)]

    # Prepare body mass (weight) rows for proximity lookup
    bodymass_rows = None
    if "type" in df.columns:
        bodymass_rows = df[df["type"] == "BodyMass"].copy()
        # Require a valid startDate for matching and ensure it's datetime
        if not bodymass_rows.empty:
            bodymass_rows = bodymass_rows[pd.notna(bodymass_rows["startDate"])].copy()

    for _, w in workouts.iterrows():
        start = w.get("startDate")
        end = w.get("endDate")

        duration = None
        # duration is usually in minutes in 'duration' column
        try:
            duration = float(w.get("duration")) if pd.notna(w.get("duration")) else None
        except Exception:
            duration = None

        # Find metric rows that overlap the workout interval
        energy_rows = get_overlapping_rows(df, "ActiveEnergyBurned", start, end)
        dist_rows = get_overlapping_rows(df, "DistanceWalkingRunning", start, end)
        hr_rows = get_overlapping_rows(df, "HeartRate", start, end)

        energy = None
        distance = None
        avg_hr = None

        # Sum energies (values are typically in Calories)
        if not energy_rows.empty:
            vals = pd.to_numeric(energy_rows["value"], errors="coerce")
            if vals.notna().any():
                energy = float(vals.sum())

        # Prefer exact-match distance rows (start==workout.start and end==workout.end)
        exact_dist = df[(df["type"] == "DistanceWalkingRunning") & (df["startDate"] == start) & (df["endDate"] == end)]

        # Local helpers were moved to module-level to avoid recreating them per workout

        if not exact_dist.empty:
            # Prefer rows from the same source as the workout
            workout_source = w.get("sourceName")
            same_source = exact_dist[exact_dist.get("sourceName") == workout_source]
            if not same_source.empty:
                # pick the maximum value among matches from same source (robust against duplicates)
                vals = [ _get_numeric_from_row(r, ["value", "sum"]) for _, r in same_source.iterrows() ]
                vals = [v for v in vals if v is not None]
                if vals:
                    distance = float(max(vals))
            else:
                # No same-source exact match: pick the largest exact distance to avoid double-counting duplicates
                vals = [ _get_numeric_from_row(r, ["value", "sum"]) for _, r in exact_dist.iterrows() ]
                vals = [v for v in vals if v is not None]
                if vals:
                    distance = float(max(vals))
        else:
            # Sum distances with simple unit normalization (km, m -> km, mi -> km)
            if not dist_rows.empty:
                total_km = 0.0
                found = False
                for _, r in dist_rows.iterrows():
                    v = _get_numeric_from_row(r, ["value", "sum"])
                    if v is None:
                        continue
                    total_km += _to_km(v, r.get("unit"))
                    found = True
                if found:
                    distance = total_km

        # Heart rate: average the 'average' values if present, otherwise the 'value' fields
        if not hr_rows.empty:
            hr_vals = pd.to_numeric(hr_rows.get("average"), errors="coerce")
            if hr_vals.notna().any():
                avg_hr = float(hr_vals.mean())
            else:
                hr_vals2 = pd.to_numeric(hr_rows.get("value"), errors="coerce")
                if hr_vals2.notna().any():
                    avg_hr = float(hr_vals2.mean())

        # Calculate pace (min per km)
        pace = None
        pace_mmss = None
        if duration is not None and distance is not None and distance > 0:
            pace = duration / distance
            # Convert fractional minutes to mm:ss
            minutes = int(math.floor(pace))
            seconds = int(round((pace - minutes) * 60))
            if seconds == 60:
                minutes += 1
                seconds = 0
            pace_mmss = f"{minutes:02d}:{seconds:02d}"

        # Weight: find nearest BodyMass within +/-7 days (choose the closest in time)
        weight = None
        if bodymass_rows is not None and not bodymass_rows.empty and pd.notna(start):
            # compute absolute time difference and filter within 7 days
            diffs = (bodymass_rows["startDate"] - pd.to_datetime(start)).abs()
            within = diffs <= pd.Timedelta(days=7)
            if within.any():
                candidate = bodymass_rows[within].iloc[diffs[within].argmin()]
                # get numeric from 'value' or 'sum'
                weight_val = _get_numeric_from_row(candidate, ["value", "sum"])
                if weight_val is not None:
                    weight = float(weight_val)

        runs.append({
            "date": pd.to_datetime(start).date() if pd.notna(start) else None,
            # keep start/end in the output to enable precise duplicate detection when re-running
            "startDate": start,
            "endDate": end,
            "duration_min": duration,
            "distance_km": distance,
            "energy_cal": energy,
            "avg_hr": avg_hr,
            "pace_min_per_km": round(pace, 2) if pace is not None else None,
            "weight_kg": weight,
        })

    return pd.DataFrame(runs)


def main():
    parser = argparse.ArgumentParser(description="Extract running workouts from Apple Health CSV")
    parser.add_argument("input", help="Input CSV file (Apple Health export)")
    parser.add_argument("output", help="Output CSV file to write runs to")
    args = parser.parse_args()

    out_df = extract_runs(args.input)
    # If the output file exists, append only new workouts (avoid duplicates).
    if pd.io.common.file_exists(args.output):
        try:
            existing = pd.read_csv(args.output, dtype=str)
        except Exception:
            existing = pd.DataFrame()

        # Normalize types for comparison
        if not existing.empty and "startDate" in existing.columns and "endDate" in existing.columns:
            # Use start/end tuple matching when available
            existing_keys = set(zip(existing["startDate"].astype(str), existing["endDate"].astype(str)))
            def is_new_row(r):
                k = (str(r.get("startDate")), str(r.get("endDate")))
                return k not in existing_keys
        else:
            # Fallback: use (date, duration_min rounded, distance_km rounded) tuple
            def round_or_none(x, ndigits):
                try:
                    return round(float(x), ndigits) if pd.notna(x) else None
                except Exception:
                    return None

            if not existing.empty and "date" in existing.columns:
                existing_keys = set()
                for _, r in existing.iterrows():
                    existing_keys.add((str(r.get("date")), round_or_none(r.get("duration_min"), 4), round_or_none(r.get("distance_km"), 5)))

            def is_new_row(r):
                key = (str(r.get("date")), round_or_none(r.get("duration_min"), 4), round_or_none(r.get("distance_km"), 5))
                return key not in existing_keys

        new_rows = [r for _, r in out_df.iterrows() if is_new_row(r)]
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            # preserve existing columns order and append any new columns
            combined = pd.concat([existing, new_df], ignore_index=True, sort=False)
            combined.to_csv(args.output, index=False)
            print(f"Appended {len(new_df)} new run(s) to {args.output} (total {len(combined)})")
        else:
            print(f"No new runs to add to {args.output}")
    else:
        out_df.to_csv(args.output, index=False)
        print(f"Wrote {len(out_df)} runs to {args.output}")


if __name__ == "__main__":
    main()
