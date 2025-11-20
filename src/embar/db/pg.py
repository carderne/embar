"""Postgres database clients for sync and async operations."""

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
from pydantic import BaseModel

from embar.column.base import EnumBase
from embar.db._util import get_migration_defs, merge_ddls
from embar.db.base import AsyncDbBase, DbBase
from embar.migration import Migration, MigrationDefs
from embar.query.delete import DeleteQueryReady
from embar.query.insert import InsertQuery
from embar.query.query import QueryMany, QuerySingle
from embar.query.select import SelectDistinctQuery, SelectQuery
from embar.query.update import UpdateQuery
from embar.sql_db import DbSql
from embar.table import Table


@final
class PgDb(DbBase):
    """
    Postgres database client for synchronous operations.
    """

    db_type = "postgres"
    _conn: Connection

    def __init__(self, connection: Connection):
        """
        Create a new PgDb instance.
        """
        self._conn = connection

    def close(self):
        """
        Close the database connection.
        """
        if self._conn:
            self._conn.close()

    def select[M: BaseModel](self, model: type[M]) -> SelectQuery[M, Self]:
        """
        Create a SELECT query.
        """
        return SelectQuery[M, Self](db=self, model=model)

    def select_distinct[M: BaseModel](self, model: type[M]) -> SelectDistinctQuery[M, Self]:
        """
        Create a SELECT query.
        """
        return SelectDistinctQuery[M, Self](db=self, model=model)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, Self]:
        """
        Create an INSERT query.
        """
        return InsertQuery[T, Self](table=table, db=self)

    def update[T: Table](self, table: type[T]) -> UpdateQuery[T, Self]:
        """
        Create an UPDATE query.
        """
        return UpdateQuery[T, Self](table=table, db=self)

    def delete[T: Table](self, table: type[T]) -> DeleteQueryReady[T, Self]:
        """
        Create an UPDATE query.
        """
        return DeleteQueryReady[T, Self](table=table, db=self)

    def sql(self, template: Template) -> DbSql[Self]:
        """
        Execute a raw SQL query using template strings.
        """
        return DbSql(template, self)

    def migrate(self, tables: Sequence[type[Table]], enums: Sequence[type[EnumBase]] | None = None) -> Migration[Self]:
        """
        Create a migration from a list of tables.
        """
        ddls = merge_ddls(MigrationDefs(tables, enums))
        return Migration(ddls, self)

    def migrates(self, schema: types.ModuleType) -> Migration[Self]:
        """
        Create a migration from a schema module.
        """
        defs = get_migration_defs(schema)
        return self.migrate(defs.tables, defs.enums)

    @override
    def execute(self, query: QuerySingle) -> None:
        """
        Execute a query without returning results.
        """
        self._conn.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]
        self._conn.commit()

    @override
    def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        params = _jsonify_dicts(query.many_params)
        with self._conn.cursor() as cur:
            cur.executemany(query.sql, params)  # pyright:ignore[reportArgumentType]
        self._conn.commit()

    @override
    def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.
        """
        with self._conn.cursor() as cur:
            if isinstance(query, QuerySingle):
                cur.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]
            else:
                cur.executemany(query.sql, query.many_params, returning=True)  # pyright:ignore[reportArgumentType]

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
        """
        Truncate all tables in the schema.
        """
        schema = schema if schema is not None else "public"
        tables = self._get_live_table_names(schema)
        if tables is None:
            return
        table_names = ", ".join(tables)
        with self._conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
            self._conn.commit()

    @override
    def drop_tables(self, schema: str | None = None):
        """
        Drop all tables in the schema.
        """
        schema = schema if schema is not None else "public"
        tables = self._get_live_table_names(schema)
        if tables is None:
            return
        table_names = ", ".join(tables)
        with self._conn.cursor() as cursor:
            cursor.execute(f"DROP TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
            self._conn.commit()

    def _get_live_table_names(self, schema: str) -> list[str] | None:
        with self._conn.cursor() as cursor:
            # Get all table names from public schema
            cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'")  # pyright:ignore[reportArgumentType]
            tables = cursor.fetchall()
            if not tables:
                return None
            table_names = [f'"{table[0]}"' for table in tables]
        return table_names


@final
class AsyncPgDb(AsyncDbBase):
    """
    Postgres database client for async operations.
    """

    db_type = "postgres"
    _conn: AsyncConnection

    def __init__(self, connection: AsyncConnection):
        """
        Create a new AsyncPgDb instance.
        """
        self._conn = connection

    async def close(self):
        """
        Close the database connection.
        """
        if self._conn:
            await self._conn.close()

    def select[M: BaseModel](self, model: type[M]) -> SelectQuery[M, Self]:
        """
        Create a SELECT query.
        """
        return SelectQuery[M, Self](db=self, model=model)

    def select_distinct[M: BaseModel](self, model: type[M]) -> SelectDistinctQuery[M, Self]:
        """
        Create a SELECT query.
        """
        return SelectDistinctQuery[M, Self](db=self, model=model)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, Self]:
        """
        Create an INSERT query.
        """
        return InsertQuery[T, Self](table=table, db=self)

    def update[T: Table](self, table: type[T]) -> UpdateQuery[T, Self]:
        """
        Create an UPDATE query.
        """
        return UpdateQuery[T, Self](table=table, db=self)

    def delete[T: Table](self, table: type[T]) -> DeleteQueryReady[T, Self]:
        """
        Create an UPDATE query.
        """
        return DeleteQueryReady[T, Self](table=table, db=self)

    def sql(self, template: Template) -> DbSql[Self]:
        """
        Execute a raw SQL query using template strings.
        """
        return DbSql(template, self)

    def migrate(self, tables: Sequence[type[Table]], enums: Sequence[type[EnumBase]] | None = None) -> Migration[Self]:
        """
        Create a migration from a list of tables.
        """
        ddls = merge_ddls(MigrationDefs(tables, enums))
        return Migration(ddls, self)

    def migrates(self, schema: types.ModuleType) -> Migration[Self]:
        """
        Create a migration from a schema module.
        """
        defs = get_migration_defs(schema)
        return self.migrate(defs.tables, defs.enums)

    @override
    async def execute(self, query: QuerySingle) -> None:
        """
        Execute a query without returning results.
        """
        await self._conn.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]

    @override
    async def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        params = _jsonify_dicts(query.many_params)
        async with self._conn.cursor() as cur:
            await cur.executemany(query.sql, params)  # pyright:ignore[reportArgumentType]
            await self._conn.commit()

    @override
    async def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.
        """
        async with self._conn.cursor() as cur:
            if isinstance(query, QuerySingle):
                await cur.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]
            else:
                await cur.executemany(query.sql, query.many_params, returning=True)  # pyright:ignore[reportArgumentType]

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
        """
        Truncate all tables in the schema.
        """
        schema = schema if schema is not None else "public"
        tables = await self._get_live_table_names(schema)
        if tables is None:
            return
        table_names = ", ".join(tables)
        async with self._conn.cursor() as cursor:
            await cursor.execute(f"TRUNCATE TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
            await self._conn.commit()

    @override
    async def drop_tables(self, schema: str | None = None):
        """
        Drop all tables in the schema.
        """
        schema = schema if schema is not None else "public"
        tables = await self._get_live_table_names(schema)
        if tables is None:
            return
        table_names = ", ".join(tables)
        async with self._conn.cursor() as cursor:
            await cursor.execute(f"DROP TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
            await self._conn.commit()

    async def _get_live_table_names(self, schema: str) -> list[str] | None:
        async with self._conn.cursor() as cursor:
            # Get all table names from public schema
            await cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'")  # pyright:ignore[reportArgumentType]
            tables = await cursor.fetchall()
            if not tables:
                return None
            table_names = [f'"{table[0]}"' for table in tables]
        return table_names


def _jsonify_dicts(params: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    psycopg requires that dicts get passed through its `Json` function.
    """
    return [{k: Json(v) if isinstance(v, dict) else v for k, v in p.items()} for p in params]
