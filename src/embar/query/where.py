from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, override

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
    params: dict[str, PyType | list[PyType]]


class WhereClause(ABC):
    """
    ABC for Where clauses.

    Not all use the get_count() directly (those with no bindings)
    but their children might.
    """

    @abstractmethod
    def get(self, get_count: GetCount) -> WhereData: ...


# Comparison operators
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


class Ne[T: PyType](WhereClause):
    """
    Checks if a column value is not equal to another column or a passed param.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"ne_{self.left.name}_{count}"

        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} != {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} != %({name})s", params={name: self.right})


class Gt[T: PyType](WhereClause):
    """
    Checks if a column value is greater than another column or a passed param.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"gt_{self.left.name}_{count}"

        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} > {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} > %({name})s", params={name: self.right})


class Gte[T: PyType](WhereClause):
    """
    Checks if a column value is greater than or equal to another column or a passed param.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"gte_{self.left.name}_{count}"

        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} >= {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} >= %({name})s", params={name: self.right})


class Lt[T: PyType](WhereClause):
    """
    Checks if a column value is less than another column or a passed param.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"lt_{self.left.name}_{count}"

        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} < {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} < %({name})s", params={name: self.right})


class Lte[T: PyType](WhereClause):
    """
    Checks if a column value is less than or equal to another column or a passed param.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"lte_{self.left.name}_{count}"

        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} <= {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} <= %({name})s", params={name: self.right})


# String matching operators
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


class Ilike[T: PyType](WhereClause):
    """
    Case-insensitive LIKE pattern matching.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"ilike_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} ILIKE {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} ILIKE %({name})s", params={name: self.right})


class NotLike[T: PyType](WhereClause):
    """
    Negated LIKE pattern matching.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"notlike_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return WhereData(sql=f"{self.left.fqn} NOT LIKE {self.right.fqn}", params={})

        return WhereData(sql=f"{self.left.fqn} NOT LIKE %({name})s", params={name: self.right})


# Null checks
class IsNull(WhereClause):
    """
    Checks if a column value is NULL.
    """

    column: ColumnInfo

    def __init__(self, column: Column[Any]):
        self.column = column.info

    @override
    def get(self, get_count: GetCount) -> WhereData:
        return WhereData(sql=f"{self.column.fqn} IS NULL", params={})


class IsNotNull(WhereClause):
    """
    Checks if a column value is NOT NULL.
    """

    column: ColumnInfo

    def __init__(self, column: Column[Any]):
        self.column = column.info

    @override
    def get(self, get_count: GetCount) -> WhereData:
        return WhereData(sql=f"{self.column.fqn} IS NOT NULL", params={})


# Array/list operations
class InArray[T: PyType](WhereClause):
    """
    Checks if a column value is in a list of values.
    """

    column: ColumnInfo
    values: list[PyType]

    def __init__(self, column: Column[T], values: list[T]):
        self.column = column.info
        self.values = values

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"in_{self.column.name}_{count}"
        return WhereData(sql=f"{self.column.fqn} = ANY(%({name})s)", params={name: self.values})


class NotInArray[T: PyType](WhereClause):
    """
    Checks if a column value is not in a list of values.
    """

    column: ColumnInfo
    values: list[PyType]

    def __init__(self, column: Column[T], values: list[T]):
        self.column = column.info
        self.values = values

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        name = f"notin_{self.column.name}_{count}"
        return WhereData(sql=f"{self.column.fqn} != ALL(%({name})s)", params={name: self.values})


# Range operations


class Between[T: PyType](WhereClause):
    """
    Checks if a column value is between two values (inclusive).
    """

    column: ColumnInfo
    lower: PyType
    upper: PyType

    def __init__(self, column: Column[T], lower: T, upper: T):
        self.column = column.info
        self.lower = lower
        self.upper = upper

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        lower_name = f"between_lower_{self.column.name}_{count}"
        upper_name = f"between_upper_{self.column.name}_{count}"
        return WhereData(
            sql=f"{self.column.fqn} BETWEEN %({lower_name})s AND %({upper_name})s",
            params={lower_name: self.lower, upper_name: self.upper},
        )


class NotBetween[T: PyType](WhereClause):
    """
    Checks if a column value is not between two values (inclusive).
    """

    column: ColumnInfo
    lower: PyType
    upper: PyType

    def __init__(self, column: Column[T], lower: T, upper: T):
        self.column = column.info
        self.lower = lower
        self.upper = upper

    @override
    def get(self, get_count: GetCount) -> WhereData:
        count = get_count()
        lower_name = f"notbetween_lower_{self.column.name}_{count}"
        upper_name = f"notbetween_upper_{self.column.name}_{count}"
        return WhereData(
            sql=f"{self.column.fqn} NOT BETWEEN %({lower_name})s AND %({upper_name})s",
            params={lower_name: self.lower, upper_name: self.upper},
        )


# Subquery operations
# TODO support Exists and NotExists with subqueries


# Logical operators
class Not(WhereClause):
    """
    Negates a where clause.
    """

    clause: WhereClause

    def __init__(self, clause: WhereClause):
        self.clause = clause

    @override
    def get(self, get_count: GetCount) -> WhereData:
        inner = self.clause.get(get_count)
        return WhereData(sql=f"NOT ({inner.sql})", params=inner.params)


class And(WhereClause):
    left: WhereClause
    right: WhereClause

    def __init__(self, left: WhereClause, right: WhereClause):
        self.left = left
        self.right = right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        left = self.left.get(get_count)
        right = self.right.get(get_count)
        params = {**left.params, **right.params}
        sql = f"{left.sql} AND {right.sql}"
        return WhereData(sql=sql, params=params)


class Or(WhereClause):
    left: WhereClause
    right: WhereClause

    def __init__(self, left: WhereClause, right: WhereClause):
        self.left = left
        self.right = right

    @override
    def get(self, get_count: GetCount) -> WhereData:
        left = self.left.get(get_count)
        right = self.right.get(get_count)
        params = {**left.params, **right.params}
        sql = f"{left.sql} OR {right.sql}"
        return WhereData(sql=sql, params=params)
