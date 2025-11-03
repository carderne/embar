from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.query import Query
from embar.table import Table


class InsertQuery[T: Table, Db: AllDbBase]:
    """
    `InsertQuery` is used to insert data into a table.

    It is generic over the `Table` being inserted into, and the database being used.
    `InsertQuery` is never used directly, but always returned by a Db instance.
    It returns an `InsertQueryReady` instance once `values()` has been called.

    ```python
    from embar.db.pg import Db
    from embar.query.insert import InsertQuery
    db = Db(None)
    insert = db.insert(None)
    assert isinstance(insert, InsertQuery)
    ```
    """

    _db: Db
    table: type[T]

    def __init__(self, table: type[T], db: Db):
        self.table = table
        self._db = db

    def values(self, *items: T) -> InsertQueryReady[T, Db]:
        """
        Load a sequence of items into the table.
        """
        return InsertQueryReady(table=self.table, db=self._db, items=items)


@dataclass
class InsertQueryReady[T: Table, Db: AllDbBase]:
    """
    `InsertQueryReady` is an insert query that is ready to be awaited or run.
    """

    _db: Db
    table: type[T]
    items: Sequence[T]

    def __init__(self, table: type[T], db: Db, items: Sequence[T]):
        self.table = table
        self._db = db
        self.items = items

    def __await__(self):
        """
        async users should construct their query and await it.

        non-async users have the `run()` convenience method below.
        """
        query = self.sql()
        if isinstance(self._db, AsyncDbBase):
            return self._db.executemany(query).__await__()

        async def get_result():
            db = cast(DbBase, self._db)
            return db.executemany(query)

        return get_result().__await__()

    def run(self):
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            return self._db.executemany(query)
        return self

    def sql(self) -> Query:
        """
        Create the SQL query and binding parameters (psycopg format) for the query.

        ```python
        from embar.column.common import Text
        from embar.table import Table
        from embar.query.insert import InsertQueryReady
        class MyTable(Table):
            my_col: Text = Text()
        row = MyTable(my_col="foo")
        insert = InsertQueryReady(db=None, table=MyTable, items=[row])
        query = insert.sql()
        assert query.sql == 'INSERT INTO "my_table" ("my_col") VALUES (%(my_col)s)'
        assert query.many_params == [{'my_col': 'foo'}]
        ```
        """
        column_names = self.table.column_names().values()
        column_names_quoted = [f'"{c}"' for c in column_names]
        columns = ", ".join(column_names_quoted)
        placeholders = [f"%({name})s" for name in column_names]
        placeholder_str = ", ".join(placeholders)
        sql = f"INSERT INTO {self.table.fqn()} ({columns}) VALUES ({placeholder_str})"
        values = [it.value_dict() for it in self.items]
        return Query(sql, many_params=values)
