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
