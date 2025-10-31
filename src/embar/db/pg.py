import types
from collections.abc import Sequence
from typing import (
    Any,
    Self,
    final,
    override,
)

from psycopg import AsyncConnection, Connection
from psycopg.types.json import Json

from embar._util import topological_sort_tables
from embar.column.pg import EmbarEnum, PgEnum
from embar.db.base import AsyncDbBase, DbBase
from embar.query.fromm import Fromm
from embar.query.insert import InsertQuery
from embar.query.selection import Selection
from embar.query.update import UpdateQuery
from embar.table import Table


@final
class Db(DbBase):
    db_type = "postgres"
    _conn: Connection

    def __init__(self, connection: Connection):
        self._conn = connection

    def close(self):
        if self._conn:
            self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> Fromm[S, DbBase]:
        return Fromm[S, DbBase](_db=self, sel=sel)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, DbBase]:
        return InsertQuery[T, DbBase](table=table, _db=self)

    def update[T: Table](self, table: type[T]) -> UpdateQuery[T, DbBase]:
        return UpdateQuery[T, DbBase](table=table, db=self)

    def migrate(self, tables: Sequence[type[Table]], enums: Sequence[type[PgEnum[Any]]] | None = None) -> Self:
        if enums is not None:
            for enum in enums:
                ddl = enum.ddl()
                self._conn.execute(ddl)  # pyright:ignore[reportArgumentType]

        tables = topological_sort_tables(tables)
        for table in tables:
            self._conn.execute(table.ddl())  # pyright:ignore[reportArgumentType]
        self._conn.commit()
        return self

    def migrates(self, schema: types.ModuleType) -> Self:
        enums: list[type[PgEnum[EmbarEnum]]] = []
        tables: list[type[Table]] = []
        for name in dir(schema):
            obj = getattr(schema, name)
            # Check if it's a class and inherits from Table
            if isinstance(obj, type) and issubclass(obj, Table) and obj is not Table:
                tables.append(obj)
            if isinstance(obj, type) and issubclass(obj, PgEnum) and obj is not PgEnum:
                enums.append(obj)  # pyright:ignore[reportUnknownArgumentType]
        self.migrate(tables, enums)
        return self

    @override
    def execute(self, query: str, params: dict[str, Any]) -> None:
        self._conn.execute(query, params)  # pyright:ignore[reportArgumentType]

    @override
    def executemany(self, query: str, params: Sequence[dict[str, Any]]):
        params = _jsonify_dicts(params)
        with self._conn.cursor() as cur:
            cur.executemany(query, params)  # pyright:ignore[reportArgumentType]
            self._conn.commit()

    @override
    def fetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        # TODO should this return a Generator instead?
        with self._conn.cursor() as cur:
            cur.execute(query, params)  # pyright:ignore[reportArgumentType]

            if cur.description is None:
                return []
            columns: list[str] = [desc[0] for desc in cur.description]
            results: list[dict[str, Any]] = []
            for row in cur.fetchall():
                data = dict(zip(columns, row))
                results.append(data)
            return results


@final
class AsyncDb(AsyncDbBase):
    db_type = "postgres"
    _conn: AsyncConnection

    def __init__(self, connection: AsyncConnection):
        self._conn = connection

    async def close(self):
        if self._conn:
            await self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> Fromm[S, Self]:
        return Fromm[S, Self](_db=self, sel=sel)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, Self]:
        return InsertQuery[T, Self](table=table, _db=self)

    async def migrate(
        self, tables: Sequence[type[Table]], enums: Sequence[type[PgEnum[EmbarEnum]]] | None = None
    ) -> Self:
        if enums is not None:
            for enum in enums:
                ddl = enum.ddl()
                await self._conn.execute(ddl)  # pyright:ignore[reportArgumentType]

        tables = topological_sort_tables(tables)
        for table in tables:
            ddl = table.ddl()
            await self._conn.execute(ddl)  # pyright:ignore[reportArgumentType]
        await self._conn.commit()
        return self

    async def migrates(self, schema: types.ModuleType) -> Self:
        enums: list[type[PgEnum[EmbarEnum]]] = []
        tables: list[type[Table]] = []
        for name in dir(schema):
            obj = getattr(schema, name)
            # Check if it's a class and inherits from Table
            if isinstance(obj, type) and issubclass(obj, Table) and obj is not Table:
                tables.append(obj)
            if isinstance(obj, type) and issubclass(obj, PgEnum) and obj is not PgEnum:
                enums.append(obj)  # pyright:ignore[reportUnknownArgumentType]
        await self.migrate(tables)
        return self

    @override
    async def aexecute(self, query: str, params: dict[str, Any]) -> None:
        await self._conn.execute(query, params)  # pyright:ignore[reportArgumentType]

    @override
    async def aexecutemany(self, query: str, params: Sequence[dict[str, Any]]):
        params = _jsonify_dicts(params)
        async with self._conn.cursor() as cur:
            await cur.executemany(query, params)  # pyright:ignore[reportArgumentType]
            await self._conn.commit()

    @override
    async def afetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        async with self._conn.cursor() as cur:
            await cur.execute(query, params)  # pyright:ignore[reportArgumentType]

            if cur.description is None:
                return []
            columns: list[str] = [desc[0] for desc in cur.description]
            results: list[dict[str, Any]] = []
            for row in await cur.fetchall():
                data = dict(zip(columns, row))
                results.append(data)
            return results


def _jsonify_dicts(params: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    psycopg requires that dicts get passed through its `Json` function.
    """
    return [{k: Json(v) if isinstance(v, dict) else v for k, v in p.items()} for p in params]
