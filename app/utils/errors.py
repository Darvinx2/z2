"""Ошибки уровня приложения, которые безопасно показывать пользователю."""

from __future__ import annotations


class AppError(Exception):
    """Базовая ожидаемая ошибка приложения."""


class AuthError(AppError):
    """Ошибка аутентификации или регистрации."""


class SecurityError(AppError):
    """Попытка выполнить небезопасную операцию."""
