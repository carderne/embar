from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, override

from pudl.table import ColumnInfo


@dataclass
class WhereData:
    sql: str
    params: dict[str, Any]


GetCount = Callable[[], int]


class WhereClause(ABC):
    @abstractmethod
    def get(self, get_count: GetCount) -> WhereData: ...


@dataclass
class Eq(WhereClause):
    column: ColumnInfo
    value: Any

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"eq_{self.column.name}_{count}"
        return WhereData(
            sql=f"{self.column.fqn} = %({name})s", params={name: self.value}
        )


@dataclass
class Like(WhereClause):
    column: ColumnInfo
    value: Any

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"like_{self.column.name}_{count}"
        return WhereData(
            sql=f"{self.column.fqn} LIKE %({name})s", params={name: self.value}
        )


@dataclass
class And(WhereClause):
    left: WhereClause
    right: WhereClause

    @override
    def get(self, get_count: GetCount) -> WhereData:
        left = self.left.get(get_count)
        right = self.right.get(get_count)
        params = {**left.params, **right.params}
        sql = f"{left.sql} AND {right.sql}"
        return WhereData(sql=sql, params=params)


@dataclass
class Or(WhereClause):
    left: WhereClause
    right: WhereClause

    @override
    def get(self, get_count: GetCount) -> WhereData:
        left = self.left.get(get_count)
        right = self.right.get(get_count)
        params = {**left.params, **right.params}
        sql = f"{left.sql} OR {right.sql}"
        return WhereData(sql=sql, params=params)


@dataclass
class Where:
    clause: WhereClause
