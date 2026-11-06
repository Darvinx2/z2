"""Модель пользователя."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.file import FileRecord
    from app.models.operation import Operation


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    files: Mapped[list[FileRecord]] = relationship(back_populates="owner")
    operations: Mapped[list[Operation]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
