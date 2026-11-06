"""Проверка сериализации JSON/XML и защиты от небезопасных данных."""

from __future__ import annotations

import pytest

from app.utils.errors import AppError
from app.utils.serialization import (
    records_from_json,
    records_from_xml,
    records_to_json,
    records_to_xml,
)

RECORDS = [{"name": "Bill Gates", "company": "Microsoft"}, {"name": "Larry Page"}]


def test_json_roundtrip():
    assert records_from_json(records_to_json(RECORDS)) == RECORDS


def test_xml_roundtrip():
    assert records_from_xml(records_to_xml(RECORDS)) == RECORDS


def test_json_to_xml_conversion_keeps_data():
    assert records_from_xml(records_to_xml(records_from_json(records_to_json(RECORDS)))) == RECORDS


@pytest.mark.parametrize("payload", ["{", "{}", '"строка"', "[1, 2, 3]"])
def test_invalid_json_is_rejected(payload):
    with pytest.raises(AppError):
        records_from_json(payload)


@pytest.mark.parametrize(
    "payload",
    ["<notrecords/>", "<records><record><field>нет имени</field></record></records>", "<records>"],
)
def test_invalid_xml_is_rejected(payload):
    with pytest.raises(AppError):
        records_from_xml(payload)


def test_xxe_entity_is_not_resolved():
    payload = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE records [<!ENTITY secret SYSTEM "file:///etc/passwd">]>'
        '<records><record><field name="a">&secret;</field></record></records>'
    )
    with pytest.raises(Exception) as exc_info:
        records_from_xml(payload)
    assert "Entities" in type(exc_info.value).__name__
