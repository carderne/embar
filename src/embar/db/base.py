from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal

from embar.custom_types import Undefined

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
    def execute(self, query: str, params: dict[str, Any]): ...
    @abstractmethod
    def executemany(self, query: str, params: Sequence[dict[str, Any]]): ...
    @abstractmethod
    def fetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
    @abstractmethod
    def truncate(self, schema: str | None = None) -> None: ...


class AsyncDbBase(ABC, AllDbBase):
    """
    Base class for async Db clients.
    """

    @abstractmethod
    async def execute(self, query: str, params: dict[str, Any]): ...
    @abstractmethod
    async def executemany(self, query: str, params: Sequence[dict[str, Any]]): ...
    @abstractmethod
    async def fetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
    @abstractmethod
    async def truncate(self, schema: str | None = None) -> None: ...
