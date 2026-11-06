"""Безопасная работа с путями внутри каталога-песочницы.

Все пользовательские пути трактуются как относительные к STORAGE_ROOT;
выход за его пределы (path traversal, абсолютные пути, символические ссылки)
блокируется.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from app.config import settings
from app.utils.errors import SecurityError

STORAGE_ROOT = settings.storage_root


def resolve_user_path(user_path: str, *, must_exist: bool = False) -> Path:
    """Преобразует путь пользователя в абсолютный путь внутри песочницы."""
    raw = (user_path or "").strip()
    if not raw:
        raise SecurityError("Путь не может быть пустым")

    candidate = PurePosixPath(raw.replace("\\", "/"))
    if candidate.is_absolute():
        raise SecurityError("Абсолютные пути запрещены, укажите путь внутри хранилища")
    if any(part == ".." for part in candidate.parts):
        raise SecurityError("Переход в родительский каталог запрещён")

    resolved = (STORAGE_ROOT / candidate).resolve()
    root = STORAGE_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise SecurityError("Путь выходит за пределы каталога хранилища")

    if must_exist and not resolved.exists():
        raise SecurityError(f"Файл или каталог не найден: {candidate}")
    return resolved


def to_relative(path: Path) -> str:
    """Путь относительно песочницы — в таком виде он хранится в базе."""
    return path.resolve().relative_to(STORAGE_ROOT.resolve()).as_posix()
