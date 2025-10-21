from dataclasses import dataclass, field
from typing import (
    Any,
    Self,
)
from psycopg import Connection

from pudl.table import ColumnInfo, Table


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
        sql = f"INSERT INTO {self.table._name} ({columns}) VALUES ({placeholders})"  # pyright:ignore[reportPrivateUsage]
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
class SelectQuery[T: Table]:
    _conn: Connection
    table: type[T]
    _where_clauses: list[str] = field(default_factory=list)
    _where_params: list[Any] = field(default_factory=list)
    _limit_value: int | None = None

    def where(self, column: ColumnInfo, op: str, value: Any) -> Self:
        self._where_clauses.append(f"{column.name} {op} %s")
        self._where_params.append(value)
        return self

    def limit(self, n: int) -> Self:
        self._limit_value = n
        return self

    def execute(self) -> list[T]:
        sql, params = self._build_sql()
        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # pyright:ignore[reportArgumentType]

            if cur.description is None:
                return []
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))  # pyright:ignore[reportUnknownMemberType]
            return results  # pyright:ignore[reportUnknownVariableType]

    def _build_sql(self) -> tuple[str, list[Any]]:
        sql = f"SELECT * FROM {self.table._name}"  # pyright:ignore[reportPrivateUsage]

        if self._where_clauses:
            sql += " WHERE " + " AND ".join(self._where_clauses)

        if self._limit_value:
            sql += f" LIMIT {self._limit_value}"

        return sql, self._where_params
