from datetime import datetime
from typing import Any

from pudl.column.common import Column, Text, Integer, Float
from pudl.types import Type

__all__ = ["Boolean", "Float", "Integer", "Serial", "Text", "Timestamp"]


class Serial(Column[int]):
    _sql_type: str = "SERIAL"
    _pytype: Type = int


class Boolean(Column[bool]):
    _sql_type: str = "BOOLEAN"
    _pytype: Type = bool


class Timestamp(Column[datetime]):
    _sql_type: str = "TIMESTAMP"
    _pytype: Type = str


class Jsonb(Column[dict[str, Any]]):
    _sql_type: str = "JSONB"
    _pytype: Type = dict[str, Any]
