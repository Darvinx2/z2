"""Сериализация и десериализация данных в JSON и XML.

К внешним данным применяется принцип минимального доверия: ограничение
размера, строгая проверка структуры, парсер XML без поддержки внешних
сущностей (defusedxml) — защита от XXE и «billion laughs».
"""

from __future__ import annotations

import json
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import fromstring as safe_fromstring

from app.utils.errors import AppError

MAX_PAYLOAD_SIZE = 8 * 1024 * 1024
ROOT_TAG = "records"
RECORD_TAG = "record"
FIELD_TAG = "field"

Record = dict[str, str]


def _check_size(payload: str) -> None:
    if len(payload.encode("utf-8")) > MAX_PAYLOAD_SIZE:
        raise AppError("Данные слишком большие для разбора")


def _validate_records(data: Any) -> list[Record]:
    if not isinstance(data, list):
        raise AppError("Ожидается список записей")
    records: list[Record] = []
    for item in data:
        if not isinstance(item, dict):
            raise AppError("Каждая запись должна быть объектом «ключ-значение»")
        records.append({str(k): "" if v is None else str(v) for k, v in item.items()})
    return records


def records_to_json(records: list[Record]) -> str:
    return json.dumps(records, ensure_ascii=False, indent=2)


def records_from_json(payload: str) -> list[Record]:
    _check_size(payload)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AppError(f"Некорректный JSON: {exc.msg} (строка {exc.lineno})") from exc
    return _validate_records(data)


def records_to_xml(records: list[Record]) -> str:
    root = Element(ROOT_TAG)
    for record in records:
        node = SubElement(root, RECORD_TAG)
        for key, value in record.items():
            field = SubElement(node, FIELD_TAG, {"name": str(key)})
            field.text = str(value)
    return tostring(root, encoding="unicode")


def records_from_xml(payload: str) -> list[Record]:
    _check_size(payload)
    try:
        root = safe_fromstring(payload)
    except ParseError as exc:
        raise AppError(f"Некорректный XML: {exc}") from exc

    if root.tag != ROOT_TAG:
        raise AppError(f"Ожидается корневой элемент <{ROOT_TAG}>")

    records: list[Record] = []
    for node in root.findall(RECORD_TAG):
        record: Record = {}
        for field in node.findall(FIELD_TAG):
            name = field.get("name")
            if not name:
                raise AppError(f"У элемента <{FIELD_TAG}> отсутствует атрибут name")
            record[name] = field.text or ""
        records.append(record)
    return records
