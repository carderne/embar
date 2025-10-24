from collections.abc import Sequence
from typing import (
    Any,
    Self,
    final,
)
from psycopg import AsyncConnection, Connection
import psycopg

from pudl.table import Selection, Table
from pudl.query import Async, From, InsertQuery, Sync


class AbstractDb: ...


@final
class Db(AbstractDb):
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._conn: Connection

    def connect(self) -> Self:
        self._conn = psycopg.connect(self.conn_string)
        return self

    def close(self):
        if self._conn:
            self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> From[S, Sync]:
        return From[S, Sync](_conn=self._conn, sel=sel, _mode=Sync)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, Sync]:
        return InsertQuery[T, Sync](table=table, _conn=self._conn, _mode=Sync)

    def migrate(self, tables: Sequence[type[Table]]) -> Self:
        for table in tables:
            self._conn.execute(table.ddl())  # pyright:ignore[reportArgumentType]
        self._conn.commit()
        return self

    def execute(self, query: str, params: dict[str, Any]) -> None:
        self._conn.execute(query, params)  # pyright:ignore[reportArgumentType]


@final
class AsyncDb(AbstractDb):
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._conn: AsyncConnection

    async def connect(self) -> Self:
        self._conn = await AsyncConnection.connect(self.conn_string)
        return self

    async def close(self):
        if self._conn:
            await self._conn.close()

    def select[S: Selection](self, sel: type[S]) -> From[S, Async]:
        return From[S, Async](_conn=self._conn, sel=sel, _mode=Async)

    def insert[T: Table](self, table: type[T]) -> InsertQuery[T, Async]:
        return InsertQuery[T, Async](table=table, _conn=self._conn, _mode=Async)

    async def migrate(self, tables: Sequence[type[Table]]) -> Self:
        for table in tables:
            await self._conn.execute(table.ddl())  # pyright:ignore[reportArgumentType]
        await self._conn.commit()
        return self

    async def execute(self, query: str, params: dict[str, Any]) -> None:
        await self._conn.execute(query, params)  # pyright:ignore[reportArgumentType]
