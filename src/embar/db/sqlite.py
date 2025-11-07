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

from embar.column.base import EnumBase
from embar.db._util import get_migration_defs, merge_ddls
from embar.db.base import DbBase
from embar.migration import Migration, MigrationDefs
from embar.query.insert import InsertQuery
from embar.query.query import Query
from embar.query.select import SelectDistinctQuery, SelectQuery
from embar.query.selection import Selection
from embar.query.update import UpdateQuery
from embar.sql_db import DbSql
from embar.table import Table


@final
class SqliteDb(DbBase):
    """
    SQLite database client for synchronous operations.
    """

    db_type = "sqlite"

    def __init__(self, connection: sqlite3.Connection):
        """
        Create a new SqliteDb instance.
        """
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    def close(self):
        """
        Close the database connection.
        """
        if self._conn:
            self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> SelectQuery[S, Self]:
        """
        Create a SELECT query.
        """
        return SelectQuery[S, Self](db=self, sel=sel)

    def select_distinct[S: Selection](self, sel: type[S]) -> SelectDistinctQuery[S, Self]:
        """
        Create a SELECT query.
        """
        return SelectDistinctQuery[S, Self](db=self, sel=sel)

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
    def execute(self, query: Query) -> None:
        """
        Execute a query without returning results.
        """
        sql = _convert_params(query.sql)
        self._conn.execute(sql, query.params)
        self._conn.commit()

    @override
    def executemany(self, query: Query):
        """
        Execute a query with multiple parameter sets.
        """
        sql = _convert_params(query.sql)
        self._conn.executemany(sql, query.many_params)
        self._conn.commit()

    @override
    def fetch(self, query: Query) -> list[dict[str, Any]]:
        """
        Fetch all rows returned by a SELECT query.

        sqlite returns json/arrays as string, so need to parse them.
        """
        sql = _convert_params(query.sql)
        cur = self._conn.execute(sql, query.params)

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
        cursor = self._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            cursor.execute(f"DELETE FROM {table_name}")
        self._conn.commit()


def _convert_params(query: str) -> str:
    """
    Convert psycopg %(name)s to sqlite :name format
    """
    import re

    return re.sub(r"%\((\w+)\)s", r":\1", query)
