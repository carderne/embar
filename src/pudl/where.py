from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, override

from pudl.table import ColumnInfo

GetCount = Callable[[], int]
Param = ColumnInfo | str | int | float | bool


@dataclass
class WhereData:
    sql: str
    params: dict[str, Param]


class WhereClause(ABC):
    @abstractmethod
    def get(self, get_count: GetCount) -> WhereData: ...


@dataclass
class Eq(WhereClause):
    column: ColumnInfo
    value: Param

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"eq_{self.column.name}_{count}"

        if isinstance(self.value, ColumnInfo):
            return WhereData(sql=f"{self.column.fqn} = {self.value.fqn}", params={})

        return WhereData(
            sql=f"{self.column.fqn} = %({name})s", params={name: self.value}
        )


@dataclass
class Like(WhereClause):
    column: ColumnInfo
    value: Param

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"like_{self.column.name}_{count}"
        if isinstance(self.value, ColumnInfo):
            return WhereData(sql=f"{self.column.fqn} = {self.value.fqn}", params={})

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
