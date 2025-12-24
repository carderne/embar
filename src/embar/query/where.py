"""Where clauses for filtering queries."""

from typing import Any, Protocol, override

from embar.column.base import ColumnInfo
from embar.column.common import Column
from embar.custom_types import PyType
from embar.query.clause_base import ClauseBase, GetCount
from embar.query.query import QuerySingle


def _gen_comparison_sql(
    left: ColumnInfo | ClauseBase,
    right: ColumnInfo | PyType,
    operator: str,
    name_root: str,
    get_count: GetCount,
) -> QuerySingle:
    """Generate SQL for binary comparison operators."""
    name = "vals"
    params: dict[str, PyType] = {}

    if isinstance(left, ColumnInfo):
        left_sql = left.fqn()
        name = left.name
    else:
        left_result = left.sql(get_count)
        left_sql = left_result.sql
        params.update(left_result.params)

    if isinstance(right, ColumnInfo):
        right_sql = right.fqn()
    else:
        count = get_count()
        param_name = f"{name_root}_{name}_{count}"
        right_sql = f"%({param_name})s"
        params[param_name] = right

    return QuerySingle(sql=f"{left_sql} {operator} {right_sql}", params=params)


# Comparison operators
class Eq[T: PyType](ClauseBase):
    """
    Checks if a column value is equal to another column or a passed param.

    Right now the left must always be a column, maybe that must be loosened.
    """

    left: ColumnInfo | ClauseBase
    right: ColumnInfo | PyType

    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T):
        self.left = left.info if isinstance(left, Column) else left
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return _gen_comparison_sql(self.left, self.right, "=", "eq", get_count)


class Ne[T: PyType](ClauseBase):
    """
    Checks if a column value is not equal to another column or a passed param.
    """

    left: ColumnInfo | ClauseBase
    right: ColumnInfo | PyType

    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T):
        self.left = left.info if isinstance(left, Column) else left
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return _gen_comparison_sql(self.left, self.right, "!=", "ne", get_count)


class Gt[T: PyType](ClauseBase):
    """
    Checks if a column value is greater than another column or a passed param.
    """

    left: ColumnInfo | ClauseBase
    right: ColumnInfo | PyType

    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T):
        self.left = left.info if isinstance(left, Column) else left
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return _gen_comparison_sql(self.left, self.right, ">", "gt", get_count)


class Gte[T: PyType](ClauseBase):
    """
    Checks if a column value is greater than or equal to another column or a passed param.
    """

    left: ColumnInfo | ClauseBase
    right: ColumnInfo | PyType

    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T):
        self.left = left.info if isinstance(left, Column) else left
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return _gen_comparison_sql(self.left, self.right, ">=", "gte", get_count)


class Lt[T: PyType](ClauseBase):
    """
    Checks if a column value is less than another column or a passed param.
    """

    left: ColumnInfo | ClauseBase
    right: ColumnInfo | PyType

    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T):
        self.left = left.info if isinstance(left, Column) else left
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return _gen_comparison_sql(self.left, self.right, "<", "lt", get_count)


class Lte[T: PyType](ClauseBase):
    """
    Checks if a column value is less than or equal to another column or a passed param.
    """

    left: ColumnInfo | ClauseBase
    right: ColumnInfo | PyType

    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T):
        self.left = left.info if isinstance(left, Column) else left
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return _gen_comparison_sql(self.left, self.right, "<=", "lte", get_count)


# String matching operators
class Like[T: PyType](ClauseBase):
    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"like_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return QuerySingle(sql=f"{self.left.fqn()} = {self.right.fqn()}")

        return QuerySingle(sql=f"{self.left.fqn()} LIKE %({name})s", params={name: self.right})


