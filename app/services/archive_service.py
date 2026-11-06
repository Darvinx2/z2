"""Работа с ZIP-архивами: создание, просмотр и безопасная распаковка."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import FileRecord, OperationType, User
from app.services import audit_service, file_service
from app.utils import archives
from app.utils.errors import AppError
from app.utils.paths import STORAGE_ROOT, resolve_user_path, to_relative


def create_archive(
    session: Session,
    user: User,
    archive_path: str,
    sources: list[str],
) -> FileRecord:
    if not sources:
        raise AppError("Не указано, что упаковывать")

    target = resolve_user_path(archive_path)
    if target.exists() and target.is_dir():
        raise AppError("По указанному пути находится каталог")
    existed = target.exists()

    resolved_sources = [resolve_user_path(src, must_exist=True) for src in sources]
    if target in resolved_sources:
        raise AppError("Архив не может упаковывать сам себя")

    size = archives.create_archive(target, resolved_sources, STORAGE_ROOT)
    operation_type = OperationType.MODIFY if existed else OperationType.CREATE
    record = file_service.register_file(session, user, target, operation_type=operation_type)
    audit_service.log_action(
        "archive.create",
        user=user,
        details=f"{record.location} ({len(resolved_sources)} источников, {size} байт)",
    )
    return record


def list_archive(
    session: Session, user: User, archive_path: str
) -> list[tuple[str, int, int]]:
    path = resolve_user_path(archive_path, must_exist=True)
    entries = archives.list_archive(path)
    audit_service.log_action(
        "archive.list", user=user, details=f"{to_relative(path)} ({len(entries)} записей)"
    )
    return entries


def extract_archive(
    session: Session, user: User, archive_path: str, destination: str
) -> list[str]:
    path = resolve_user_path(archive_path, must_exist=True)
    target_dir = resolve_user_path(destination)
    if target_dir.exists() and not target_dir.is_dir():
        raise AppError("Назначение должно быть каталогом")

    try:
        extracted = archives.extract_archive(path, target_dir)
    except Exception as exc:
        audit_service.log_action(
            "archive.extract",
            user=user,
            details=f"{to_relative(path)}: {exc}",
            success=False,
        )
        raise

    for name in extracted:
        file_path = target_dir / name
        if file_path.is_file():
            file_service.register_file(
                session, user, file_path, operation_type=OperationType.CREATE
            )

    audit_service.log_action(
        "archive.extract",
        user=user,
        details=f"{to_relative(path)} -> {to_relative(target_dir)} ({len(extracted)} записей)",
    )
    return extracted
