from collections.abc import Sequence
from typing import Any

from embar.custom_types import PyType


class Query:
    sql: str
    params: dict[str, PyType]
    many_params: Sequence[dict[str, PyType]]

    def __init__(self, sql: str, params: dict[str, Any], many_params: Sequence[dict[str, Any]] | None = None):
        self.sql = sql
        self.params = params
        self.many_params = many_params if many_params is not None else []
