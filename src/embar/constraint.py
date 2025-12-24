"""Table constraints like indexes and unique constraints."""

from collections.abc import Callable
from typing import Self, override

from embar.column.base import ColumnBase
from embar.constraint_base import Constraint
from embar.custom_types import PyType
from embar.query.clause_base import ClauseBase
from embar.query.query import QuerySingle


class Index:
    """
    Creates a database index on one or more columns.

    ```python
    from embar.column.common import Integer
    from embar.config import EmbarConfig
    from embar.constraint import Index
    from embar.table import Table
    class MyTable(Table):
        embar_config: EmbarConfig = EmbarConfig(
            constraints=[Index("my_idx").on(lambda: MyTable.id)]
        )
        id: Integer = Integer()
    ```
    """

    name: str

    def __init__(self, name: str):
        """
        Create a new Index instance.
        """
        self.name = name

    def on(self, *columns: Callable[[], ColumnBase]) -> IndexReady:
        """
        Specify the columns this index should be created on.
        """
        return IndexReady(self.name, False, *columns)


class UniqueIndex:
    """
    Creates a unique database index on one or more columns.
    """

    name: str

    def __init__(self, name: str):
        """
        Create a new UniqueIndex instance.
        """
        self.name = name

    def on(self, *columns: Callable[[], ColumnBase]) -> IndexReady:
        """
        Specify the columns this unique index should be created on.
        """
        return IndexReady(self.name, True, *columns)


class IndexReady(Constraint):
    """
    A fully configured index ready to generate SQL.
    """

    unique: bool
    name: str
    columns: tuple[Callable[[], ColumnBase], ...]
    _where_clause: Callable[[], ClauseBase] | None = None

    def __init__(self, name: str, unique: bool, *columns: Callable[[], ColumnBase]):
        """
        Create a new IndexReady instance.
        """
        self.name = name
        self.unique = unique
        self.columns = columns

    def where(self, where_clause: Callable[[], ClauseBase]) -> Self:
        """
        Add a WHERE clause to create a partial index.
        """
        self._where_clause = where_clause
        return self

    @override
    def sql(self) -> QuerySingle:
        """
        Generate the CREATE INDEX SQL statement.
        """
        # Not so sure about this, seems a bit brittle to just get the name as a string?
        table_names = [c().info.table_name for c in self.columns]
        if len(set(table_names)) > 1:
            raise ValueError(f"Index {self.name}: all columns must be in the same table")
        table_name = table_names[0]

        cols = ", ".join(f'"{c().info.name}"' for c in self.columns)
        unique = " UNIQUE " if self.unique else ""
        params: dict[str, PyType] = {}

        where_sql = ""
        if self._where_clause:
            count = -1

            def get_count() -> int:
                nonlocal count
                count += 1
                return count

            where = self._where_clause().sql(get_count)
            where_sql = f" WHERE {where.sql}"
            params = {**params, **where.params}

        query = f'CREATE {unique} INDEX "{self.name}" ON "{table_name}"({cols}){where_sql};'

        return QuerySingle(query, params)
