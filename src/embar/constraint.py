from collections.abc import Callable
from typing import Self, override

from embar.column.base import ColumnBase, ColumnInfo
from embar.constraint_base import Constraint
from embar.custom_types import PyType
from embar.query.query import Query
from embar.query.where import WhereClause


class Index:
    name: str

    def __init__(self, name: str, *columns: ColumnInfo):
        self.name = name

    def on(self, *columns: Callable[[], ColumnBase]) -> IndexReady:
        return IndexReady(self.name, False, *columns)


class UniqueIndex:
    name: str

    def __init__(self, name: str, *columns: ColumnInfo):
        self.name = name

    def on(self, *columns: Callable[[], ColumnBase]) -> IndexReady:
        return IndexReady(self.name, True, *columns)


class IndexReady(Constraint):
    unique: bool
    name: str
    columns: tuple[Callable[[], ColumnBase], ...]
    _where_clause: WhereClause | None = None

    def __init__(self, name: str, unique: bool, *columns: Callable[[], ColumnBase]):
        self.name = name
        self.unique = unique
        self.columns = columns

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    @override
    def sql(self) -> Query:
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

            where = self._where_clause.sql(get_count)
            where_sql = f" WHERE {where.sql}"
            params = {**params, **where.params}

        query = f'CREATE {unique} INDEX "{self.name}" ON "{table_name}"({cols}){where_sql};'

        return Query(query, params)
