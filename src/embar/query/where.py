from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, override

from embar.column.base import ColumnInfo
from embar.column.common import Column
from embar.custom_types import PyType

# Where clauses get passed a get_count() function that returns a monotonically
# increasing integer. This allows each SQL binding parameter to get a unique
# name like `%(eq_id_2)s` in psycopg format.
type GetCount = Callable[[], int]


@dataclass
class WhereData:
    """
    sql and params in psycopg format for the Where clause.

    Both are concatenated as they recurse up the tree.
    """

    sql: str
    params: dict[str, PyType]


class WhereClause(ABC):
    """
    ABC for Where clauses.

    Not all use the get_count() directly (those with no bindings)
    but their children might.
    """

    @abstractmethod
    def get(self, get_count: GetCount) -> WhereData: ...


# TODO add more where clause types


class Eq[T: PyType](WhereClause):
    """
    Checks if a column value is equal to another column or a passed param.

    Right now the left must always be a column, maybe that must be loosened.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"eq_{self.left.name}_{count}"

        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} = {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} = %({name})s", params={name: self.right})


@dataclass
class Like[T: PyType](WhereClause):
    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"like_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} = {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} LIKE %({name})s", params={name: self.right})


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
