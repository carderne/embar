from collections.abc import Generator, Sequence
from string.templatelib import Template
from typing import Any, cast, overload

from dacite import from_dict

from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.query import Query
from embar.query.selection import Selection, selection_to_dataclass
from embar.sql import Sql


class DbSql[Db: AllDbBase]:
    """
    Used to run raw SQL queries.
    """

    sql: Sql
    _db: Db

    def __init__(self, template: Template, db: Db):
        self.sql = Sql(template)
        self._db = db

    def model[S: Selection](self, sel: type[S]) -> DbSqlReturning[S, Db]:
        return DbSqlReturning(self.sql, sel, self._db)

    def __await__(self):
        sql = self.sql.execute()
        query = Query(sql)

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
        if isinstance(self._db, DbBase):
            sql = self.sql.execute()
            query = Query(sql)
            self._db.execute(query)
        return self


class DbSqlReturning[S: Selection, Db: AllDbBase]:
    """
    Used to run raw SQL queries and return a value.
    """

    sql: Sql
    sel: type[S]
    _db: Db

    def __init__(self, sql: Sql, sel: type[S], db: Db):
        self.sql = sql
        self.sel = sel
        self._db = db

    def __await__(self) -> Generator[Any, None, Sequence[S]]:
        sql = self.sql.execute()
        query = Query(sql)

        async def awaitable():
            db = self._db

            if isinstance(db, AsyncDbBase):
                data = await db.fetch(query)
            else:
                db = cast(DbBase, self._db)
                data = db.fetch(query)
            results = [from_dict(self.sel, d) for d in data]
            return results

        return awaitable().__await__()

    @overload
    def run(self: DbSqlReturning[S, DbBase]) -> Sequence[S]: ...
    @overload
    def run(self: DbSqlReturning[S, AsyncDbBase]) -> DbSqlReturning[S, Db]: ...

    def run(self) -> Sequence[S] | DbSqlReturning[S, Db]:
        if isinstance(self._db, DbBase):
            sql = self.sql.execute()
            query = Query(sql)
            data = self._db.fetch(query)
            selection = self._get_selection()
            self.sel.__init_subclass__()
            results = [from_dict(selection, d) for d in data]
            return results
        return self

    def _get_selection(self) -> type[S]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.
        """
        return selection_to_dataclass(self.sel)
