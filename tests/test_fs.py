"""Проверка атомарной записи и чтения файлов."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.errors import AppError
from app.utils.fs import atomic_write_text, read_text


def test_atomic_write_creates_file_and_returns_size(workdir: Path):
    path = workdir / "sub" / "note.txt"
    size = atomic_write_text(path, "привет")
    assert path.read_text(encoding="utf-8") == "привет"
    assert size == path.stat().st_size


def test_atomic_write_leaves_no_temporary_files(workdir: Path):
    path = workdir / "note.txt"
    atomic_write_text(path, "первый")
    atomic_write_text(path, "второй")
    assert read_text(path) == "второй"
    assert [item.name for item in workdir.iterdir()] == ["note.txt"]


def test_read_rejects_too_large_file(workdir: Path):
    path = workdir / "big.txt"
    path.write_text("x" * 1000, encoding="utf-8")
    with pytest.raises(AppError):
        read_text(path, max_size=100)


def test_read_rejects_binary_file(workdir: Path):
    path = workdir / "binary.bin"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(AppError):
        read_text(path)
