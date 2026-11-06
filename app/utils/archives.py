"""Создание и распаковка ZIP-архивов с защитой от «zip-бомб» и traversal."""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.config import settings
from app.utils.errors import AppError, SecurityError

# максимальный коэффициент сжатия одной записи
MAX_COMPRESSION_RATIO = 100
COPY_CHUNK = 64 * 1024


def create_archive(archive_path: Path, sources: list[Path], base_dir: Path) -> int:
    """Упаковывает файлы и каталоги в ZIP. Возвращает размер архива."""
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            if source.is_dir():
                for item in sorted(source.rglob("*")):
                    if item.is_file() and not item.is_symlink():
                        archive.write(item, item.relative_to(base_dir).as_posix())
            elif source.is_file() and not source.is_symlink():
                archive.write(source, source.relative_to(base_dir).as_posix())
            else:
                raise AppError(f"Нельзя упаковать объект: {source.name}")
    return archive_path.stat().st_size


def list_archive(archive_path: Path) -> list[tuple[str, int, int]]:
    """Содержимое архива: имя, размер в упакованном и распакованном виде."""
    with zipfile.ZipFile(archive_path) as archive:
        return [(i.filename, i.compress_size, i.file_size) for i in archive.infolist()]


def _safe_target(entry_name: str, destination: Path) -> Path:
    """Проверяет имя записи архива и возвращает путь назначения."""
    name = entry_name.replace("\\", "/")
    if name.startswith("/") or ".." in Path(name).parts or (len(name) > 1 and name[1] == ":"):
        raise SecurityError(f"Небезопасное имя записи в архиве: {entry_name}")
    target = (destination / name).resolve()
    if destination.resolve() not in target.parents:
        raise SecurityError(f"Запись архива выходит за пределы каталога: {entry_name}")
    return target


def extract_archive(archive_path: Path, destination: Path) -> list[str]:
    """Распаковывает архив с ограничениями на число записей и объём данных."""
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    total_written = 0

    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > settings.max_archive_entries:
            raise SecurityError(
                f"В архиве слишком много записей: {len(infos)} "
                f"(лимит {settings.max_archive_entries})"
            )
        declared = sum(i.file_size for i in infos)
        if declared > settings.max_unpacked_size:
            raise SecurityError(
                f"Заявленный размер распакованных данных {declared} байт "
                f"превышает лимит {settings.max_unpacked_size}"
            )

        for info in infos:
            target = _safe_target(info.filename, destination)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise SecurityError(
                    f"Подозрительная степень сжатия записи {info.filename} — "
                    "возможна zip-бомба"
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(info) as source, open(target, "wb") as sink:
                # размер контролируется по фактически записанным байтам:
                # заголовкам архива доверять нельзя
                while chunk := source.read(COPY_CHUNK):
                    written += len(chunk)
                    total_written += len(chunk)
                    if total_written > settings.max_unpacked_size:
                        sink.close()
                        target.unlink(missing_ok=True)
                        raise SecurityError(
                            "Превышен лимит распакованных данных "
                            f"({settings.max_unpacked_size} байт)"
                        )
                    sink.write(chunk)
            extracted.append(info.filename)

    return extracted
