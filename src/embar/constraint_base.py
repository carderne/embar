from abc import ABC, abstractmethod

from embar.query.query import Query


class Constraint(ABC):
    @abstractmethod
    def sql(self) -> Query: ...
