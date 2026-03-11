"""Raw SQL query execution with optional result parsing."""

from collections.abc import Generator, Sequence
from string.templatelib import Template
from typing import Any, Self, cast

from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.model import BaseModel, DataModel, load_results, upgrade_model_nested_fields
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

    def model[M: DataModel](self, model: type[M]) -> DbSqlReturning[M, Db]:
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

    def run(self) -> Self:
        """
        Run the query synchronously without returning results.

        Returns self so that `await db.sql(...).run()` works for async.
        For sync callers, the return value can be ignored.
        """
        if isinstance(self._db, DbBase):
            sql = self._sql.sql()
            query = QuerySingle(sql)
            self._db.execute(query)
        return self


class DbSqlReturning[M: DataModel, Db: AllDbBase]:
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

        async def awaitable():
            db = self._db

            if isinstance(db, AsyncDbBase):
                data = await db.fetch(query)
            else:
                db = cast(DbBase, self._db)
                data = db.fetch(query)
            results = load_results(model, data)
            return results

        return awaitable().__await__()

    def run(self) -> Sequence[M]:
        """
        Run the query synchronously and return parsed results.

        For async, use `await query` instead.
        """
        sql = self._sql.sql()
        query = QuerySingle(sql)
        model = self._get_model()
        db = cast(DbBase, self._db)
        data = db.fetch(query)
        results = load_results(model, data)
        return results

    def _get_model(self) -> type[M]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.
        """
        use_pydantic = isinstance(self.model, type) and issubclass(self.model, BaseModel)
        return upgrade_model_nested_fields(self.model, use_pydantic=use_pydantic)
