"""Проверка упаковки и безопасной распаковки ZIP-архивов."""

from __future__ import annotations

import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from app.config import settings
from app.utils import archives
from app.utils.archives import create_archive, extract_archive, list_archive
from app.utils.errors import SecurityError
from app.utils.paths import STORAGE_ROOT


@pytest.fixture
def limits(monkeypatch):
    """Небольшие лимиты распаковки, не зависящие от настроек окружения."""

    def _limits(*, max_unpacked_size: int = 1024 * 1024, max_entries: int = 50):
        monkeypatch.setattr(
            archives,
            "settings",
            replace(
                settings,
                max_unpacked_size=max_unpacked_size,
                max_archive_entries=max_entries,
            ),
        )

    return _limits


def _make_file(directory: Path, name: str, content: str = "данные") -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_create_and_extract_archive(workdir: Path):
    _make_file(workdir, "docs/a.txt", "первый")
    _make_file(workdir, "b.txt", "второй")
    archive = workdir / "arc.zip"

    size = create_archive(archive, [workdir / "docs", workdir / "b.txt"], STORAGE_ROOT)
    assert size > 0
    assert {name for name, _, _ in list_archive(archive)} == {
        f"{workdir.name}/docs/a.txt",
        f"{workdir.name}/b.txt",
    }

    destination = workdir / "out"
    extracted = extract_archive(archive, destination)
    assert len(extracted) == 2
    assert (destination / workdir.name / "docs" / "a.txt").read_text(encoding="utf-8") == "первый"


def test_zip_slip_is_blocked(workdir: Path):
    archive = workdir / "evil.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../../evil.txt", "pwned")

    with pytest.raises(SecurityError):
        extract_archive(archive, workdir / "out")
    assert not (STORAGE_ROOT.parent / "evil.txt").exists()


def test_zip_bomb_compression_ratio_is_blocked(workdir: Path, limits):
    limits()
    archive = workdir / "bomb.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("big.txt", b"0" * 500_000)

    with pytest.raises(SecurityError, match="сжатия"):
        extract_archive(archive, workdir / "out")


def test_total_unpacked_size_limit(workdir: Path, limits):
    limits(max_unpacked_size=1_000_000)
    archive = workdir / "big.zip"
    chunk = b"".join(bytes([i % 251]) for i in range(100_000))  # плохо сжимаемые данные
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as handle:
        for index in range(20):
            handle.writestr(f"part{index}.bin", chunk)

    with pytest.raises(SecurityError, match="лимит"):
        extract_archive(archive, workdir / "out")


def test_too_many_entries_is_blocked(workdir: Path, limits):
    limits(max_entries=10)
    archive = workdir / "many.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for index in range(11):
            handle.writestr(f"f{index}.txt", "x")

    with pytest.raises(SecurityError, match="записей"):
        extract_archive(archive, workdir / "out")
