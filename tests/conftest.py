"""Общая настройка тестов: изолированное хранилище во временном каталоге.

Переменные окружения выставляются до импорта модулей приложения, так как
настройки читаются один раз при импорте `app.config`.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

_TMP_STORAGE = tempfile.mkdtemp(prefix="filemanager-tests-")
os.environ["STORAGE_ROOT"] = _TMP_STORAGE

import pytest  # noqa: E402

from app.utils.paths import STORAGE_ROOT  # noqa: E402


@pytest.fixture
def workdir() -> Path:
    """Пустой подкаталог внутри хранилища, уникальный для каждого теста."""
    return Path(tempfile.mkdtemp(dir=STORAGE_ROOT))


@pytest.fixture
def rel(workdir: Path) -> Callable[[str], str]:
    """Путь внутри каталога теста в том виде, в каком его вводит пользователь."""

    def _rel(name: str) -> str:
        return f"{workdir.name}/{name}"

    return _rel
