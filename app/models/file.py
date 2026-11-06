"""Модель записи о файле, находящемся под управлением приложения."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.operation import Operation
    from app.models.user import User


class FileRecord(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("owner_id", "location", name="uq_files_owner_location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # путь относительно каталога-песочницы
    location: Mapped[str] = mapped_column(String(1024), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner: Mapped[User] = relationship(back_populates="files")
    operations: Mapped[list[Operation]] = relationship(back_populates="file")

    def __repr__(self) -> str:
        return f"<FileRecord id={self.id} location={self.location!r}>"