class Ilike[T: PyType](ClauseBase):
    """
    Case-insensitive LIKE pattern matching.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"ilike_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return QuerySingle(sql=f"{self.left.fqn()} ILIKE {self.right.fqn()}")

        return QuerySingle(sql=f"{self.left.fqn()} ILIKE %({name})s", params={name: self.right})


class NotLike[T: PyType](ClauseBase):
    """
    Negated LIKE pattern matching.
    """

    left: ColumnInfo
    right: PyType | ColumnInfo

    def __init__(self, left: Column[T], right: T | Column[T]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"notlike_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return QuerySingle(sql=f"{self.left.fqn()} NOT LIKE {self.right.fqn()}")

        return QuerySingle(sql=f"{self.left.fqn()} NOT LIKE %({name})s", params={name: self.right})


# Null checks
class IsNull(ClauseBase):
    """
    Checks if a column value is NULL.
    """

    column: ColumnInfo

    def __init__(self, column: Column[Any]):
        self.column = column.info

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return QuerySingle(sql=f"{self.column.fqn()} IS NULL")


class IsNotNull(ClauseBase):
    """
    Checks if a column value is NOT NULL.
    """

    column: ColumnInfo

    def __init__(self, column: Column[Any]):
        self.column = column.info

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        return QuerySingle(sql=f"{self.column.fqn()} IS NOT NULL")


# Array/list operations
class InArray[T: PyType](ClauseBase):
    """
    Checks if a column value is in a list of values.
    """

    column: ColumnInfo
    values: list[PyType]

    def __init__(self, column: Column[T], values: list[T]):
        self.column = column.info
        self.values = values

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"in_{self.column.name}_{count}"
        return QuerySingle(sql=f"{self.column.fqn()} = ANY(%({name})s)", params={name: self.values})


class NotInArray[T: PyType](ClauseBase):
    """
    Checks if a column value is not in a list of values.
    """

    column: ColumnInfo
    values: list[PyType]

    def __init__(self, column: Column[T], values: list[T]):
        self.column = column.info
        self.values = values

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"notin_{self.column.name}_{count}"
        return QuerySingle(sql=f"{self.column.fqn()} != ALL(%({name})s)", params={name: self.values})


# Range operations


class Between[T: PyType](ClauseBase):
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
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        lower_name = f"between_lower_{self.column.name}_{count}"
        upper_name = f"between_upper_{self.column.name}_{count}"
        return QuerySingle(
            sql=f"{self.column.fqn()} BETWEEN %({lower_name})s AND %({upper_name})s",
            params={lower_name: self.lower, upper_name: self.upper},
        )


class NotBetween[T: PyType](ClauseBase):
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
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        lower_name = f"notbetween_lower_{self.column.name}_{count}"
        upper_name = f"notbetween_upper_{self.column.name}_{count}"
        return QuerySingle(
            sql=f"{self.column.fqn()} NOT BETWEEN %({lower_name})s AND %({upper_name})s",
            params={lower_name: self.lower, upper_name: self.upper},
        )


# Subquery operations
class SqlAble(Protocol):
    def sql(self) -> QuerySingle: ...


class Exists(ClauseBase):
    """
    Check if a subquery result exists.
    """

    query: SqlAble

    def __init__(self, query: SqlAble):
        self.query = query

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        query = self.query.sql()
        return QuerySingle(f"EXISTS ({query.sql})", query.params)


class NotExists(ClauseBase):
    """
    Check if a subquery result does not exist.
    """

    query: SqlAble

    def __init__(self, query: SqlAble):
        self.query = query

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        query = self.query.sql()
        return QuerySingle(f"NOT EXISTS ({query.sql})", query.params)


# Logical operators
class Not(ClauseBase):
    """
    Negates a where clause.
    """

    clause: ClauseBase

    def __init__(self, clause: ClauseBase):
        self.clause = clause

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        inner = self.clause.sql(get_count)
        return QuerySingle(sql=f"NOT ({inner.sql})", params=inner.params)


class And(ClauseBase):
    """
    AND two clauses.
    """

    left: ClauseBase
    right: ClauseBase

    def __init__(self, left: ClauseBase, right: ClauseBase):
        self.left = left
        self.right = right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        left = self.left.sql(get_count)
        right = self.right.sql(get_count)
        params = {**left.params, **right.params}
        sql = f"{left.sql} AND {right.sql}"
        return QuerySingle(sql=sql, params=params)


class Or(ClauseBase):
    """
    OR two clauses.
    """

    left: ClauseBase
    right: ClauseBase

    def __init__(self, left: ClauseBase, right: ClauseBase):
        self.left = left
        self.right = right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        left = self.left.sql(get_count)
        right = self.right.sql(get_count)
        params = {**left.params, **right.params}
        sql = f"{left.sql} OR {right.sql}"
        return QuerySingle(sql=sql, params=params)
