"""Custom types used throughout embar."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, TypeAliasType

from pydantic import Json

Undefined: Any = ...

type Type = type | TypeAliasType

# All the types that are allowed to ser/de to/from the DB.
type PyType = (
    str
    | int
    | float
    | Decimal
    | bool
    | bytes
    | date
    | time
    | datetime
    | timedelta
    | dict[str, Any]
    | Json[Any]
    | list[PyType]
    | None
)
