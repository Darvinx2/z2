"""Низкоуровневые безопасные операции с файлами."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.utils.errors import AppError

# ограничение на чтение файла в память
MAX_READ_SIZE = 16 * 1024 * 1024


def read_text(path: Path, *, max_size: int = MAX_READ_SIZE) -> str:
    size = path.stat().st_size
    if size > max_size:
        raise AppError(f"Файл слишком большой для чтения в память ({size} байт)")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AppError("Файл не является текстовым в кодировке UTF-8") from exc


def atomic_write_text(path: Path, content: str) -> int:
    """Атомарная запись: сначала временный файл, затем замена.

    Исключает race condition, при котором параллельный читатель увидит
    частично записанный файл.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return path.stat().st_size
