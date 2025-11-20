from string.templatelib import Template
from typing import Any, cast

from embar.column.base import ColumnBase
from embar.table_base import TableBase


class Sql:
    """
    Used to run raw SQL queries.

    On creation, nothing actually happens. Only later inside the select query
    class is the `execute()` method called.

    ```python
    from embar.table import Table
    from embar.sql import Sql
    class MyTable(Table): ...
    sql = Sql(t"DELETE FROM {MyTable}").sql()
    assert sql == 'DELETE FROM "my_table"'
    ```
    """

    template_obj: Template

    def __init__(self, template: Template):
        self.template_obj = template

    def sql(self) -> str:
        """
        Actually generate the SQL output.
        """
        query_parts: list[str] = []

        # Some types of queries we _don't_ want the table name prefixed to the column name
        # UPDATE "user" SET "name" = 'foo'
        # Using "user"."name" is an error
        # TODO: This is a very terrible heuristic and will probably break
        strings = self.template_obj.strings
        first_word = strings[0].strip() if len(strings) > 0 else None
        omit_table_name = first_word is not None and first_word in ["CREATE", "UPDATE"]

        # Iterate over template components
        for item in self.template_obj:
            if isinstance(item, str):
                query_parts.append(item)
            else:
                value = item.value

                if isinstance(value, type) and issubclass(value, TableBase):
                    query_parts.append(value.fqn())
                elif isinstance(value, ColumnBase):
                    quoted = f'"{value.info.name}"' if omit_table_name else value.info.fqn()
                    query_parts.append(quoted)
                else:
                    raise Exception(f"Unexpected interpolation type: {type(cast(Any, value))}")

        result = "".join(query_parts)
        escaped = escape_placeholder(result)
        return escaped


def escape_placeholder(s: str) -> str:
    placeholder = "\x00"
    s = s.replace("%%", placeholder)
    s = s.replace("%", "%%")
    s = s.replace(placeholder, "%%")
    return s
