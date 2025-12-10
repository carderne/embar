"""Insert query builder."""

from collections.abc import Generator, Sequence
from typing import Any, Self, cast, overload

from pydantic import BaseModel, TypeAdapter

from embar.custom_types import PyType
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.model import generate_model
from embar.query.conflict import OnConflict, OnConflictDoNothing, OnConflictDoUpdate, TupleAtLeastOne
from embar.query.query import QueryMany
from embar.table import Table


class InsertQuery[T: Table, Db: AllDbBase]:
    """
    `InsertQuery` is used to insert data into a table.

    It is generic over the `Table` being inserted into, and the database being used.
    `InsertQuery` is never used directly, but always returned by a Db instance.
    It returns an `InsertQueryReady` instance once `values()` has been called.

    ```python
    from embar.db.pg import PgDb
    from embar.query.insert import InsertQuery
    db = PgDb(None)
    insert = db.insert(None)
    assert isinstance(insert, InsertQuery)
    ```
    """

    _db: Db
    table: type[T]

    def __init__(self, table: type[T], db: Db):
        """
        Create a new InsertQuery instance.
        """
        self.table = table
        self._db = db

    def values(self, *items: T) -> InsertQueryReady[T, Db]:
        """
        Load a sequence of items into the table.
        """
        return InsertQueryReady(table=self.table, db=self._db, items=items)


class InsertQueryReady[T: Table, Db: AllDbBase]:
    """
    `InsertQueryReady` is an insert query that is ready to be awaited or run.
    """

    _db: Db
    table: type[T]
    items: Sequence[T]
    on_conflict: OnConflict | None = None

    def __init__(self, table: type[T], db: Db, items: Sequence[T]):
        """
        Create a new InsertQueryReady instance.
        """
        self.table = table
        self._db = db
        self.items = items

    def returning(self) -> InsertQueryReturning[T, Db]:
        return InsertQueryReturning(self.table, self._db, self.items, on_conflict=self.on_conflict)

    def on_conflict_do_nothing(self, target: TupleAtLeastOne | None = None) -> Self:
        self.on_conflict = OnConflictDoNothing(target)
        return self

    def on_conflict_do_update(self, target: TupleAtLeastOne, update: dict[str, PyType]) -> Self:
        self.on_conflict = OnConflictDoUpdate(target, update)
        return self

    def __await__(self):
        """
        async users should construct their query and await it.

        non-async users have the `run()` convenience method below.
        """
        query = self.sql()

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                return await db.executemany(query)
            else:
                db = cast(DbBase, self._db)
                return db.executemany(query)

        return awaitable().__await__()

    @overload
    def run(self: InsertQueryReady[T, DbBase]) -> None: ...
    @overload
    def run(self: InsertQueryReady[T, AsyncDbBase]) -> InsertQueryReady[T, Db]: ...

    def run(self) -> InsertQueryReady[T, Db] | None:
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            return self._db.executemany(query)
        return self

    def sql(self) -> QueryMany:
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

        if self.on_conflict is not None:
            count = -1

            def get_count() -> int:
                nonlocal count
                count += 1
                return count

            conflict_query = self.on_conflict.sql(get_count)
            values = [{**row, **conflict_query.params} for row in values]
            sql += f"\n{conflict_query.sql}"

        return QueryMany(sql, many_params=values)


class InsertQueryReturning[T: Table, Db: AllDbBase]:
    """
    `InsertQueryReturning` is an insert query that will return what it inserts.
    """

    _db: Db
    table: type[T]
    items: Sequence[T]
    on_conflict: OnConflict | None

    def __init__(self, table: type[T], db: Db, items: Sequence[T], on_conflict: OnConflict | None):
        """
        Create a new InsertQueryReturning instance.
        """
        self.table = table
        self._db = db
        self.items = items
        self.on_conflict = on_conflict

    def __await__(self) -> Generator[Any, None, Sequence[T]]:
        """
        async users should construct their query and await it.

        non-async users have the `run()` convenience method below.
        """
        query = self.sql()
        model = self._get_model()
        model = cast(type[T], model)
        adapter = TypeAdapter(list[model])

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                data = await db.fetch(query)
            else:
                db = cast(DbBase, self._db)
                data = db.fetch(query)
            results = adapter.validate_python(data)
            return results

        return awaitable().__await__()

    @overload
    def run(self: InsertQueryReturning[T, DbBase]) -> list[T]: ...
    @overload
    def run(self: InsertQueryReturning[T, AsyncDbBase]) -> InsertQueryReturning[T, Db]: ...

    def run(self) -> Sequence[T] | InsertQueryReturning[T, Db]:
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            model = self._get_model()
            model = cast(type[T], model)
            adapter = TypeAdapter(list[model])
            data = self._db.fetch(query)
            results = adapter.validate_python(data)
            return results
        return self

    def sql(self) -> QueryMany:
        """
        Create the SQL query and binding parameters (psycopg format) for the query.
        """
        column_names = self.table.column_names().values()
        column_names_quoted = [f'"{c}"' for c in column_names]
        columns = ", ".join(column_names_quoted)
        placeholders = [f"%({name})s" for name in column_names]
        placeholder_str = ", ".join(placeholders)
        sql = f"INSERT INTO {self.table.fqn()} ({columns}) VALUES ({placeholder_str})"
        values = [it.value_dict() for it in self.items]

        if self.on_conflict is not None:
            count = -1

            def get_count() -> int:
                nonlocal count
                count += 1
                return count

            conflict_query = self.on_conflict.sql(get_count)
            values = [{**row, **conflict_query.params} for row in values]
            sql += f"\n{conflict_query.sql}"

        sql += " RETURNING *"
        return QueryMany(sql, many_params=values)

    def _get_model(self) -> type[BaseModel]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.
        """
        model = generate_model(self.table)
        return model
