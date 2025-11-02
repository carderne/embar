from abc import ABC, abstractmethod
from typing import Any, Literal

from embar.custom_types import Undefined
from embar.query.query import Query

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
    def execute(self, query: Query): ...
    @abstractmethod
    def executemany(self, query: Query): ...
    @abstractmethod
    def fetch(self, query: Query) -> list[dict[str, Any]]: ...
    @abstractmethod
    def truncate(self, schema: str | None = None) -> None: ...


class AsyncDbBase(ABC, AllDbBase):
    """
    Base class for async Db clients.
    """

    @abstractmethod
    async def execute(self, query: Query): ...
    @abstractmethod
    async def executemany(self, query: Query): ...
    @abstractmethod
    async def fetch(self, query: Query) -> list[dict[str, Any]]: ...
    @abstractmethod
    async def truncate(self, schema: str | None = None) -> None: ...
