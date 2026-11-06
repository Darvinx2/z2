"""Регистрация и аутентификация пользователей."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.services import audit_service
from app.utils.errors import AuthError
from app.utils.security import hash_password, verify_password

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50


def _validate_username(username: str) -> str:
    value = (username or "").strip()
    if not MIN_USERNAME_LENGTH <= len(value) <= MAX_USERNAME_LENGTH:
        raise AuthError(
            f"Логин должен быть длиной от {MIN_USERNAME_LENGTH} "
            f"до {MAX_USERNAME_LENGTH} символов"
        )
    if not all(ch.isalnum() or ch in "._-" for ch in value):
        raise AuthError("Логин может содержать только буквы, цифры и символы . _ -")
    return value


def register(session: Session, username: str, password: str) -> User:
    value = _validate_username(username)
    user = User(username=value, password_hash=hash_password(password))
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise AuthError("Пользователь с таким логином уже существует") from exc

    # фиксируем пользователя до записи в журнал: журнал ведётся отдельной транзакцией
    session.commit()
    audit_service.log_action("register", user=user, details=f"username={value}")
    return user


def authenticate(session: Session, username: str, password: str) -> User:
    # параметризованный запрос ORM — пользовательский ввод не попадает в текст SQL
    user = session.scalar(select(User).where(User.username == (username or "").strip()))
    if user is None or not verify_password(password, user.password_hash):
        audit_service.log_action(
            "login",
            user=user,
            details=f"username={username!r}",
            success=False,
        )
        # одинаковое сообщение в обоих случаях — не раскрываем существование логина
        raise AuthError("Неверный логин или пароль")

    audit_service.log_action("login", user=user)
    return user
