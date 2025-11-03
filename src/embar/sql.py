from string.templatelib import Template
from typing import Any, cast

from embar.column.base import ColumnBase
from embar.table_base import TableBase


class Sql:
    """
    Used to run raw SQL queries.

    On creation, nothing actually happens. Only later inside the [`Selection`][embar.query.selection.Selection]
    class is the `execute()` method called.

    ```python
    from embar.table import Table
    from embar.sql import Sql
    class MyTable(Table): ...
    sql = Sql(t"DELETE FROM {MyTable}").execute()
    assert sql == 'DELETE FROM "my_table"'
    ```
    """

    template_obj: Template

    def __init__(self, template: Template):
        self.template_obj = template

    def execute(self) -> str:
        """
        Actually generate the SQL output.
        """
        query_parts: list[str] = []

        # Iterate over template components
        for item in self.template_obj:
            if isinstance(item, str):
                query_parts.append(item)
            else:
                value = item.value

                if isinstance(value, type) and issubclass(value, TableBase):
                    query_parts.append(value.fqn())
                elif isinstance(value, ColumnBase):
                    query_parts.append(value.info.fqn())
                else:
                    raise Exception(f"Unexpected interpolation type: {type(cast(Any, value))}")

        result = "".join(query_parts)
        return result
