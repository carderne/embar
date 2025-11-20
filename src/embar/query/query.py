"""Query class for SQL queries with parameterized values."""

import re
from collections.abc import Sequence
from typing import Any

from embar.custom_types import PyType


class QuerySingle:
    """
    Represents an SQL query with parameterized values.
    """

    sql: str
    params: dict[str, PyType]

    def __init__(self, sql: str, params: dict[str, Any] | None = None):
        """
        Create a new QuerySingle instance.
        """
        self.sql = sql
        self.params = params if params is not None else {}

    def merged(self) -> str:
        """
        Combine query and params into a single string.

        This is used in Constraints where we don't want params as it's desirable to be
        able to print the DDL to a text file.

        ```python
        from embar.query.query import QuerySingle
        query = QuerySingle(
            sql="SELECT * FROM a WHERE id = %(my_var_name)s",
            params={"my_var_name": 100},
        )
        assert query.merged() == "SELECT * FROM a WHERE id = 100"
        ```
        """

        def replace_param(match: re.Match[str]) -> str:
            param_name = match.group(1)
            value = self.params[param_name]

            if isinstance(value, str):
                return f"'{value}'"
            elif value is None:
                return "NULL"
            else:
                return str(value)

        return re.sub(r"%\((\w+)\)s", replace_param, self.sql)


class QueryMany:
    """
    Represents an SQL query with a sequence parameterized values.
    """

    sql: str
    many_params: Sequence[dict[str, PyType]]

    def __init__(self, sql: str, many_params: Sequence[dict[str, Any]] | None = None):
        """
        Create a new QueryMany instance.
        """
        self.sql = sql
        self.many_params = many_params if many_params is not None else []
