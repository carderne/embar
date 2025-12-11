"""SQLite database client."""

import json
import sqlite3
import types
from collections.abc import Sequence
from datetime import datetime
from string.templatelib import Template
from typing import (
    Any,
    Self,
    final,
    override,
)

from pydantic import BaseModel

from embar.column.base import EnumBase
from embar.db._util import get_migration_defs, merge_ddls
from embar.db.base import DbBase
from embar.migration import Migration, MigrationDefs
from embar.query.delete import DeleteQueryReady
from embar.query.insert import InsertQuery
from embar.query.query import QueryMany, QuerySingle
from embar.query.select import SelectDistinctQuery, SelectQuery
from embar.query.update import UpdateQuery
from embar.sql_db import DbSql
from embar.table import Table


@final
class SqliteDb(DbBase):
    """
    SQLite database client for synchronous operations.
    """

    db_type = "sqlite"
    conn: sqlite3.Connection
    _commit_after_execute: bool = True

    def __init__(self, connection: sqlite3.Connection):
        """
        Create a new SqliteDb instance.
        """
        self.conn = connection
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()

    def transaction(self) -> SqliteDbTransaction:
        """
        Start an isolated transaction.
        """
        db_copy = SqliteDb(self.conn)
        db_copy._commit_after_execute = False
        return SqliteDbTransaction(db_copy)

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
        sql = _convert_params(query.sql)
        self.conn.execute(sql, query.params)
        if self._commit_after_execute:
            self.conn.commit()

    @override
    def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        sql = _convert_params(query.sql)
        self.conn.executemany(sql, query.many_params)
        if self._commit_after_execute:
            self.conn.commit()

    @override
    def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Fetch all rows returned by a SELECT query.

        sqlite returns json/arrays as string, so need to parse them.
        """
        sql = _convert_params(query.sql)
        if isinstance(query, QuerySingle):
            cur = self.conn.execute(sql, query.params)
        else:
            cur = self.conn.executemany(sql, query.many_params)

        if cur.description is None:
            return []

        results: list[dict[str, Any]] = []
        for row in cur.fetchall():
            row_dict = dict(row)
            for key, value in row_dict.items():
                if isinstance(value, str):
                    try:
                        row_dict[key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        try:
                            row_dict[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass  # Keep as string
            results.append(row_dict)
        return results

    @override
    def truncate(self, schema: str | None = None):
        """
        Truncate all tables in the database.
        """
        cursor = self.conn.cursor()
        tables = self._get_live_table_names()
        for (table_name,) in tables:
            cursor.execute(f"DELETE FROM {table_name}")
        if self._commit_after_execute:
            self.conn.commit()

    @override
    def drop_tables(self, schema: str | None = None):
        """
        Drop all tables in the database.
        """
        cursor = self.conn.cursor()
        tables = self._get_live_table_names()
        for (table_name,) in tables:
            cursor.execute(f"DROP TABLE {table_name}")
        if self._commit_after_execute:
            self.conn.commit()

    def _get_live_table_names(self) -> list[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables: list[str] = cursor.fetchall()
        return tables


class SqliteDbTransaction:
    """
    Transaction context manager for SqliteDb
    """

    _db: SqliteDb

    def __init__(self, db: SqliteDb):
        self._db = db

    def __enter__(self) -> SqliteDb:
        self._db.conn.execute("BEGIN")
        return self._db

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        if exc_type is None:
            self._db.conn.commit()
        else:
            self._db.conn.rollback()
        return False


def _convert_params(query: str) -> str:
    """
    Convert psycopg %(name)s to sqlite :name format
    """
    import re

    return re.sub(r"%\((\w+)\)s", r":\1", query)
