"""Contains schema unit tests."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from pytest import CaptureFixture

from tests.resources.example_summary import summary

NOW = datetime(2023, 12, 15)


@patch("voraus_template_updater._schemas.datetime")
def test_summary_printing(datetime_mock: MagicMock, capsys: CaptureFixture, resource_dir: Path) -> None:
    datetime_mock.now.return_value = NOW
    datetime_mock.strftime = datetime.strftime
    summary.print()
    stdout = capsys.readouterr().out

    assert stdout == (resource_dir / "example_summary_output.txt").read_text(encoding="utf-8")
