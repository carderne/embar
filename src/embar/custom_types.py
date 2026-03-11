"""Custom types used throughout embar."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, TypeAliasType

Undefined: Any = ...


class _NoDefaultType:
    """Sentinel to distinguish 'no default' from 'default is None'."""

    _instance: _NoDefaultType | None = None

    def __new__(cls) -> _NoDefaultType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NO_DEFAULT"

    def __bool__(self) -> bool:
        return False


NO_DEFAULT = _NoDefaultType()

type Type = type | TypeAliasType

# All the types that are allowed to ser/de to/from the DB.
# Note: pydantic.Json[Any] was intentionally removed from this union when pydantic
# became an optional dependency.  No column definition in the codebase annotates
# its Python type as pydantic.Json — the only Json usage is psycopg's Json adapter
# in db/pg.py, which is a separate type entirely.
type PyType = (
    str | int | float | Decimal | bool | bytes | date | time | datetime | timedelta | dict[str, Any] | list[Any] | None
)
