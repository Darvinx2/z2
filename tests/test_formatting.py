"""Проверка форматирования вывода."""

from __future__ import annotations

import pytest

from app.utils.formatting import format_dt, human_size, render_table


@pytest.mark.parametrize(
    ("size", "expected"),
    [(0, "0 Б"), (512, "512 Б"), (2048, "2.0 КБ"), (5 * 1024**3, "5.0 ГБ")],
)
def test_human_size(size, expected):
    assert human_size(size) == expected


def test_format_dt_handles_none():
    assert format_dt(None) == "-"


def test_render_table():
    table = render_table(["ID", "Имя"], [["1", "файл.txt"]])
    assert "ID" in table and "файл.txt" in table
    assert render_table(["ID"], []) == "(пусто)"
