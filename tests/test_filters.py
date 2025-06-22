import os
from app import file_exists_filter


def test_file_exists_filter(tmp_path):
    folder = tmp_path
    # Create a non-empty file
    existing = folder / "file.txt"
    existing.write_text("hello")
    assert file_exists_filter(existing.name, str(folder)) is True

    # Create an empty file
    empty = folder / "empty.txt"
    empty.touch()
    assert file_exists_filter(empty.name, str(folder)) is False

    # Non-existent file
    assert file_exists_filter("missing.txt", str(folder)) is False

