"""This module contains example tests."""

from pathlib import Path

from voraus_template_updater.example import my_function


def test_my_function() -> None:
    assert my_function() == 42


def test_use_test_resource(resource_dir: Path) -> None:
    assert resource_dir.joinpath("example_resource.txt").is_file()
