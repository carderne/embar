"""Postgres database clients for sync and async operations."""

import types
from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from string.templatelib import Template
from typing import (
    Any,
    Self,
    final,
    override,
)

from psycopg import AsyncConnection, AsyncTransaction, Connection, Transaction
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool, ConnectionPool
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


class ConnectionWrapper[C: Connection | ConnectionPool]:
    conn_or_pool: C

    def __init__(self, conn_or_pool: C):
        self.conn_or_pool = conn_or_pool
        self._cm: AbstractContextManager[Connection] | None = None

    def __enter__(self) -> Connection:
        if isinstance(self.conn_or_pool, Connection):
            return self.conn_or_pool

        # Ensure pool is open (idempotent if already open)
        self.conn_or_pool.open()

        self._cm = self.conn_or_pool.connection()
        return self._cm.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool | None:
        if self._cm is not None:
            return self._cm.__exit__(exc_type, exc_val, exc_tb)
        return None

    def close(self):
        self.conn_or_pool.close()


class AsyncConnectionWrapper[C: AsyncConnection | AsyncConnectionPool]:
    conn_or_pool: C

    def __init__(self, conn_or_pool: C):
        self.conn_or_pool = conn_or_pool
        self._cm: AbstractAsyncContextManager[AsyncConnection] | None = None

    async def __aenter__(self) -> AsyncConnection:
        if isinstance(self.conn_or_pool, AsyncConnection):
            return self.conn_or_pool

        # Ensure pool is open (must be awaited for async pools)
        await self.conn_or_pool.open()

        self._cm = self.conn_or_pool.connection()
        return await self._cm.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool | None:
        if self._cm is not None:
            return await self._cm.__aexit__(exc_type, exc_val, exc_tb)
        return None

    async def close(self):
        await self.conn_or_pool.close()


