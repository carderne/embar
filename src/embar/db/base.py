"""Base classes for database clients."""

from abc import ABC, abstractmethod
from typing import Any, Literal

from embar.custom_types import Undefined
from embar.query.query import QueryMany, QuerySingle

DbType = Literal["sqlite"] | Literal["postgres"]


class AllDbBase:
    """
    Base class (not an ABC, but could be) for all Db clients.
    """

    db_type: DbType = Undefined


class DbBase(ABC, AllDbBase):
    """
    Base class for _sync_ Db clients.
    """

    @abstractmethod
    def execute(self, query: QuerySingle):
        """
        Execute a query without returning results.
        """
        ...

    @abstractmethod
    def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        ...

    @abstractmethod
    def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.
        """
        ...

    @abstractmethod
    def truncate(self, schema: str | None = None) -> None:
        """
        Truncate all tables in the schema.
        """
        ...

    @abstractmethod
    def drop_tables(self, schema: str | None = None) -> None:
        """
        Drop all tables in the schema.
        """
        ...


class AsyncDbBase(ABC, AllDbBase):
    """
    Base class for async Db clients.
    """

    @abstractmethod
    async def execute(self, query: QuerySingle):
        """
        Execute a query without returning results.
        """
        ...

    @abstractmethod
    async def executemany(self, query: QueryMany):
        """
        Execute a query with multiple parameter sets.
        """
        ...

    @abstractmethod
    async def fetch(self, query: QuerySingle | QueryMany) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.
        """
        ...

    @abstractmethod
    async def truncate(self, schema: str | None = None) -> None:
        """
        Truncate all tables in the schema.
        """
        ...

    @abstractmethod
    async def drop_tables(self, schema: str | None = None) -> None:
        """
        Drop all tables in the schema.
        """
        ...
