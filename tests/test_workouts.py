import csv
from pathlib import Path

import pandas as pd

from workouts import extract_runs


def test_extract_runs_simple(tmp_path: Path):
    data = [
        [
            "type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"
        ],
        [
            "","Roni’s Apple Watch","","","2025-12-11 05:24:18","2025-12-11 06:46:52","2025-12-11 06:47:09","82.5575146","","HKWorkoutActivityTypeRunning"
        ],
        [
            "ActiveEnergyBurned","","1010.99","Cal","2025-12-11 05:24:18","2025-12-11 06:46:52","","",""
        ],
        [
            "DistanceWalkingRunning","","9.36978","km","2025-12-11 05:24:18","2025-12-11 06:46:52","","",""
        ],
        [
            "HeartRate","","","count/min","2025-12-11 05:24:18","2025-12-11 06:46:52","","","84"
        ],
        [
            "BodyMass","Withings","103.206","kg","2025-12-13 05:55:46","","","","",""
        ],
    ]

    csv_path = tmp_path / "input.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    out_df = extract_runs(str(csv_path))
    assert len(out_df) == 1
    row = out_df.iloc[0]
    assert round(row["distance_km"], 5) == round(9.36978, 5)
    assert round(row["energy_cal"], 2) == round(1010.99, 2)
    assert round(row["duration_min"], 4) == round(82.5575146, 4)
    assert row["avg_hr"] == 84.0

    # pace = duration / distance
    expected_pace = 82.5575146 / 9.36978
    assert abs(row["pace_min_per_km"] - round(expected_pace, 2)) < 0.01
    # weight within +/-7 days should be attached
    assert abs(row["weight_kg"] - 103.206) < 1e-6


def test_weight_nearest_and_range(tmp_path: Path):
    # Workout on 2025-12-11; several body-mass entries near/far — choose nearest within 7d
    rows = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"],
        ["","Watch","","","2025-12-11 05:24:18","2025-12-11 06:46:52","2025-12-11 06:47:09","82.5575146","","HKWorkoutActivityTypeRunning"],
        ["BodyMass","Withings","100","kg","2025-12-05 05:55:46","","","","",""],  # 6 days before
        ["BodyMass","Withings","103","kg","2025-12-13 05:55:46","","","","",""],  # 2 days after (closest)
        ["BodyMass","Withings","110","kg","2025-12-21 05:55:46","","","","",""],  # 10 days after (out of range)
    ]

    p = tmp_path / "input_weight.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    out = extract_runs(str(p))
    assert len(out) == 1
    r = out.iloc[0]
    assert abs(r["weight_kg"] - 103.0) < 1e-6


def test_weight_out_of_range(tmp_path: Path):
    # Workout on 2025-12-11; only a weight 10 days away -> no weight attached
    rows = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"],
        ["","Watch","","","2025-12-11 05:24:18","2025-12-11 06:46:52","2025-12-11 06:47:09","82.5575146","","HKWorkoutActivityTypeRunning"],
        ["BodyMass","Withings","110","kg","2025-12-21 05:55:46","","","","",""],  # 10 days after
    ]

    p = tmp_path / "input_weight2.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    out = extract_runs(str(p))
    assert len(out) == 1
    r = out.iloc[0]
    assert r["weight_kg"] is None
