"""Migration classes for creating and running database migrations."""

from collections.abc import Generator, Sequence
from typing import Any, cast, overload

from embar.column.base import EnumBase
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.query import QuerySingle
from embar.table import Table


class Ddl:
    """
    Represents a DDL statement with optional constraints.
    """

    name: str
    ddl: str
    constraints: list[str]

    def __init__(self, name: str, ddl: str, constraints: list[str] | None = None):
        """
        Create a new Ddl instance.
        """
        self.name = name
        self.ddl = ddl
        self.constraints = constraints if constraints is not None else []


class MigrationDefs:
    """
    Holds table and enum definitions for migrations.
    """

    tables: list[type[Table]]
    enums: list[type[EnumBase]]

    def __init__(self, tables: Sequence[type[Table]], enums: Sequence[type[EnumBase]] | None = None):
        """
        Create a new MigrationDefs instance.
        """
        self.tables = list(tables)
        self.enums = list(enums) if enums is not None else []


class Migration[Db: AllDbBase]:
    """
    Represents a migration that can be run against a database.
    """

    ddls: list[Ddl]
    _db: Db

    def __init__(self, ddls: list[Ddl], db: Db):
        """
        Create a new Migration instance.
        """
        self.ddls = ddls
        self._db = db

    @property
    def merged(self) -> str:
        """
        Get all DDL statements merged into a single string.
        """
        query = ""
        for table in self.ddls:
            query += "\n\n" + table.ddl
            for constraint in table.constraints:
                query += "\n" + constraint

        return query

    def __await__(self) -> Generator[Any, None, None]:
        """
        Run the migration asynchronously.
        """

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                for ddl in self.ddls:
                    await db.execute(QuerySingle(ddl.ddl))
                    for constraint in ddl.constraints:
                        await db.execute(QuerySingle(constraint))

            else:
                db = cast(DbBase, self._db)
                for ddl in self.ddls:
                    db.execute(QuerySingle(ddl.ddl))
                    for constraint in ddl.constraints:
                        db.execute(QuerySingle(constraint))

        return awaitable().__await__()

    @overload
    def run(self: Migration[DbBase]) -> None: ...
    @overload
    def run(self: Migration[AsyncDbBase]) -> Migration[Db]: ...
    def run(self) -> None | Migration[Db]:
        """
        Run the migration synchronously.
        """
        if isinstance(self._db, DbBase):
            for ddl in self.ddls:
                self._db.execute(QuerySingle(ddl.ddl))
                for constraint in ddl.constraints:
                    self._db.execute(QuerySingle(constraint))
            return
        return self
