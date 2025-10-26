from __future__ import annotations

from dataclasses import dataclass, field, fields, make_dataclass
from collections.abc import Sequence
from typing import (
    Any,
    NoReturn,
    Self,
    TypeVar,
    cast,
    overload,
)

from dacite import from_dict
from psycopg import AsyncConnection, Connection

from pudl.column_base import ColumnBase
from pudl.group_by import GroupBy
from pudl.join import JoinClause, LeftJoin
from pudl.types import Undefined
from pudl.where import WhereClause
from pudl.selection import (
    SelectAll,
    Selection,
    convert_annotation,
    generate_selection_dataclass,
)
from pudl.table import Table


class Sync: ...


class Async: ...


Mode = TypeVar("Mode", Sync, Async)


@dataclass
class InsertQuery[T: Table, Mode]:
    _mode: type[Mode]
    _conn: Connection | AsyncConnection
    table: type[T]
    items: list[T] = Undefined

    def value(self, item: T) -> Self:
        self.items = [item]
        return self

    def values(self, items: Sequence[T]) -> Self:
        self.items = list(items)
        return self

    def _build_sql(self) -> tuple[str, list[list[T]]]:
        column_names = self.table.column_names()
        columns = ", ".join(column_names)
        placeholders = ", ".join(["%s"] * len(column_names))
        sql = f"INSERT INTO {self.table.fqn()} ({columns}) VALUES ({placeholders})"
        values = [it.values() for it in self.items]
        return sql, values

    @overload
    def execute(self: InsertQuery[T, Sync]) -> None: ...

    @overload
    def execute(self: InsertQuery[T, Async]) -> NoReturn: ...

    def execute(self):
        if not isinstance(self._conn, Connection):
            raise Exception("You need to use 'await ...aexecute()' here!")
        sql, params = self._build_sql()
        with self._conn.cursor() as cur:
            cur.executemany(sql, params)  # pyright:ignore[reportArgumentType]
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
            await cur.executemany(sql, params)  # pyright:ignore[reportArgumentType]
            await self._conn.commit()


@dataclass
class SelectQuery[S: Selection, T: Table, Mode]:
    _mode: type[Mode]
    _conn: Connection | AsyncConnection
    table: type[T]
    sel: type[S]

    _joins: list[JoinClause] = field(default_factory=list)
    _where_clause: WhereClause | None = None
    _group_clause: GroupBy | None = None
    _limit_value: int | None = None

    def left_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(LeftJoin(table, on))
        return self

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    def group_by(self, col: ColumnBase) -> Self:
        self._group_clause = GroupBy(col)
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
                parsed = from_dict(data_class, data)
                results.append(parsed)
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
            generate_selection_dataclass(self.table)
            if self.sel is SelectAll
            else self.sel
        )

        new_fields: list[tuple[str, type, Any]] = []
        for cls_field in fields(data_class):
            new_type = convert_annotation(cls_field)  # returns just the type
            if new_type:
                new_fields.append((cls_field.name, new_type, cls_field))
            else:
                field_type = cast(type, cls_field.type)
                new_fields.append((cls_field.name, field_type, cls_field))

        NewClass = make_dataclass(data_class.__name__, new_fields, bases=(Selection,))

        return NewClass

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

        if self._where_clause is not None:
            where_data = self._where_clause.get(get_count)
            sql += f" WHERE {where_data.sql} "
            params = {**params, **where_data.params}

        if self._group_clause is not None:
            group_by_col = self._group_clause.col.info.fqn
            sql += f" GROUP BY {group_by_col} "

        if self._limit_value is not None:
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
