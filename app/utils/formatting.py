"""Утилиты форматирования вывода в консоль."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

_UNITS = ("Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ")


def human_size(size_bytes: float) -> str:
    value = float(size_bytes)
    for unit in _UNITS:
        if abs(value) < 1024.0 or unit == _UNITS[-1]:
            return f"{value:.1f} {unit}" if unit != "Б" else f"{int(value)} Б"
        value /= 1024.0
    return f"{value:.1f} {_UNITS[-1]}"


def format_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "-"


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return "(пусто)"
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def line(cells: Sequence[str]) -> str:
        return "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells)).rstrip()

    separator = "  ".join("-" * w for w in widths)
    return "\n".join([line(headers), separator, *(line(r) for r in rows)])
