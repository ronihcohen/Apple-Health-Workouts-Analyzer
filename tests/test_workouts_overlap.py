import csv
from pathlib import Path

from workouts import extract_runs


def test_partial_distance_segment(tmp_path: Path):
    # Workout spanning 06:55:12 - 07:27:31
    rows = [
        [
            "type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"
        ],
        [
            "","Roni's Apple Watch","","","2024-05-05 06:55:12","2024-05-05 07:27:31","2024-05-05 07:27:36","32.31028506557147","","HKWorkoutActivityTypeRunning"
        ],
        [
            "DistanceWalkingRunning","Roni's Apple Watch","0.671479","km","2024-05-05 06:55:12","2024-05-05 07:00:17","2024-09-02 13:29:08","",""
        ],
        [
            "ActiveEnergyBurned","","317.693","Cal","2024-05-05 06:55:12","2024-05-05 07:27:31","","",""
        ],
    ]

    p = tmp_path / "input2.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    out = extract_runs(str(p))
    assert len(out) == 1
    r = out.iloc[0]
    assert abs(r["distance_km"] - 0.671479) < 1e-6
    assert abs(r["energy_cal"] - 317.693) < 1e-6


def test_exact_match_prefers_workout_source(tmp_path: Path):
    # Two exact-match distance rows; prefer the one with same sourceName as the workout
    rows = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"],
        ["","Roni's Apple Watch","","","2025-05-07 18:07:34","2025-05-07 18:45:09","","37.58392325043678","","HKWorkoutActivityTypeRunning"],
        ["DistanceWalkingRunning","Roni's Apple Watch","5.01725","km","2025-05-07 18:07:34","2025-05-07 18:45:09","","",""],
        ["DistanceWalkingRunning","Other","5.806481","km","2025-05-07 18:07:34","2025-05-07 18:45:09","","",""],
    ]

    p = tmp_path / "input3.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        import csv as _csv
        w = _csv.writer(f)
        w.writerows(rows)

    out = extract_runs(str(p))
    assert len(out) == 1
    r = out.iloc[0]
    assert abs(r["distance_km"] - 5.01725) < 1e-6


def test_distance_in_sum_column(tmp_path: Path):
    # Distance value stored in 'sum' column (as in some exports)
    rows = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType","sum"],
        ["","Roni's Apple Watch","","km","2025-05-07 18:07:34","2025-05-07 18:45:09","","37.58392325043678","","HKWorkoutActivityTypeRunning",""],
        ["DistanceWalkingRunning","Roni's Apple Watch","","km","2025-05-07 18:07:34","2025-05-07 18:45:09","","","","", "5.01725"],
    ]

    p = tmp_path / "input5.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        import csv as _csv
        w = _csv.writer(f)
        w.writerows(rows)

    out = extract_runs(str(p))
    assert len(out) == 1
    r = out.iloc[0]
    assert abs(r["distance_km"] - 5.01725) < 1e-6


def test_exact_match_no_source_prefers_max(tmp_path: Path):
    # Two exact-match distance rows from different sources, none match workout source -> pick max
    rows = [
        ["type","sourceName","value","unit","startDate","endDate","creationDate","duration","average","workoutActivityType"],
        ["","Some Device","","","2025-05-07 18:07:34","2025-05-07 18:45:09","","37.58392325043678","","HKWorkoutActivityTypeRunning"],
        ["DistanceWalkingRunning","A","5.01725","km","2025-05-07 18:07:34","2025-05-07 18:45:09","","",""],
        ["DistanceWalkingRunning","B","5.806481","km","2025-05-07 18:07:34","2025-05-07 18:45:09","","",""],
    ]

    p = tmp_path / "input4.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        import csv as _csv
        w = _csv.writer(f)
        w.writerows(rows)

    out = extract_runs(str(p))
    assert len(out) == 1
    r = out.iloc[0]
    assert abs(r["distance_km"] - 5.806481) < 1e-6
