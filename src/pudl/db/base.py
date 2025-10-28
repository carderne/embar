from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal

from pudl.types import Undefined

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


class AsyncDbBase(ABC, AllDbBase):
    """
    Base class for async Db clients.
    """

    @abstractmethod
    async def aexecute(self, query: str, params: dict[str, Any]): ...
    @abstractmethod
    async def aexecutemany(self, query: str, params: Sequence[dict[str, Any]]): ...
    @abstractmethod
    async def afetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
