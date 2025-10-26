from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal

from pudl.types import Undefined

DbType = Literal["sqlite"] | Literal["postgres"]


class AllDbBase:
    db_type: DbType = Undefined


class DbBase(ABC, AllDbBase):
    @abstractmethod
    def execute(self, query: str, params: dict[str, Any]): ...
    @abstractmethod
    def executemany(self, query: str, params: Sequence[dict[str, Any]]): ...
    @abstractmethod
    def fetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...


class AsyncDbBase(ABC, AllDbBase):
    @abstractmethod
    async def aexecute(self, query: str, params: dict[str, Any]): ...
    @abstractmethod
    async def aexecutemany(self, query: str, params: Sequence[dict[str, Any]]): ...
    @abstractmethod
    async def afetch(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
