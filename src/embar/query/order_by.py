"""Order by clause for sorting query results."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, override

from embar.column.base import ColumnBase
from embar.sql import Sql

type NullsOrdering = Literal["first", "last"]


class OrderByClause(ABC):
    """
    Base class for ORDER BY clause components.

    An ORDER BY clause can contain:
    - A bare column (defaults to ASC)
    - An Asc(column) or Desc(column) wrapper with optional nulls handling
    - Raw SQL via Sql(t"...")
    """

    @abstractmethod
    def sql(self) -> str:
        """Generate the SQL fragment for this ORDER BY component."""
        ...


class Asc(OrderByClause):
    """
    Represents an ascending sort order for a column.

    ```python
    from embar.query.order_by import Asc
    from embar.column.base import ColumnBase, ColumnInfo

    col = ColumnBase()
    col.info = ColumnInfo(
        _table_name=lambda: "users",
        name="age",
        col_type="INTEGER",
        py_type=int,
        primary=False,
        not_null=False
    )
    asc = Asc(col, nulls="last")
    sql = asc.sql()
    assert sql == '"users"."age" ASC NULLS LAST'
    ```
    """

    col: ColumnBase
    nulls: NullsOrdering | None

    def __init__(self, col: ColumnBase, nulls: NullsOrdering | None = None):
        """
        Create an ascending sort order.

        Args:
            col: The column to sort by
            nulls: Optional nulls ordering ("first" or "last")
        """
        self.col = col
        self.nulls = nulls

    @override
    def sql(self) -> str:
        """Generate the SQL fragment."""
        base = f"{self.col.info.fqn()} ASC"
        if self.nulls is not None:
            return f"{base} NULLS {self.nulls.upper()}"
        return base


class Desc(OrderByClause):
    """
    Represents a descending sort order for a column.

    ```python
    from embar.query.order_by import Desc
    from embar.column.base import ColumnBase, ColumnInfo

    col = ColumnBase()
    col.info = ColumnInfo(
        _table_name=lambda: "users",
        name="age",
        col_type="INTEGER",
        py_type=int,
        primary=False,
        not_null=False
    )
    desc = Desc(col, nulls="first")
    sql = desc.sql()
    assert sql == '"users"."age" DESC NULLS FIRST'
    ```
    """

    col: ColumnBase
    nulls: NullsOrdering | None

    def __init__(self, col: ColumnBase, nulls: NullsOrdering | None = None):
        """
        Create a descending sort order.

        Args:
            col: The column to sort by
            nulls: Optional nulls ordering ("first" or "last")
        """
        self.col = col
        self.nulls = nulls

    @override
    def sql(self) -> str:
        """Generate the SQL fragment."""
        base = f"{self.col.info.fqn()} DESC"
        if self.nulls is not None:
            return f"{base} NULLS {self.nulls.upper()}"
        return base


class BareColumn(OrderByClause):
    """
    Represents a bare column reference (defaults to ASC).

    This is used internally when a column is passed directly to order_by().

    ```python
    from embar.query.order_by import BareColumn
    from embar.column.base import ColumnBase, ColumnInfo

    col = ColumnBase()
    col.info = ColumnInfo(
        _table_name=lambda: "users",
        name="id",
        col_type="INTEGER",
        py_type=int,
        primary=False,
        not_null=False
    )
    bare = BareColumn(col)
    sql = bare.sql()
    assert sql == '"users"."id"'
    ```
    """

    col: ColumnBase

    def __init__(self, col: ColumnBase):
        """Create a bare column reference."""
        self.col = col

    @override
    def sql(self) -> str:
        """Generate the SQL fragment (just the column FQN)."""
        return self.col.info.fqn()


class RawSqlOrder(OrderByClause):
    """
    Represents raw SQL in an ORDER BY clause.

    ```python
    from embar.query.order_by import RawSqlOrder
    from embar.sql import Sql
    from embar.table import Table
    from embar.column.common import Integer

    class User(Table):
        id: Integer = Integer()

    raw = RawSqlOrder(Sql(t"{User.id} DESC"))
    sql = raw.sql()
    assert sql == '"user"."id" DESC'
    ```
    """

    sql_obj: Sql

    def __init__(self, sql_obj: Sql):
        """Create a raw SQL order clause."""
        self.sql_obj = sql_obj

    @override
    def sql(self) -> str:
        """Generate the SQL fragment."""
        return self.sql_obj.sql()


@dataclass
class OrderBy:
    """
    Represents an ORDER BY clause for sorting query results.

    ```python
    from embar.query.order_by import OrderBy, Asc, Desc, BareColumn
    from embar.column.base import ColumnBase, ColumnInfo

    col1 = ColumnBase()
    col1.info = ColumnInfo(
        _table_name=lambda: "users",
        name="age",
        col_type="INTEGER",
        py_type=int,
        primary=False,
        not_null=False
    )

    col2 = ColumnBase()
    col2.info = ColumnInfo(
        _table_name=lambda: "users",
        name="name",
        col_type="TEXT",
        py_type=str,
        primary=False,
        not_null=False
    )

    order = OrderBy((
        Desc(col1),
        Asc(col2, nulls="first"),
    ))
    sql = order.sql()
    assert sql == '"users"."age" DESC, "users"."name" ASC NULLS FIRST'
    ```
    """

    clauses: tuple[OrderByClause, ...]

    def sql(self) -> str:
        """
        Generate the full ORDER BY SQL clause.

        ```python
        from embar.query.order_by import OrderBy, Asc, BareColumn
        from embar.column.base import ColumnBase, ColumnInfo

        col1 = ColumnBase()
        col1.info = ColumnInfo(
            _table_name=lambda: "users",
            name="id",
            col_type="INTEGER",
            py_type=int,
            primary=False,
            not_null=False
        )

        col2 = ColumnBase()
        col2.info = ColumnInfo(
            _table_name=lambda: "users",
            name="name",
            col_type="TEXT",
            py_type=str,
            primary=False,
            not_null=False
        )

        order = OrderBy((BareColumn(col1), Asc(col2)))
        sql = order.sql()
        assert sql == '"users"."id", "users"."name" ASC'
        ```
        """
        return ", ".join(clause.sql() for clause in self.clauses)
