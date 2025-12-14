# Apple Health Workouts Analyzer ⚙️

## 🚀 Overview

This small toolset reads Apple Health CSV exports and extracts running workouts with their associated metrics. It is designed to work with the CSV output produced by jameno/Simple-Apple-Health-XML-to-CSV (https://github.com/jameno/Simple-Apple-Health-XML-to-CSV). It handles cases where metrics are split across multiple rows (interval overlap), where some metrics are stored in nonstandard columns, and prefers exact matches when available to avoid double-counting.

## ✨ Features

- Finds workouts where `workoutActivityType` contains `HKWorkoutActivityTypeRunning`.
- Matches and aggregates associated rows for:
  - `DistanceWalkingRunning` (distance in km, supports unit normalization)
  - `ActiveEnergyBurned` (Calories)
  - `HeartRate` (average)
- Interval-overlap matching: includes metric rows that overlap the workout time window (handles partial segments and split GPS laps).
- Prefer exact-match distance rows when available (prefers the workout's `sourceName`), else fall back to aggregated overlapping segments.
- Pace calculation: minutes per kilometer and mm:ss formatting.
- Unit tests to validate behavior and edge cases.

## 📦 Files

- `workouts.py` — main CLI script to extract runs and compute pace.
- `tests/test_workouts.py`, `tests/test_workouts_overlap.py` — pytest tests verifying examples and edge cases.
- `README.md` — root README (overview). This file documents the analyzer under `Analize/`.
- `runs_output.csv` — example output produced from a real export (generated locally).

## 💡 Installation

This project uses Python 3 and depends on `pandas` for CSV handling and `pytest` for tests. You can install dependencies with pip:

```bash
python -m pip install pandas pytest
```

(If you keep a `requirements.txt` or `pyproject.toml` you can add these there.)

## 🧭 Usage

Basic command:

```bash
python workouts.py path/to/apple_health_export.csv runs.csv
```

Example (from repository):

```bash
python workouts.py apple_health_export_2025-12-14.csv runs_output.csv
# produces runs_output.csv (one row per workout)
```

Note: If the output file already exists, `workouts.py` will append only new workouts and avoid adding duplicates. The output now includes `startDate` and `endDate` (in addition to `date`) to enable precise duplicate detection when re-running the script.

Output columns:

- `date` — workout date (YYYY-MM-DD)
- `duration_min` — duration in minutes (float)
- `distance_km` — distance in kilometers (float, may be empty when not available)
- `energy_cal` — active energy burned (Calories, summed from overlapping rows when necessary)
- `avg_hr` — average heart rate (bpm)
- `pace_min_per_km` — pace as float (minutes per km), computed when duration and distance are present

## 🔍 Matching & Calculation Details

- Matching logic looks for workout rows (`HKWorkoutActivityTypeRunning`) and then finds metric rows by interval overlap: a metric row is included when its interval overlaps the workout's interval.
- If a metric row is a point (only `startDate` present), it's included when its timestamp falls inside the workout interval.
- For distances:
  - The script first tries to find *exact-match* `DistanceWalkingRunning` rows (same `startDate` and `endDate` as the workout).
  - If an exact-match exists with the same `sourceName`, that value is preferred (to avoid double-counting alternate sources).
  - If multiple exact-match distances exist and none match the workout's source, the script uses the maximum exact distance (conservative choice to avoid adding duplicated splits).
  - If no exact match exists, the script sums overlapping distance segments and normalizes units (km, m -> km, mi -> km).
- For energy: overlapping energy rows are summed (Calories).
- For heart rate: the script averages available `average` fields; if not present, it averages `value` fields.
- Pace = `duration_min / distance_km` when both are present.

## 🧪 Tests

Run the test suite with:

```bash
python -m pytest -q
```

Relevant tests cover:

- Simple extraction and pace calculation
- Partial distance segments (interval overlap)
- Exact-match preference (choose same-source or maximum)
- Numeric values appearing in alternate columns (e.g., `sum`)

## 🛠 Troubleshooting & Notes

- If the script outputs `distance_km` as empty for a workout, it's usually because no distance rows overlap and no exact distance row is present. Consider checking the export for split segments or alternate unit columns.
- If you see duplicated (too-large) distances, it was often due to summing overlapping rows; the script now prefers exact-match rows to mitigate this.
- The parser attempts to read numeric values from `value` and `sum` columns to handle variations in CSV exports.

