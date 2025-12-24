"""Update query builder."""

from collections.abc import Generator, Mapping, Sequence
from typing import Any, Self, cast, overload

from pydantic import BaseModel, TypeAdapter

from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.model import generate_model
from embar.query.clause_base import ClauseBase
from embar.query.query import QuerySingle
from embar.table import Table


class UpdateQuery[T: Table, Db: AllDbBase]:
    """
    `UpdateQuery` is used to update rows.

    It is never used directly, but always created from a Db.
    It returns an `UpdateQueryReady` instance once `set()` has been called.

    ```python
    from embar.db.pg import PgDb
    from embar.query.update import UpdateQuery
    db = PgDb(None)
    update = db.update(None)
    assert isinstance(update, UpdateQuery)
    ```
    """

    table: type[T]
    _db: Db

    def __init__(self, table: type[T], db: Db):
        """
        Create a new UpdateQuery instance.
        """
        self.table = table
        self._db = db

    def set(self, data: Mapping[str, Any]) -> UpdateQueryReady[T, Db]:
        """
        Set the values to be updated.
        """
        return UpdateQueryReady(table=self.table, db=self._db, data=data)


class UpdateQueryReady[T: Table, Db: AllDbBase]:
    """
    `UpdateQueryReady` is an update query that is ready to be awaited or run.
    """

    table: type[T]
    _db: Db
    data: Mapping[str, Any]
    _where_clause: ClauseBase | None = None

    def __init__(self, table: type[T], db: Db, data: Mapping[str, Any]):
        """
        Create a new UpdateQueryReady instance.
        """
        self.table = table
        self._db = db
        self.data = data

    def where(self, where_clause: ClauseBase) -> Self:
        """
        Add a WHERE clause to limit which rows are updated.
        """
        self._where_clause = where_clause
        return self

    def returning(self) -> UpdateQueryReturning[T, Db]:
        return UpdateQueryReturning(self.table, self._db, self.data, self._where_clause)

    def __await__(self):
        """
        async users should construct their query and await it.

        non-async users have the `run()` convenience method below.
        """
        query = self.sql()

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                return await db.execute(query)
            else:
                db = cast(DbBase, self._db)
                return db.execute(query)

        return awaitable().__await__()

    @overload
    def run(self: UpdateQueryReady[T, DbBase]) -> None: ...
    @overload
    def run(self: UpdateQueryReady[T, AsyncDbBase]) -> UpdateQueryReady[T, Db]: ...

    def run(self) -> None | UpdateQueryReady[T, Db]:
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            return self._db.execute(query)
        return self

    def sql(self) -> QuerySingle:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """
        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        cols = self.table.column_names()

        setters: list[str] = []
        for field_name, value in self.data.items():
            col = cols[field_name]
            count = get_count()
            binding_name = f"set_{field_name}_{count}"
            setter = f'"{col}" = %({binding_name})s'
            setters.append(setter)
            params[binding_name] = value

        set_stmt = ", ".join(setters)
        sql = f"UPDATE {self.table.fqn()} SET {set_stmt}"

        if self._where_clause is not None:
            where_data = self._where_clause.sql(get_count)
            sql += f"\nWHERE {where_data.sql}"
            params = {**params, **where_data.params}

        return QuerySingle(sql, params)


class UpdateQueryReturning[T: Table, Db: AllDbBase]:
    """
    `UpdateQueryReturning` is an update query that returns all results.
    """

    table: type[T]
    _db: Db
    data: Mapping[str, Any]
    _where_clause: ClauseBase | None = None

    def __init__(self, table: type[T], db: Db, data: Mapping[str, Any], where_clause: ClauseBase | None):
        """
        Create a new UpdateQueryReturning instance.
        """
        self.table = table
        self._db = db
        self.data = data
        self._where_clause = where_clause

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
    def run(self: UpdateQueryReturning[T, DbBase]) -> list[T]: ...
    @overload
    def run(self: UpdateQueryReturning[T, AsyncDbBase]) -> UpdateQueryReturning[T, Db]: ...

    def run(self) -> list[T] | UpdateQueryReturning[T, Db]:
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

    def sql(self) -> QuerySingle:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """
        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        cols = self.table.column_names()

        setters: list[str] = []
        for field_name, value in self.data.items():
            col = cols[field_name]
            count = get_count()
            binding_name = f"set_{field_name}_{count}"
            setter = f'"{col}" = %({binding_name})s'
            setters.append(setter)
            params[binding_name] = value

        set_stmt = ", ".join(setters)
        sql = f"UPDATE {self.table.fqn()} SET {set_stmt}"

        if self._where_clause is not None:
            where_data = self._where_clause.sql(get_count)
            sql += f"\nWHERE {where_data.sql}"
            params = {**params, **where_data.params}

        sql += " RETURNING *"

        return QuerySingle(sql, params)

    def _get_model(self) -> type[BaseModel]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.
        """
        model = generate_model(self.table)
        return model
