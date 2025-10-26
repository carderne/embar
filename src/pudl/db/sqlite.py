from collections.abc import Sequence
from datetime import datetime
import json
import sqlite3
import types
from typing import (
    Any,
    Self,
    final,
    override,
)

from pudl._util import topological_sort_tables
from pudl.db.base import DbBase
from pudl.selection import Selection
from pudl.table import Table
from pudl.query import From, InsertQuery


@final
class Db(DbBase):
    db_type = "sqlite"

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    def close(self):
        if self._conn:
            self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> From[S, DbBase]:
        return From[S, DbBase](_db=self, sel=sel)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, DbBase]:
        return InsertQuery[T, DbBase](table=table, _db=self)

    def migrate(self, tables: Sequence[type[Table]]) -> Self:
        for table in tables:
            self._conn.execute(table.ddl())
        self._conn.commit()
        return self

    def migrates(self, schema: types.ModuleType) -> Self:
        tables: list[type[Table]] = []
        for name in dir(schema):
            obj = getattr(schema, name)
            if isinstance(obj, type) and issubclass(obj, Table) and obj is not Table:
                tables.append(obj)
        tables = topological_sort_tables(tables)
        self.migrate(tables)
        return self

    @override
    def execute(self, query: str, params: dict[str, Any]) -> None:
        # Convert psycopg %(name)s to sqlite :name format
        query = self._convert_params(query)
        self._conn.execute(query, params)

    @override
    def executemany(self, query: str, params: Sequence[dict[str, Any]]):
        query = self._convert_params(query)
        self._conn.executemany(query, params)
        self._conn.commit()

    @override
    def fetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Fetch all rows returned by a SELECT query.

        sqlite returns json/arrays as string, so need to parse them.
        """
        query = self._convert_params(query)
        cur = self._conn.execute(query, params)

        if cur.description is None:
            return []

        results: list[dict[str, Any]] = []
        for row in cur.fetchall():
            row_dict = dict(row)
            for key, value in row_dict.items():
                if isinstance(value, str):
                    # TODO do this in a more sensible way (use the schema!)
                    try:
                        row_dict[key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        try:
                            row_dict[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass  # Keep as string
            results.append(row_dict)
        return results

    def _convert_params(self, query: str) -> str:
        """
        Convert psycopg %(name)s to sqlite :name format
        """
        import re

        return re.sub(r"%\((\w+)\)s", r":\1", query)
