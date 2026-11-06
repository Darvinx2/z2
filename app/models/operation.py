"""Модель операции над файлом (создание, изменение, удаление)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.file import FileRecord
    from app.models.user import User


class OperationType(enum.StrEnum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    operation_type: Mapped[OperationType] = mapped_column(
        Enum(OperationType, name="operation_type"), nullable=False
    )

    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    file: Mapped[FileRecord] = relationship(back_populates="operations")
    user: Mapped[User] = relationship(back_populates="operations")

    def __repr__(self) -> str:
        return f"<Operation id={self.id} type={self.operation_type}>"
