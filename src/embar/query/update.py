from collections.abc import Mapping
from typing import Any, Self, cast

from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.query import Query
from embar.query.where import WhereClause
from embar.table import Table


class UpdateQuery[T: Table, Db: AllDbBase]:
    """
    `UpdateQuery` is used to update rows.

    It is never used directly, but always created from a Db.
    It returns an `UpdateQueryReady` instance once `set()` has been called.

    ```python
    from embar.db.pg import Db
    from embar.query.update import UpdateQuery
    db = Db(None)
    update = db.update(None)
    assert isinstance(update, UpdateQuery)
    ```
    """

    table: type[T]
    _db: Db

    def __init__(self, table: type[T], db: Db):
        self.table = table
        self._db = db

    def set(self, data: Mapping[str, Any]) -> UpdateQueryReady[T, Db]:
        return UpdateQueryReady(table=self.table, db=self._db, data=data)


class UpdateQueryReady[T: Table, Db: AllDbBase]:
    """
    `UpdateQueryReady` is an update query that is ready to be awaited or run.
    """

    table: type[T]
    _db: Db
    data: Mapping[str, Any]
    _where_clause: WhereClause | None = None

    def __init__(self, table: type[T], db: Db, data: Mapping[str, Any]):
        self.table = table
        self._db = db
        self.data = data

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    def __await__(self):
        """
        async users should construct their query and await it.

        non-async users have the `run()` convenience method below.
        """
        query = self.sql()
        if isinstance(self._db, AsyncDbBase):
            return self._db.execute(query).__await__()

        async def get_result():
            db = cast(DbBase, self._db)
            return db.execute(query)

        return get_result().__await__()

    def run(self):
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            return self._db.execute(query)
        return self

    def sql(self) -> Query:
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

        return Query(sql, params)
