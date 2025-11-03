import types
from collections.abc import Sequence
from string.templatelib import Template
from typing import (
    Any,
    Self,
    final,
    override,
)

from psycopg import AsyncConnection, Connection
from psycopg.types.json import Json

from embar.column.base import EnumBase
from embar.db._util import get_migration_defs, merge_ddls
from embar.db.base import AsyncDbBase, DbBase
from embar.migration import Migration, MigrationDefs
from embar.query.insert import InsertQuery
from embar.query.query import Query
from embar.query.select import SelectQuery
from embar.query.selection import Selection
from embar.query.update import UpdateQuery
from embar.sql_db import DbSql
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

    def select[S: Selection](self, sel: type[S]) -> SelectQuery[S, DbBase]:
        return SelectQuery[S, DbBase](db=self, sel=sel)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, DbBase]:
        return InsertQuery[T, DbBase](table=table, db=self)

    def update[T: Table](self, table: type[T]) -> UpdateQuery[T, Self]:
        return UpdateQuery[T, Self](table=table, db=self)

    def sql(self, template: Template) -> DbSql[Self]:
        return DbSql(template, self)

    def migrate(self, tables: Sequence[type[Table]], enums: Sequence[type[EnumBase]] | None = None) -> Migration[Self]:
        ddls = merge_ddls(MigrationDefs(tables, enums))
        return Migration(ddls, self)

    def migrates(self, schema: types.ModuleType) -> Migration[Self]:
        defs = get_migration_defs(schema)
        return self.migrate(defs.tables, defs.enums)

    @override
    def execute(self, query: Query) -> None:
        self._conn.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]
        self._conn.commit()

    @override
    def executemany(self, query: Query):
        params = _jsonify_dicts(query.many_params)
        with self._conn.cursor() as cur:
            cur.executemany(query.sql, params)  # pyright:ignore[reportArgumentType]
        self._conn.commit()

    @override
    def fetch(self, query: Query) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]

            if cur.description is None:
                return []
            columns: list[str] = [desc[0] for desc in cur.description]
            results: list[dict[str, Any]] = []
            for row in cur.fetchall():
                data = dict(zip(columns, row))
                results.append(data)
        self._conn.commit()  # Commit after SELECT
        return results

    @override
    def truncate(self, schema: str | None = None):
        schema = schema if schema is not None else "public"
        with self._conn.cursor() as cursor:
            # Get all table names from public schema
            cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'")  # pyright:ignore[reportArgumentType]
            tables = cursor.fetchall()
            if not tables:
                return
            table_names = ", ".join([f'"{table[0]}"' for table in tables])
            cursor.execute(f"TRUNCATE TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
            self._conn.commit()


@final
class AsyncDb(AsyncDbBase):
    db_type = "postgres"
    _conn: AsyncConnection

    def __init__(self, connection: AsyncConnection):
        self._conn = connection

    async def close(self):
        if self._conn:
            await self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> SelectQuery[S, Self]:
        return SelectQuery[S, Self](db=self, sel=sel)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, Self]:
        return InsertQuery[T, Self](table=table, db=self)

    def update[T: Table](self, table: type[T]) -> UpdateQuery[T, Self]:
        return UpdateQuery[T, Self](table=table, db=self)

    def sql(self, template: Template) -> DbSql[Self]:
        return DbSql(template, self)

    def migrate(self, tables: Sequence[type[Table]], enums: Sequence[type[EnumBase]] | None = None) -> Migration[Self]:
        ddls = merge_ddls(MigrationDefs(tables, enums))
        return Migration(ddls, self)

    def migrates(self, schema: types.ModuleType) -> Migration[Self]:
        defs = get_migration_defs(schema)
        return self.migrate(defs.tables, defs.enums)

    @override
    async def execute(self, query: Query) -> None:
        await self._conn.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]

    @override
    async def executemany(self, query: Query):
        params = _jsonify_dicts(query.many_params)
        async with self._conn.cursor() as cur:
            await cur.executemany(query.sql, params)  # pyright:ignore[reportArgumentType]
            await self._conn.commit()

    @override
    async def fetch(self, query: Query) -> list[dict[str, Any]]:
        async with self._conn.cursor() as cur:
            await cur.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]

            if cur.description is None:
                return []
            columns: list[str] = [desc[0] for desc in cur.description]
            results: list[dict[str, Any]] = []
            for row in await cur.fetchall():
                data = dict(zip(columns, row))
                results.append(data)
        await self._conn.commit()
        return results

    @override
    async def truncate(self, schema: str | None = None):
        schema = schema if schema is not None else "public"
        async with self._conn.cursor() as cursor:
            # Get all table names from public schema
            await cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'")  # pyright:ignore[reportArgumentType]
            tables = await cursor.fetchall()
            if tables:
                table_names = ", ".join([f'"{table[0]}"' for table in tables])
                await cursor.execute(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")  # pyright:ignore[reportArgumentType]
            await self._conn.commit()


def _jsonify_dicts(params: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    psycopg requires that dicts get passed through its `Json` function.
    """
    return [{k: Json(v) if isinstance(v, dict) else v for k, v in p.items()} for p in params]
