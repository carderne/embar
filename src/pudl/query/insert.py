from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import (
    Any,
    NoReturn,
    Self,
    overload,
)

from pudl.db.base import AllDbBase, AsyncDbBase, DbBase
from pudl.table import Table
from pudl.types import Undefined


@dataclass
class InsertQuery[T: Table, Db: AllDbBase]:
    """
    `InsertQuery` is used to insert data into a table.

    It is generic over the `Table` being inserted into, and the database being used.

    It has a regular `execute()` method, and an async `aexecute()` method.
    These are typed to return `NoReturn` when the wrong one is used, but there doesn't
    seem to be a way to make it an error to use them in the wrong case.

    `InsertQuery` is never used directly, but always returned by a Db instance.

    Example:
    >>> from pudl.db.pg import Db
    >>> db = Db(None)
    >>> insert = db.insert(None)
    >>> assert isinstance(insert, InsertQuery)
    """

    _db: Db
    table: type[T]
    items: list[T] = Undefined

    def value(self, item: T) -> Self:
        """
        Load a single item into the table.
        """
        self.items = [item]
        return self

    def values(self, items: Sequence[T]) -> Self:
        """
        Load a sequence of items into the table.
        """
        self.items = list(items)
        return self

    def _build_sql(self) -> tuple[str, list[dict[str, Any]]]:
        """
        Create the SQL query and binding parameters (psycopg format) for the query.

        Example:
        >>> from pudl.column.common import Text
        >>> from pudl.table import Table
        >>> @dataclass
        ... class MyTable(Table):
        ...     my_col: Text = Text()
        >>> row = MyTable(my_col="foo")
        >>> insert = InsertQuery(_db=None, table=MyTable, items=[row])
        >>> insert._build_sql()
        ('INSERT INTO "my_table" ("my_col") VALUES (%(my_col)s)', [{'my_col': 'foo'}])
        """
        # TODO this (and `execute`) should actually be on a separate class.
        # It's possible for an `InsertQuery` to have no `self.items` set, in which case calling this will error
        column_names = self.table.column_names().values()
        column_names_quoted = [f'"{c}"' for c in column_names]
        columns = ", ".join(column_names_quoted)
        placeholders = [f"%({name})s" for name in column_names]
        placeholder_str = ", ".join(placeholders)
        sql = f"INSERT INTO {self.table.fqn()} ({columns}) VALUES ({placeholder_str})"
        values = [it.value_dict() for it in self.items]
        return sql, values

    @overload
    def execute(self: InsertQuery[T, DbBase]) -> None: ...

    @overload
    def execute(self: InsertQuery[T, AsyncDbBase]) -> NoReturn: ...

    def execute(self):
        """
        Run the query against the underlying DB.

        Errors if `self._db` is async.
        """
        if not isinstance(self._db, DbBase):
            raise Exception("You need to use 'await ...aexecute()' here!")
        sql, params = self._build_sql()
        self._db.executemany(sql, params)

    @overload
    async def aexecute(self: InsertQuery[T, DbBase]) -> NoReturn: ...

    @overload
    async def aexecute(self: InsertQuery[T, AsyncDbBase]) -> None: ...

    async def aexecute(self):
        """
        Run the query against the underlying DB.

        Errors if `self._db` is non-async.
        """
        if not isinstance(self._db, AsyncDbBase):
            raise Exception("You need to use '...execute()' here (not 'aexecute()')")
        sql, params = self._build_sql()
        await self._db.aexecutemany(sql, params)
