from abc import ABC, abstractmethod


class QueryFn(ABC):
    @abstractmethod
    def sql(self) -> str: ...
