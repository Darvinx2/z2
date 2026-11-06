"""Переиспользуемые помощники для ввода данных в консоли."""

from __future__ import annotations

import getpass


class ExitRequested(Exception):
    """Пользователь прервал ввод (Ctrl+D/Ctrl+C)."""


def ask(prompt: str, *, default: str | None = None, allow_empty: bool = False) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        try:
            value = input(f"{prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise ExitRequested from None
        if not value and default is not None:
            return default
        if value or allow_empty:
            return value
        print("Значение не может быть пустым.")


def ask_password(prompt: str = "Пароль") -> str:
    try:
        return getpass.getpass(f"{prompt}: ")
    except (EOFError, KeyboardInterrupt):
        raise ExitRequested from None


def ask_multiline(prompt: str) -> str:
    """Читает многострочный текст до строки с одной точкой."""
    print(f"{prompt} (завершите ввод строкой с одной точкой «.»)")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            raise ExitRequested from None
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def confirm(prompt: str) -> bool:
    return ask(f"{prompt} (y/n)", default="n").lower() in ("y", "yes", "д", "да")
