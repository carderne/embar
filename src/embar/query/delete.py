"""Select query builder."""

from collections.abc import Generator
from textwrap import dedent
from typing import Any, Self, cast, overload

from pydantic import BaseModel, TypeAdapter

from embar.column.base import ColumnBase
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.model import (
    generate_model,
)
from embar.query.clause_base import ClauseBase
from embar.query.order_by import Asc, BareColumn, Desc, OrderBy, RawSqlOrder
from embar.query.query import QuerySingle
from embar.sql import Sql
from embar.table import Table


class DeleteQueryReady[T: Table, Db: AllDbBase]:
    """
    `DeleteQueryReady` is used to delete data from a table.

    It is generic over the `Table` being inserted into, and the database being used.

    `DeleteQueryReady` is returned by `db.delete()`
    """

    table: type[T]
    _db: Db

    _where_clause: ClauseBase | None = None
    _order_clause: OrderBy | None = None
    _limit_value: int | None = None

    def __init__(self, table: type[T], db: Db):
        """
        Create a new SelectQueryReady instance.
        """
        self.table = table
        self._db = db

    def returning(self) -> DeleteQueryReturning[T, Db]:
        return DeleteQueryReturning(self.table, self._db, self._where_clause, self._order_clause, self._limit_value)

    def where(self, where_clause: ClauseBase) -> Self:
        """
        Add a WHERE clause to the query.
        """
        self._where_clause = where_clause
        return self

    def order_by(self, *clauses: ColumnBase | Asc | Desc | Sql) -> Self:
        """
        Add an ORDER BY clause to sort query results.

        Accepts multiple ordering clauses:
        - Bare column references (defaults to ASC): `User.id`
        - `Asc(User.id)` or `Asc(User.id, nulls="last")`
        - `Desc(User.id)` or `Desc(User.id, nulls="first")`
        - Raw SQL: `Sql(t"{User.id} DESC")`

        Can be called multiple times to add more sort columns.

        ```python
        from embar.db.pg import PgDb
        from embar.table import Table
        from embar.column.common import Integer

        class User(Table):
            id: Integer = Integer(primary=True)

        db = PgDb(None)

        query = db.delete(User).order_by(User.id)
        sql_result = query.sql()
        assert "ORDER BY" in sql_result.sql
        ```
        """
        # Convert each clause to an OrderByClause
        order_clauses: list[ClauseBase] = []
        for clause in clauses:
            if isinstance(clause, (Asc, Desc)):
                order_clauses.append(clause)
            elif isinstance(clause, Sql):
                order_clauses.append(RawSqlOrder(clause))
            else:
                order_clauses.append(BareColumn(clause))

        if self._order_clause is None:
            self._order_clause = OrderBy(tuple(order_clauses))
        else:
            # Add to existing ORDER BY clauses
            self._order_clause = OrderBy((*self._order_clause.clauses, *order_clauses))

        return self

    def limit(self, n: int) -> Self:
        """
        Add a LIMIT clause to the query.
        """
        self._limit_value = n
        return self

    def __await__(self):
        """
        Async users should construct their query and await it.

        Non-async users have the `run()` convenience method below.
        But this method will still work if called in an async context against a non-async db.

        The overrides provide for a few different cases:
        - A Model was passed, in which case that's the return type
        - `SelectAll` was passed, in which case the return type is the `Table`
        - This is called with an async db, in which case an error is returned.
        """
        query = self.sql()

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                await db.execute(query)
            else:
                db = cast(DbBase, self._db)
                db.execute(query)

        return awaitable().__await__()

    @overload
    def run(self: DeleteQueryReady[T, DbBase]) -> None: ...
    @overload
    def run(self: DeleteQueryReady[T, AsyncDbBase]) -> DeleteQueryReady[T, Db]: ...

    def run(self) -> None | DeleteQueryReady[T, Db]:
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            self._db.execute(query)
        return self

    def sql(self) -> QuerySingle:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """

        sql = f"""
        DELETE
        FROM {self.table.fqn()}
        """
        sql = dedent(sql).strip()

        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        if self._where_clause is not None:
            where_data = self._where_clause.sql(get_count)
            sql += f"\nWHERE {where_data.sql}"
            params = {**params, **where_data.params}

        if self._order_clause is not None:
            order_by_query = self._order_clause.sql(get_count)
            sql += f"\nORDER BY {order_by_query.sql}"
            params = {**params, **order_by_query.params}

        if self._limit_value is not None:
            sql += f"\nLIMIT {self._limit_value}"

        sql = sql.strip()

        return QuerySingle(sql, params=params)


class DeleteQueryReturning[T: Table, Db: AllDbBase]:
    """
    `DeleteQueryReturning` is used to delete data from a table and return it.
    """

    table: type[T]
    _db: Db

    _where_clause: ClauseBase | None = None
    _order_clause: OrderBy | None = None
    _limit_value: int | None = None

    def __init__(
        self,
        table: type[T],
        db: Db,
        where_clause: ClauseBase | None,
        order_clause: OrderBy | None,
        limit_value: int | None,
    ):
        """
        Create a new SelectQueryReady instance.
        """
        self.table = table
        self._db = db
        self._where_clause = where_clause
        self._order_clause = order_clause
        self._limit_value = limit_value

    def __await__(self) -> Generator[Any, None, list[T]]:
        """
        Async users should construct their query and await it.

        Non-async users have the `run()` convenience method below.
        But this method will still work if called in an async context against a non-async db.

        The overrides provide for a few different cases:
        - A Model was passed, in which case that's the return type
        - `SelectAll` was passed, in which case the return type is the `Table`
        - This is called with an async db, in which case an error is returned.
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
    def run(self: DeleteQueryReady[T, DbBase]) -> list[T]: ...
    @overload
    def run(self: DeleteQueryReady[T, AsyncDbBase]) -> DeleteQueryReturning[T, Db]: ...

    def run(self) -> list[T] | DeleteQueryReturning[T, Db]:
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

        sql = f"""
        DELETE
        FROM {self.table.fqn()}
        """
        sql = dedent(sql).strip()

        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        if self._where_clause is not None:
            where_data = self._where_clause.sql(get_count)
            sql += f"\nWHERE {where_data.sql}"
            params = {**params, **where_data.params}

        if self._order_clause is not None:
            order_by_query = self._order_clause.sql(get_count)
            sql += f"\nORDER BY {order_by_query.sql}"
            params = {**params, **order_by_query.params}

        if self._limit_value is not None:
            sql += f"\nLIMIT {self._limit_value}"

        # This is the only difference vs the regular DeleteQueryReady sql
        sql += "\nRETURNING *"

        sql = sql.strip()

        return QuerySingle(sql, params=params)

    def _get_model(self) -> type[BaseModel]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.
        """
        model = generate_model(self.table)
        return model
