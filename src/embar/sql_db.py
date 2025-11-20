"""Raw SQL query execution with optional result parsing."""

from collections.abc import Generator, Sequence
from string.templatelib import Template
from typing import Any, cast, overload

from pydantic import BaseModel, TypeAdapter

from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.model import upgrade_model_nested_fields
from embar.query.query import QuerySingle
from embar.sql import Sql


class DbSql[Db: AllDbBase]:
    """
    Used to run raw SQL queries.
    """

    _sql: Sql
    _db: Db

    def __init__(self, template: Template, db: Db):
        """
        Create a new DbSql instance.
        """
        self._sql = Sql(template)
        self._db = db

    def model[M: BaseModel](self, model: type[M]) -> DbSqlReturning[M, Db]:
        """
        Specify a model for parsing results.
        """
        return DbSqlReturning(self._sql, model, self._db)

    def sql(self) -> str:
        return self._sql.sql()

    def __await__(self):
        """
        Run the query asynchronously without returning results.
        """
        sql = self._sql.sql()
        query = QuerySingle(sql)

        async def awaitable():
            db = self._db

            if isinstance(db, AsyncDbBase):
                await db.execute(query)
            else:
                db = cast(DbBase, self._db)
                db.execute(query)

        return awaitable().__await__()

    @overload
    def run(self: DbSql[DbBase]) -> None: ...
    @overload
    def run(self: DbSql[AsyncDbBase]) -> DbSql[Db]: ...

    def run(self) -> None | DbSql[Db]:
        """
        Run the query synchronously without returning results.
        """
        if isinstance(self._db, DbBase):
            sql = self._sql.sql()
            query = QuerySingle(sql)
            self._db.execute(query)
        return self


class DbSqlReturning[M: BaseModel, Db: AllDbBase]:
    """
    Used to run raw SQL queries and return a value.
    """

    _sql: Sql
    model: type[M]
    _db: Db

    def __init__(self, sql: Sql, model: type[M], db: Db):
        """
        Create a new DbSqlReturning instance.
        """
        self._sql = sql
        self.model = model
        self._db = db

    def sql(self) -> str:
        return self._sql.sql()

    def __await__(self) -> Generator[Any, None, Sequence[M]]:
        """
        Run the query asynchronously and return parsed results.
        """
        sql = self._sql.sql()
        query = QuerySingle(sql)
        model = self._get_model()
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
    def run(self: DbSqlReturning[M, DbBase]) -> Sequence[M]: ...
    @overload
    def run(self: DbSqlReturning[M, AsyncDbBase]) -> DbSqlReturning[M, Db]: ...

    def run(self) -> Sequence[M] | DbSqlReturning[M, Db]:
        """
        Run the query synchronously and return parsed results.
        """
        if isinstance(self._db, DbBase):
            sql = self._sql.sql()
            query = QuerySingle(sql)
            data = self._db.fetch(query)
            model = self._get_model()
            adapter = TypeAdapter(list[model])
            self.model.__init_subclass__()
            results = adapter.validate_python(data)
            return results
        return self

    def _get_model(self) -> type[M]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.
        """
        return upgrade_model_nested_fields(self.model)
