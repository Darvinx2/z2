"""Журнал активности и история операций над файлами."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import session_scope
from app.models import AuditLog, FileRecord, Operation, OperationType, User


def log_action(
    action: str,
    *,
    user: User | None = None,
    details: str | None = None,
    success: bool = True,
) -> None:
    """Записывает действие в журнал активности отдельной транзакцией.

    Собственная сессия нужна, чтобы запись о неудачной операции сохранялась
    даже при откате основной транзакции.
    """
    with session_scope() as session:
        session.add(
            AuditLog(
                action=action,
                user_id=user.id if user else None,
                details=details,
                success=success,
            )
        )


def record_operation(
    session: Session,
    *,
    file: FileRecord,
    user: User,
    operation_type: OperationType,
) -> Operation:
    session.flush()  # нужен file.id для внешнего ключа
    operation = Operation(
        file_id=file.id,
        user_id=user.id,
        operation_type=operation_type,
    )
    session.add(operation)
    return operation


def list_audit(session: Session, user: User, limit: int = 20) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def list_operations(session: Session, user: User, limit: int = 20) -> list[Operation]:
    stmt = (
        select(Operation)
        .where(Operation.user_id == user.id)
        .order_by(Operation.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))
