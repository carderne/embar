from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, TypeAliasType

Undefined: Any = ...

type Type = type | TypeAliasType

# JSON not currently used because it confuses dacite (expects dict)
# type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None

# All the types that are allowed to ser/de to/from the DB.
# Used by dacite (other libraries in the future) to control ser/de.
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
    | list[PyType]
    | None
)
