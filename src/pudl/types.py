from datetime import datetime
from typing import Any, TypeAliasType


Undefined: Any = ...

type Type = type | TypeAliasType

# TODO
# JSON not currently used because it confuses dacite (expects dict)
# type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None

type PyType = str | int | float | bool | datetime | dict[str, Any]
