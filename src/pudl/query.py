from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import (
    Any,
    NoReturn,
    Self,
    TypeVar,
    overload,
)

from dacite import from_dict
from psycopg import AsyncConnection, Connection

from pudl.join import JoinClause, LeftJoin
from pudl.where import WhereClause
from pudl.table import SelectAll, Selection, Table


Undefined: Any = ...


class Sync: ...


class Async: ...


Mode = TypeVar("Mode", Sync, Async)


@dataclass
class InsertQuery[T: Table, Mode]:
    _mode: type[Mode]
    _conn: Connection | AsyncConnection
    table: type[T]
    item: T = Undefined

    def values(self, item: T) -> Self:
        self.item = item
        return self

    def _build_sql(self) -> tuple[str, list[T]]:
        column_names = self.table.column_names()
        columns = ", ".join(column_names)
        placeholders = ", ".join(["%s"] * len(column_names))
        sql = f"INSERT INTO {self.table.fqn()} ({columns}) VALUES ({placeholders})"
        return sql, self.item.values()

    @overload
    def execute(self: InsertQuery[T, Sync]) -> None: ...

    @overload
    def execute(self: InsertQuery[T, Async]) -> NoReturn: ...

    def execute(self):
        if not isinstance(self._conn, Connection):
            raise Exception("You need to use 'await ...aexecute()' here!")
        sql, params = self._build_sql()
        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # pyright:ignore[reportArgumentType]
            self._conn.commit()

    @overload
    async def aexecute(self: InsertQuery[T, Sync]) -> NoReturn: ...

    @overload
    async def aexecute(self: InsertQuery[T, Async]) -> None: ...

    async def aexecute(self):
        if not isinstance(self._conn, AsyncConnection):
            raise Exception("You need to use '...execute()' here (not 'aexecute()')")
        sql, params = self._build_sql()
        async with self._conn.cursor() as cur:
            await cur.execute(sql, params)  # pyright:ignore[reportArgumentType]
            await self._conn.commit()


@dataclass
class SelectQuery[S: Selection, T: Table, Mode]:
    _mode: type[Mode]
    _conn: Connection | AsyncConnection
    table: type[T]
    sel: type[S]

    _joins: list[JoinClause] = field(default_factory=list)
    _where_clause: WhereClause | None = None
    _limit_value: int | None = None

    def left_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(LeftJoin(table, on))
        return self

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    def limit(self, n: int) -> Self:
        self._limit_value = n
        return self

    @overload
    def execute(self: SelectQuery[SelectAll, T, Sync]) -> list[T]: ...

    @overload
    def execute(self: SelectQuery[S, T, Sync]) -> list[S]: ...

    @overload
    def execute(self: SelectQuery[SelectAll, T, Async]) -> NoReturn: ...

    @overload
    def execute(self: SelectQuery[S, T, Async]) -> NoReturn: ...

    def execute(self) -> Sequence[Selection | T]:
        if not isinstance(self._conn, Connection):
            raise Exception("You need to use 'await ...aexecute()' here!")

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

    @overload
    async def aexecute(self: SelectQuery[SelectAll, T, Sync]) -> NoReturn: ...

    @overload
    async def aexecute(self: SelectQuery[S, T, Sync]) -> NoReturn: ...

    @overload
    async def aexecute(self: SelectQuery[SelectAll, T, Async]) -> list[T]: ...

    @overload
    async def aexecute(self: SelectQuery[S, T, Async]) -> list[S]: ...

    async def aexecute(self) -> Sequence[Selection | T]:
        if not isinstance(self._conn, AsyncConnection):
            raise Exception("You need to use '...execute()' here (not 'aexecute()')")

        sql, params = self._build_sql()
        data_class = self._get_dataclass()

        async with self._conn.cursor() as acur:
            await acur.execute(sql, params)  # pyright:ignore[reportArgumentType]

            if acur.description is None:
                return []
            columns: list[str] = [desc[0] for desc in acur.description]
            results: Sequence[Selection | T] = []
            for row in await acur.fetchall():
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

    def _build_sql(self) -> tuple[str, dict[str, Any]]:
        data_class = self._get_dataclass()
        selection = data_class.to_sql_columns()

        sql = f"SELECT {selection} FROM {self.table.fqn()}"

        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        for join in self._joins:
            join_data = join.get(get_count)
            sql += join_data.sql
            params = {**params, **join_data.params}

        if self._where_clause:
            where_data = self._where_clause.get(get_count)
            sql += f" WHERE {where_data.sql} "
            params = {**params, **where_data.params}

        if self._limit_value:
            sql += f" LIMIT {self._limit_value}"

        return sql, params


@dataclass
class From[S: Selection, Mode]:
    _mode: type[Mode]
    _conn: Connection | AsyncConnection
    sel: type[S]

    def fromm[T: Table](self, table: type[T]) -> SelectQuery[S, T, Mode]:
        return SelectQuery[S, T, Mode](
            sel=self.sel, table=table, _conn=self._conn, _mode=self._mode
        )
