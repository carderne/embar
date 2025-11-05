"""Base class for table constraints."""

from abc import ABC, abstractmethod

from embar.query.query import Query


class Constraint(ABC):
    """
    Base class for all table constraints like indexes and unique constraints.
    """

    @abstractmethod
    def sql(self) -> Query: ...
