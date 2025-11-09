from __future__ import annotations

from pathlib import Path

from tools.fix import run


def snapshot_dir(path: Path) -> dict:
    snapshot: dict = {}
    for file in sorted(path.rglob("*")):
        if file.is_file():
            snapshot[file.relative_to(path)] = file.read_bytes()
    return snapshot


def test_pipeline_is_idempotent(sample_raw_dir, tmp_path):
    out_dir = tmp_path / "clean"
    run(str(sample_raw_dir), str(out_dir))
    first = snapshot_dir(out_dir)
    run(str(sample_raw_dir), str(out_dir))
    second = snapshot_dir(out_dir)
    assert first == second
