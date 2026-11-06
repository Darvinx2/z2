"""Хеширование и проверка паролей."""

from __future__ import annotations

import bcrypt

from app.utils.errors import AuthError

MIN_PASSWORD_LENGTH = 8
# bcrypt учитывает только первые 72 байта пароля
MAX_PASSWORD_BYTES = 72


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise AuthError("Пароль слишком длинный (максимум 72 байта)")


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
