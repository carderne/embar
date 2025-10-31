from collections.abc import Mapping
from typing import (
    Any,
    NoReturn,
    Self,
    overload,
)

from embar.custom_types import Undefined
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.where import WhereClause
from embar.table import Table


class UpdateQuery[T: Table, Db: AllDbBase]:
    """
    `UpdateQuery` is used to update rows.

    It is never used directly, but always created from a Db.

    Example:
    >>> from embar.db.pg import Db
    >>> db = Db(None)
    >>> update = db.update(None)
    >>> assert isinstance(update, UpdateQuery)
    """

    table: type[T]
    _db: Db

    _where_clause: WhereClause | None = None

    data: Mapping[str, Any] = Undefined

    def __init__(self, table: type[T], db: Db):
        self.table = table
        self._db = db

    def set(self, data: Mapping[str, Any]) -> Self:
        self.data = data
        return self

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    @overload
    def execute(self: UpdateQuery[T, DbBase]) -> None: ...

    @overload
    def execute(self: UpdateQuery[T, AsyncDbBase]) -> NoReturn: ...

    def execute(self):
        if not isinstance(self._db, DbBase):
            raise Exception("You need to use 'await ...aexecute()' here!")

        sql, params = self._build_sql()
        self._db.execute(sql, params)

    @overload
    async def aexecute(self: UpdateQuery[T, DbBase]) -> NoReturn: ...

    @overload
    async def aexecute(self: UpdateQuery[T, AsyncDbBase]) -> None: ...

    async def aexecute(self):
        if not isinstance(self._db, AsyncDbBase):
            raise Exception("You need to use '...execute()' here (not 'aexecute()')")

        sql, params = self._build_sql()
        await self._db.aexecute(sql, params)

    def _build_sql(self) -> tuple[str, dict[str, Any]]:
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
            where_data = self._where_clause.get(get_count)
            sql += f" WHERE {where_data.sql} "
            params = {**params, **where_data.params}

        return sql, params
