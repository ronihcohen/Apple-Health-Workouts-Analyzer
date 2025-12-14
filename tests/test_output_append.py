import csv
import sys
from pathlib import Path

import pandas as pd

import workouts


def _write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def test_append_skips_duplicates(tmp_path: Path, capsys):
    rows = [
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
    ]

    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    _write_csv(in_csv, rows)

    # First run writes the output
    sys.argv = ["workouts.py", str(in_csv), str(out_csv)]
    workouts.main()
    df = pd.read_csv(out_csv)
    assert len(df) == 1

    # Second run should detect no new runs and not duplicate
    sys.argv = ["workouts.py", str(in_csv), str(out_csv)]
    workouts.main()
    captured = capsys.readouterr()
    assert "No new runs to add" in captured.out
    df2 = pd.read_csv(out_csv)
    assert len(df2) == 1


def test_append_adds_new_workout(tmp_path: Path):
    rows1 = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"],
        ["","Device A","","","2025-01-01 06:00:00","2025-01-01 07:00:00","","60","","HKWorkoutActivityTypeRunning"],
        ["DistanceWalkingRunning","","10","km","2025-01-01 06:00:00","2025-01-01 07:00:00","","",""],
    ]

    rows2 = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"],
        ["","Device A","","","2025-01-02 06:00:00","2025-01-02 07:00:00","","60","","HKWorkoutActivityTypeRunning"],
        ["DistanceWalkingRunning","","8","km","2025-01-02 06:00:00","2025-01-02 07:00:00","","",""],
    ]

    in1 = tmp_path / "in1.csv"
    in2 = tmp_path / "in2.csv"
    out = tmp_path / "out.csv"
    _write_csv(in1, rows1)
    _write_csv(in2, rows2)

    sys.argv = ["workouts.py", str(in1), str(out)]
    workouts.main()
    df = pd.read_csv(out)
    assert len(df) == 1

    sys.argv = ["workouts.py", str(in2), str(out)]
    workouts.main()
    df2 = pd.read_csv(out)
    assert len(df2) == 2
