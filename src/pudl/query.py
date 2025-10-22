from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import (
    Any,
    Literal,
    Self,
    overload,
)

from dacite import from_dict
from psycopg import Connection

from pudl.table import ColumnInfo, SelectAll, Selection, Table


Undefined: Any = ...


@dataclass
class InsertQuery[T: Table]:
    _conn: Connection
    table: type[T]
    item: T = Undefined

    def values(self, item: T) -> Self:
        self.item = item
        return self

    def _build_sql(self) -> tuple[str, list[T]]:
        column_names = self.table.column_names()
        columns = ", ".join(column_names)
        placeholders = ", ".join(["%s"] * len(column_names))
        sql = f'INSERT INTO "{self.table._name}" ({columns}) VALUES ({placeholders})'  # pyright:ignore[reportPrivateUsage]
        return sql, self.item.values()

    def execute(self):
        sql, params = self._build_sql()
        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # pyright:ignore[reportArgumentType]
            self._conn.commit()


def execute(conn: Connection, sql: str, params: list[Any]) -> list[Any]:
    with conn.cursor() as cur:
        cur.execute(sql, params)  # pyright:ignore[reportArgumentType]

        if cur.description is None:
            return []
        columns = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))  # pyright:ignore[reportUnknownMemberType]
        return results  # pyright:ignore[reportUnknownVariableType]


@dataclass
class SelectQuery[S: Selection, T: Table]:
    _conn: Connection
    table: type[T]
    sel: type[S]

    _where_clauses: list[str] = field(default_factory=list)
    _where_params: list[Any] = field(default_factory=list)
    _limit_value: int | None = None

    def where(
        self, column: ColumnInfo, op: Literal["=", "LIKE", "ILIKE"], value: Any
    ) -> Self:
        self._where_clauses.append(f'"{column.table_name}"."{column.name}" {op} %s')
        self._where_params.append(value)
        return self

    def limit(self, n: int) -> Self:
        self._limit_value = n
        return self

    @overload
    def execute(self: SelectQuery[SelectAll, T]) -> list[T]: ...

    @overload
    def execute(self: SelectQuery[S, T]) -> list[S]: ...

    def execute(self) -> Sequence[Selection | T]:
        sql, params = self._build_sql()

        data_class = self._get_dataclass()

        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # pyright:ignore[reportArgumentType]

            if cur.description is None:
                return []
            columns: list[str] = [desc[0] for desc in cur.description]
            results: Sequence[Selection | T] = []
            for row in cur.fetchall():
                data = dict(zip(columns, row))
                results.append(from_dict(data_class, data))
            return results

    def _get_dataclass(self) -> type[Selection] | type[S]:
        data_class = (
            self.table.generate_selection_dataclass()
            if self.sel is SelectAll
            else self.sel
        )
        return data_class

    def _build_sql(self) -> tuple[str, list[Any]]:
        data_class = self._get_dataclass()
        selection = data_class.to_sql_columns()

        sql = f'SELECT {selection} FROM "{self.table._name}"'  # pyright:ignore[reportPrivateUsage]

        if self._where_clauses:
            sql += " WHERE " + " AND ".join(self._where_clauses)

        if self._limit_value:
            sql += f" LIMIT {self._limit_value}"

        return sql, self._where_params


@dataclass
class From[S: Selection]:
    _conn: Connection
    sel: type[S]

    def fromm[T: Table](self, table: type[T]) -> SelectQuery[S, T]:
        return SelectQuery[S, T](sel=self.sel, table=table, _conn=self._conn)
