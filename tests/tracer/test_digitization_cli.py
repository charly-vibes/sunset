"""Regression tests for the digitization CLI surface (digitization/__main__)."""
import contextlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from digitization.__main__ import main


def _run_output(capsys):
    captured = capsys.readouterr()
    return json.loads(captured.out)


def test_inspect_missing_run_directory_reports_invalid_input(tmp_path, capsys):
    missing = tmp_path / "nope"
    code = main(["inspect", "--run", str(missing), "--json"])
    result = _run_output(capsys)
    assert code == 3
    assert result["status"] == "invalid-input"
    assert result["detail"] == "run directory does not exist"


def test_replay_missing_run_directory_reports_invalid_input(tmp_path, capsys):
    missing = tmp_path / "nope"
    code = main(["replay", "--run", str(missing), "--output", str(tmp_path / "out")])
    result = _run_output(capsys)
    assert code == 3
    assert result["status"] == "invalid-input"
    assert result["detail"] == "run directory does not exist"


def test_native_pages_parse_error_message_matches_enforced_check(capsys):
    code = main(["native", "--source", "unused.pdf", "--output", "unused-out", "--pages", "1,z"])
    result = _run_output(capsys)
    assert code == 3
    assert result["detail"] == "pages must be unique one-based indices within the PDF"


def test_run_pages_parse_error_message_matches_enforced_check(capsys):
    code = main(["run", "--source", "unused.pdf", "--pages", "1,z",
                 "--config", "unused", "--output", "unused-out"])
    result = _run_output(capsys)
    assert code == 3
    assert result["detail"] == "pages must be unique one-based indices within the PDF"


def test_final_print_survives_closed_stdout_pipe(capsys):
    read_fd, write_fd = os.pipe()
    os.close(read_fd)  # consumer (e.g. `head`) already exited
    with contextlib.redirect_stdout(os.fdopen(write_fd, 'w')):
        code = main(["native", "--source", "unused.pdf", "--output", "unused-out",
                     "--pages", "1,z"])
    assert code == 3  # invalid-input exit is reported without a traceback
