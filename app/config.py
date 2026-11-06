"""Конфигурация приложения, читаемая из переменных окружения (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage_root: Path
    max_unpacked_size: int
    max_archive_entries: int


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Переменная окружения {name} должна быть целым числом") from exc


def load_settings() -> Settings:
    storage_root = Path(
        os.getenv("STORAGE_ROOT") or (PROJECT_ROOT / "storage")
    ).expanduser()
    if not storage_root.is_absolute():
        storage_root = (PROJECT_ROOT / storage_root).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)

    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://filemanager:filemanager@localhost:5433/filemanager",
        ),
        storage_root=storage_root,
        max_unpacked_size=_int_env("MAX_UNPACKED_SIZE", 100 * 1024 * 1024),
        max_archive_entries=_int_env("MAX_ARCHIVE_ENTRIES", 1000),
    )


settings = load_settings()
