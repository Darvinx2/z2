"""Хранение и чтение структурированных данных в форматах JSON и XML."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import FileRecord, OperationType, User
from app.services import audit_service, file_service
from app.utils import fs, serialization
from app.utils.errors import AppError
from app.utils.paths import resolve_user_path, to_relative
from app.utils.serialization import Record

JSON = "json"
XML = "xml"


def _dump(records: list[Record], fmt: str) -> str:
    if fmt == JSON:
        return serialization.records_to_json(records)
    if fmt == XML:
        return serialization.records_to_xml(records)
    raise AppError(f"Неизвестный формат: {fmt}")


def _parse(payload: str, fmt: str) -> list[Record]:
    if fmt == JSON:
        return serialization.records_from_json(payload)
    if fmt == XML:
        return serialization.records_from_xml(payload)
    raise AppError(f"Неизвестный формат: {fmt}")


def save_records(
    session: Session,
    user: User,
    relative_path: str,
    records: list[Record],
    fmt: str,
) -> FileRecord:
    path = resolve_user_path(relative_path)
    if path.is_dir():
        raise AppError("По указанному пути находится каталог")

    existed = path.exists()
    fs.atomic_write_text(path, _dump(records, fmt))
    operation_type = OperationType.MODIFY if existed else OperationType.CREATE
    record = file_service.register_file(session, user, path, operation_type=operation_type)
    audit_service.log_action(
        f"data.save.{fmt}",
        user=user,
        details=f"{record.location} ({len(records)} записей)",
    )
    return record


def load_records(
    session: Session, user: User, relative_path: str, fmt: str
) -> list[Record]:
    path = resolve_user_path(relative_path, must_exist=True)
    if not path.is_file():
        raise AppError("Указанный путь не является файлом")

    records = _parse(fs.read_text(path), fmt)
    audit_service.log_action(
        f"data.load.{fmt}",
        user=user,
        details=f"{to_relative(path)} ({len(records)} записей)",
    )
    return records


def convert(
    session: Session,
    user: User,
    source_path: str,
    source_fmt: str,
    target_path: str,
    target_fmt: str,
) -> FileRecord:
    records = load_records(session, user, source_path, source_fmt)
    return save_records(session, user, target_path, records, target_fmt)
