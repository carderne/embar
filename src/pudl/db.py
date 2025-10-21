from typing import (
    Self,
    final,
)
from psycopg import Connection
import psycopg

from pudl.table import Table
from pudl.query import InsertQuery, SelectQuery


@final
class Database:
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._conn: Connection

    def connect(self) -> Self:
        self._conn = psycopg.connect(self.conn_string)
        return self

    def close(self):
        if self._conn:
            self._conn.close()

    def select[T: Table](self, table: type[T]) -> SelectQuery[T]:
        return SelectQuery[T](table=table, _conn=self._conn)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T]:
        return InsertQuery[T](table=table, _conn=self._conn)

    def migrate(self, table: type[Table]) -> Self:
        self._conn.execute(table.ddl())  # pyright:ignore[reportArgumentType]
        self._conn.commit()
        return self
