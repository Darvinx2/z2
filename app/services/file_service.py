"""CRUD-операции с файлами внутри каталога-песочницы и их учёт в БД."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FileRecord, OperationType, User
from app.services import audit_service
from app.utils import fs
from app.utils.errors import AppError
from app.utils.paths import STORAGE_ROOT, resolve_user_path, to_relative


@dataclass(frozen=True)
class DirEntry:
    name: str
    is_dir: bool
    size: int
    modified: datetime


def list_directory(relative_path: str = ".") -> tuple[str, list[DirEntry]]:
    target = STORAGE_ROOT if relative_path in ("", ".") else resolve_user_path(
        relative_path, must_exist=True
    )
    if not target.is_dir():
        raise AppError("Указанный путь не является каталогом")

    entries: list[DirEntry] = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        stat = item.stat()
        entries.append(
            DirEntry(
                name=item.name,
                is_dir=item.is_dir(),
                size=0 if item.is_dir() else stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return (to_relative(target) if target != STORAGE_ROOT else "."), entries


def get_record(session: Session, user: User, location: str) -> FileRecord | None:
    stmt = select(FileRecord).where(
        FileRecord.owner_id == user.id, FileRecord.location == location
    )
    return session.scalar(stmt)


def register_file(
    session: Session,
    user: User,
    path: Path,
    *,
    operation_type: OperationType,
) -> FileRecord:
    """Создаёт или обновляет запись о файле и фиксирует операцию."""
    location = to_relative(path)
    record = get_record(session, user, location)
    if record is None:
        record = FileRecord(
            filename=path.name,
            location=location,
            size=path.stat().st_size,
            owner_id=user.id,
        )
        session.add(record)
    else:
        record.size = path.stat().st_size
        record.deleted_at = None
    audit_service.record_operation(
        session, file=record, user=user, operation_type=operation_type
    )
    return record


def read_file(session: Session, user: User, relative_path: str) -> str:
    path = resolve_user_path(relative_path, must_exist=True)
    if not path.is_file():
        raise AppError("Указанный путь не является файлом")
    content = fs.read_text(path)
    audit_service.log_action("file.read", user=user, details=to_relative(path))
    return content


def write_file(
    session: Session,
    user: User,
    relative_path: str,
    content: str,
    *,
    append: bool = False,
) -> FileRecord:
    path = resolve_user_path(relative_path)
    if path.is_dir():
        raise AppError("По указанному пути находится каталог")

    existed = path.exists()
    if append and existed:
        content = fs.read_text(path) + content

    fs.atomic_write_text(path, content)
    operation_type = OperationType.MODIFY if existed else OperationType.CREATE
    record = register_file(session, user, path, operation_type=operation_type)
    audit_service.log_action(
        "file.write",
        user=user,
        details=f"{record.location} ({operation_type}, {record.size} байт)",
    )
    return record


def delete_file(session: Session, user: User, relative_path: str) -> str:
    path = resolve_user_path(relative_path, must_exist=True)
    if not path.is_file():
        raise AppError("Удалять можно только файлы")

    location = to_relative(path)
    record = get_record(session, user, location)
    if record is not None:
        record.deleted_at = datetime.now(UTC)
        audit_service.record_operation(
            session, file=record, user=user, operation_type=OperationType.DELETE
        )
    path.unlink()
    audit_service.log_action("file.delete", user=user, details=location)
    return location


def list_user_files(session: Session, user: User) -> list[FileRecord]:
    stmt = (
        select(FileRecord)
        .where(FileRecord.owner_id == user.id)
        .order_by(FileRecord.location)
    )
    return list(session.scalars(stmt))
