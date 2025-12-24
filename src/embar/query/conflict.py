from abc import ABC, abstractmethod
from typing import override

from embar.custom_types import PyType
from embar.query.clause_base import GetCount
from embar.query.query import QuerySingle

# require at least one element in tuple
TupleAtLeastOne = tuple[str, *tuple[str, ...]]


class OnConflict(ABC):
    @abstractmethod
    def sql(self, get_count: GetCount) -> QuerySingle: ...


class OnConflictDoNothing(OnConflict):
    target: TupleAtLeastOne | None

    def __init__(self, target: TupleAtLeastOne | None = None):
        self.target = target

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        if self.target is not None:
            target = f"({', '.join(self.target)})"
        else:
            target = ""
        q = f"ON CONFLICT {target} DO NOTHING"
        return QuerySingle(q, {})


class OnConflictDoUpdate[T: dict[str, PyType]](OnConflict):
    target: TupleAtLeastOne
    update: T

    def __init__(self, target: TupleAtLeastOne, update: T):
        if len(update) == 0:
            raise ValueError("update dict cannot be empty")

        self.target = target
        self.update = update

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        targets = ", ".join(self.target)
        target = f"({targets})"

        sets: list[str] = []
        params: dict[str, PyType] = {}
        for key, val in self.update.items():
            count = get_count()
            name = f"set_{key}_{count}"
            q = f"{key} = %({name})s"
            sets.append(q)
            params[name] = val

        updates_str = ",\n".join(sets)

        q = f"ON CONFLICT {target} DO UPDATE SET {updates_str}"
        return QuerySingle(q, params)
