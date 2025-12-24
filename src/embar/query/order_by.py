"""Order by clause for sorting query results."""

from dataclasses import dataclass
from typing import Literal, override

from embar.column.base import ColumnBase
from embar.custom_types import PyType
from embar.query.clause_base import ClauseBase, GetCount
from embar.query.query import QuerySingle
from embar.sql import Sql

type NullsOrdering = Literal["first", "last"]


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
    sql = order.sql(lambda: 0)
    print(sql)
    assert sql.sql == '"users"."age" DESC, "users"."name" ASC NULLS FIRST'
    ```
    """

    clauses: tuple[ClauseBase, ...]

    def sql(self, get_count: GetCount) -> QuerySingle:
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
        sql = order.sql(lambda: 0)
        assert sql.sql == '"users"."id", "users"."name" ASC'
        ```
        """

        queries = [clause.sql(get_count) for clause in self.clauses]
        params = {k: v for d in queries for k, v in d.params.items()}

        sql = ", ".join(q.sql for q in queries)
        return QuerySingle(sql=sql, params=params)


def _asc_or_desc_sql(
    clause: ColumnBase | ClauseBase,
    nulls: NullsOrdering | None,
    asc: bool,
    get_count: GetCount,
) -> QuerySingle:
    """Generate the SQL fragment."""
    params: dict[str, PyType] = {}
    direction = "ASC" if asc else "DESC"
    if isinstance(clause, ColumnBase):
        sql = f"{clause.info.fqn()} {direction}"
    else:
        query = clause.sql(get_count)
        sql = f"{query.sql} {direction}"
        params = query.params

    if nulls is not None:
        return QuerySingle(sql=f"{sql} NULLS {nulls.upper()}", params=params)
    return QuerySingle(sql=sql, params=params)


class Asc(ClauseBase):
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
    sql = asc.sql(lambda: 0)
    assert sql.sql == '"users"."age" ASC NULLS LAST'
    ```
    """

    clause: ColumnBase | ClauseBase
    nulls: NullsOrdering | None

    def __init__(self, clause: ColumnBase | ClauseBase, nulls: NullsOrdering | None = None):
        """
        Create an ascending sort order.

        Args:
            col: The column to sort by
            nulls: Optional nulls ordering ("first" or "last")
        """
        self.clause = clause
        self.nulls = nulls

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        """Generate the SQL fragment."""
        return _asc_or_desc_sql(
            self.clause,
            self.nulls,
            True,
            get_count,
        )


class Desc(ClauseBase):
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
    sql = desc.sql(lambda: 0)
    assert sql.sql == '"users"."age" DESC NULLS FIRST'
    ```
    """

    clause: ColumnBase | ClauseBase
    nulls: NullsOrdering | None

    def __init__(self, clause: ColumnBase | ClauseBase, nulls: NullsOrdering | None = None):
        """
        Create a descending sort order.

        Args:
            col: The column to sort by
            nulls: Optional nulls ordering ("first" or "last")
        """
        self.clause = clause
        self.nulls = nulls

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        """Generate the SQL fragment."""
        return _asc_or_desc_sql(
            self.clause,
            self.nulls,
            False,
            get_count,
        )


class BareColumn(ClauseBase):
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
    sql = bare.sql(lambda: 0)
    assert sql.sql == '"users"."id"'
    ```
    """

    col: ColumnBase

    def __init__(self, col: ColumnBase):
        """Create a bare column reference."""
        self.col = col

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        """Generate the SQL fragment (just the column FQN)."""
        return QuerySingle(sql=self.col.info.fqn(), params=None)


class RawSqlOrder(ClauseBase):
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
    sql = raw.sql(lambda: 0)
    assert sql.sql == '"user"."id" DESC'
    ```
    """

    sql_obj: Sql

    def __init__(self, sql_obj: Sql):
        """Create a raw SQL order clause."""
        self.sql_obj = sql_obj

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        """Generate the SQL fragment."""
        return QuerySingle(sql=self.sql_obj.sql(), params=None)