@final
class PgDb(DbBase):
    """
    Postgres database client for synchronous operations.
    """

    db_type = "postgres"
    conn_wrapper: ConnectionWrapper[Connection | ConnectionPool]
    _commit_after_execute: bool = True

    def __init__(self, connection_or_pool: Connection | ConnectionPool):
        """
        Create a new PgDb instance.
        """
        self.conn_wrapper = ConnectionWrapper(connection_or_pool)

    def close(self):
        """
        Close the database connection.
        """
        if self.conn_wrapper:
            self.conn_wrapper.close()

    def transaction(self) -> PgDbTransaction:
        """
        Start an isolated transaction.

        ```python notest
        from embar.db.pg import PgDb
        db = PgDb(None)

        with db.transaction() as tx:
            ...
        ```
        """
        return PgDbTransaction(self)

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
        with self.conn_wrapper as conn:
            conn.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]
            if self._commit_after_execute:
                conn.commit()

    @override
    def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        params = _jsonify_dicts(query.many_params)
        with self.conn_wrapper as conn:
            with conn.cursor() as cur:
                cur.executemany(query.sql, params)  # pyright:ignore[reportArgumentType]
            if self._commit_after_execute:
                conn.commit()

    @override
    def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.
        """
        with self.conn_wrapper as conn:
            with conn.cursor() as cur:
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
            if self._commit_after_execute:
                conn.commit()  # Commit after SELECT
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
        with self.conn_wrapper as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
                if self._commit_after_execute:
                    conn.commit()

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
        with self.conn_wrapper as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"DROP TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
                if self._commit_after_execute:
                    conn.commit()

    def _get_live_table_names(self, schema: str) -> list[str] | None:
        with self.conn_wrapper as conn:
            with conn.cursor() as cursor:
                # Get all table names from public schema
                cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'")  # pyright:ignore[reportArgumentType]
                tables = cursor.fetchall()
                if not tables:
                    return None
                table_names = [f'"{table[0]}"' for table in tables]
            return table_names


class PgDbTransaction:
    """
    Transaction context manager for PgDb.
    """

    _db: PgDb
    _conn_cm: AbstractContextManager[Connection] | None = None
    _tx: AbstractContextManager[Transaction] | None = None

    def __init__(self, db: PgDb):
        self._db = db

    def __enter__(self) -> PgDb:
        pool_or_conn = self._db.conn_wrapper.conn_or_pool

        if isinstance(pool_or_conn, ConnectionPool):
            # Ensure pool is open (idempotent if already open)
            pool_or_conn.open()

            # Check out a dedicated connection for the transaction
            self._conn_cm = pool_or_conn.connection()
            conn = self._conn_cm.__enter__()
        else:
            conn = pool_or_conn

        # Create a PgDb that uses this single connection (no auto-commit)
        tx_db = PgDb(conn)
        tx_db._commit_after_execute = False  # pyright: ignore[reportPrivateUsage]
        self._db = tx_db

        self._tx = conn.transaction()
        self._tx.__enter__()
        return tx_db

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ):
        result = None
        if self._tx is not None:
            result = self._tx.__exit__(exc_type, exc_val, exc_tb)
        if self._conn_cm is not None:
            self._conn_cm.__exit__(exc_type, exc_val, exc_tb)
        return result


@final
class AsyncPgDb(AsyncDbBase):
    """
    Postgres database client for async operations.
    """

    db_type = "postgres"
    conn_wrapper: AsyncConnectionWrapper[AsyncConnection | AsyncConnectionPool]
    _commit_after_execute: bool = True

    def __init__(self, connection_or_pool: AsyncConnection | AsyncConnectionPool):
        """
        Create a new AsyncPgDb instance.
        """
        self.conn_wrapper = AsyncConnectionWrapper(connection_or_pool)

    async def close(self):
        """
        Close the database connection.
        """
        if self.conn_wrapper:
            await self.conn_wrapper.close()

    def transaction(self) -> AsyncPgDbTransaction:
        """
        Start an isolated transaction.

        ```python notest
        from embar.db.pg import AsyncPgDb
        db = AsyncPgDb(None)

        async with db.transaction() as tx:
            ...
        ```
        """
        return AsyncPgDbTransaction(self)

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
        async with self.conn_wrapper as conn:
            await conn.execute(query.sql, query.params)  # pyright:ignore[reportArgumentType]
            if self._commit_after_execute:
                await conn.commit()

    @override
    async def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        params = _jsonify_dicts(query.many_params)
        async with self.conn_wrapper as conn:
            async with conn.cursor() as cur:
                await cur.executemany(query.sql, params)  # pyright:ignore[reportArgumentType]
            if self._commit_after_execute:
                await conn.commit()

    @override
    async def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.
        """
        async with self.conn_wrapper as conn:
            async with conn.cursor() as cur:
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
            if self._commit_after_execute:
                await conn.commit()
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
        async with self.conn_wrapper as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"TRUNCATE TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
                if self._commit_after_execute:
                    await conn.commit()

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
        async with self.conn_wrapper as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"DROP TABLE {table_names} CASCADE")  # pyright:ignore[reportArgumentType]
                if self._commit_after_execute:
                    await conn.commit()

    async def _get_live_table_names(self, schema: str) -> list[str] | None:
        async with self.conn_wrapper as conn:
            async with conn.cursor() as cursor:
                # Get all table names from public schema
                await cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}'")  # pyright:ignore[reportArgumentType]
                tables = await cursor.fetchall()
                if not tables:
                    return None
                table_names = [f'"{table[0]}"' for table in tables]
            return table_names


class AsyncPgDbTransaction:
    """
    Transaction context manager for AsyncPgDb.
    """

    _db: AsyncPgDb
    _conn_cm: AbstractAsyncContextManager[AsyncConnection] | None = None
    _tx: AbstractAsyncContextManager[AsyncTransaction] | None = None

    def __init__(self, db: AsyncPgDb):
        self._db = db

    async def __aenter__(self) -> AsyncPgDb:
        pool_or_conn = self._db.conn_wrapper.conn_or_pool

        if isinstance(pool_or_conn, AsyncConnectionPool):
            # Ensure pool is open
            await pool_or_conn.open()

            # Check out a dedicated connection for the transaction
            self._conn_cm = pool_or_conn.connection()
            conn = await self._conn_cm.__aenter__()
        else:
            conn = pool_or_conn

        # Create an AsyncPgDb that uses this single connection (no auto-commit)
        tx_db = AsyncPgDb(conn)
        tx_db._commit_after_execute = False  # pyright: ignore[reportPrivateUsage]
        self._db = tx_db

        self._tx = conn.transaction()
        await self._tx.__aenter__()
        return tx_db

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ):
        result = None
        if self._tx is not None:
            result = await self._tx.__aexit__(exc_type, exc_val, exc_tb)
        if self._conn_cm is not None:
            await self._conn_cm.__aexit__(exc_type, exc_val, exc_tb)
        return result


def _jsonify_dicts(params: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    psycopg requires that dicts get passed through its `Json` function.
    """
    return [{k: Json(v) if isinstance(v, dict) else v for k, v in p.items()} for p in params]
