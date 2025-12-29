"""Select query builder."""

from collections.abc import Generator, Sequence
from textwrap import dedent
from typing import Any, Self, cast, overload
from warnings import deprecated

from pydantic import BaseModel, TypeAdapter

from embar.column.base import ColumnBase
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.model import (
    SelectAll,
    generate_model,
    to_sql_columns,
    upgrade_model_nested_fields,
)
from embar.query.clause_base import ClauseBase
from embar.query.group_by import GroupBy
from embar.query.having import Having
from embar.query.join import CrossJoin, FullJoin, InnerJoin, JoinClause, LeftJoin, RightJoin
from embar.query.order_by import Asc, BareColumn, Desc, OrderBy, RawSqlOrder
from embar.query.query import QuerySingle
from embar.sql import Sql
from embar.table import Table


class SelectQuery[M: BaseModel, Db: AllDbBase]:
    """
    `SelectQuery` is returned by Db.select and exposes one method that produced the `SelectQueryReady`.
    """

    _db: Db
    model: type[M]

    def __init__(self, model: type[M], db: Db):
        """
        Create a new SelectQuery instance.
        """
        self.model = model
        self._db = db

    @deprecated("Use from_ instead")
    def fromm[T: Table](self, table: type[T]) -> SelectQueryReady[M, T, Db]:
        """
        The silly name is because `from` is a reserved keyword.
        """
        return SelectQueryReady[M, T, Db](model=self.model, table=table, db=self._db, distinct=False)

    def from_[T: Table](self, table: type[T]) -> SelectQueryReady[M, T, Db]:
        """
        The underscore is because `from` is a reserved keyword.
        """
        return SelectQueryReady[M, T, Db](model=self.model, table=table, db=self._db, distinct=False)


class SelectDistinctQuery[M: BaseModel, Db: AllDbBase]:
    """
    `SelectDistinctQuery` is returned by Db.select and exposes one method that produced the `SelectQueryReady`.

    The only difference is that `distinct=True` is passed.
    """

    _db: Db
    model: type[M]

    def __init__(self, model: type[M], db: Db):
        """
        Create a new SelectQuery instance.
        """
        self.model = model
        self._db = db

    @deprecated("Use from_ instead")
    def fromm[T: Table](self, table: type[T]) -> SelectQueryReady[M, T, Db]:
        """
        The silly name is because `from` is a reserved keyword.
        """
        return SelectQueryReady[M, T, Db](model=self.model, table=table, db=self._db, distinct=True)

    def from_[T: Table](self, table: type[T]) -> SelectQueryReady[M, T, Db]:
        """
        The underscore is because `from` is a reserved keyword.
        """
        return SelectQueryReady[M, T, Db](model=self.model, table=table, db=self._db, distinct=True)


class SelectQueryReady[M: BaseModel, T: Table, Db: AllDbBase]:
    """
    `SelectQueryReady` is used to insert data into a table.

    It is generic over the `Model` made, `Table` being inserted into, and the database being used.

    `SelectQueryReady` is returned by [`from_`][embar.query.select.SelectQuery.from_].

    ```python
    from embar.db.pg import PgDb
    from embar.query.select import SelectQueryReady
    db = PgDb(None)
    select = db.select(None).from_(None)
    assert isinstance(select, SelectQueryReady)
    ```
    """

    model: type[M]
    table: type[T]
    _db: Db

    _distinct: bool
    _joins: list[JoinClause]
    _where_clause: ClauseBase | None = None
    _group_clause: GroupBy | None = None
    _having_clause: Having | None = None
    _order_clause: OrderBy | None = None
    _limit_value: int | None = None
    _offset_value: int | None = None

    def __init__(self, model: type[M], table: type[T], db: Db, distinct: bool):
        """
        Create a new SelectQueryReady instance.
        """
        self.model = model
        self.table = table
        self._db = db
        self._distinct = distinct
        self._joins = []

    def left_join(self, table: type[Table], on: ClauseBase) -> Self:
        """
        Add a LEFT JOIN clause to the query.
        """
        self._joins.append(LeftJoin(table, on))
        return self

    def right_join(self, table: type[Table], on: ClauseBase) -> Self:
        """
        Add a RIGHT JOIN clause to the query.
        """
        self._joins.append(RightJoin(table, on))
        return self

    def inner_join(self, table: type[Table], on: ClauseBase) -> Self:
        """
        Add an INNER JOIN clause to the query.
        """
        self._joins.append(InnerJoin(table, on))
        return self

    def full_join(self, table: type[Table], on: ClauseBase) -> Self:
        """
        Add a FULL OUTER JOIN clause to the query.
        """
        self._joins.append(FullJoin(table, on))
        return self

    def cross_join(self, table: type[Table]) -> Self:
        """
        Add a CROSS JOIN clause to the query.
        """
        self._joins.append(CrossJoin(table))
        return self

    def where(self, where_clause: ClauseBase) -> Self:
        """
        Add a WHERE clause to the query.
        """
        self._where_clause = where_clause
        return self

    def group_by(self, *cols: ColumnBase) -> Self:
        """
        Add a GROUP BY clause to the query.
        """
        self._group_clause = GroupBy(cols)
        return self

    def having(self, clause: ClauseBase) -> Self:
        """
        Add a HAVING clause to filter grouped/aggregated results.

        HAVING clauses work like WHERE clauses but operate on grouped data.
        They are typically used with GROUP BY to filter groups based on aggregate conditions.

        ```python
        from embar.db.pg import PgDb
        from embar.table import Table
        from embar.column.common import Integer, Text
        from embar.query.where import Gt

        class User(Table):
            id: Integer = Integer(primary=True)
            age: Integer = Integer()
            name: Text = Text()

        db = PgDb(None)

        # SELECT * FROM users GROUP BY age HAVING COUNT(*) > 5
        query = db.select(User.all()).from_(User).group_by(User.age).having(Gt(User.age, 18))
        sql_result = query.sql()
        assert "HAVING" in sql_result.sql
        ```
        """
        self._having_clause = Having(clause)
        return self

    def order_by(self, *clauses: ColumnBase | Asc | Desc | ClauseBase | Sql) -> Self:
        """
        Add an ORDER BY clause to sort query results.

        Accepts multiple ordering clauses:
        - Bare column references (defaults to ASC): `User.id`
        - `Asc(User.id)` or `Asc(User.id, nulls="last")`
        - `Desc(User.id)` or `Desc(User.id, nulls="first")`
        - Raw SQL: `Sql(t"{User.id} DESC")`

        Can be called multiple times to add more sort columns.

        ```python
        from embar.db.pg import PgDb
        from embar.table import Table
        from embar.column.common import Integer, Text
        from embar.query.order_by import Asc, Desc
        from embar.sql import Sql

        class User(Table):
            id: Integer = Integer(primary=True)
            age: Integer = Integer()
            name: Text = Text()

        db = PgDb(None)

        # Multiple ways to specify ORDER BY
        query = db.select(User.all()).from_(User).order_by(User.age, Desc(User.name))
        sql_result = query.sql()
        assert "ORDER BY" in sql_result.sql

        # With nulls handling
        query2 = db.select(User.all()).from_(User).order_by(Asc(User.age, nulls="last"))
        sql_result2 = query2.sql()
        assert "NULLS LAST" in sql_result2.sql

        # With raw SQL
        query3 = db.select(User.all()).from_(User).order_by(Sql(t"{User.id} DESC"))
        sql_result3 = query3.sql()
        assert "ORDER BY" in sql_result3.sql
        ```
        """
        # Convert each clause to an OrderByClause
        order_clauses: list[ClauseBase] = []
        for clause in clauses:
            if isinstance(clause, (Asc, Desc)):
                order_clauses.append(clause)
            elif isinstance(clause, Sql):
                order_clauses.append(RawSqlOrder(clause))
            elif isinstance(clause, ClauseBase):
                order_clauses.append(clause)
            else:
                order_clauses.append(BareColumn(clause))

        if self._order_clause is None:
            self._order_clause = OrderBy(tuple(order_clauses))
        else:
            # Add to existing ORDER BY clauses
            self._order_clause = OrderBy((*self._order_clause.clauses, *order_clauses))

        return self

    def limit(self, n: int) -> Self:
        """
        Add a LIMIT clause to the query.
        """
        self._limit_value = n
        return self

    def offset(self, n: int) -> Self:
        """
        Add an OFFSET clause to skip a number of rows.

        Typically used with LIMIT for pagination.

        ```python
        from embar.db.pg import PgDb
        from embar.table import Table
        from embar.column.common import Integer, Text

        class User(Table):
            id: Integer = Integer(primary=True)
            age: Integer = Integer()
            name: Text = Text()

        db = PgDb(None)

        # SELECT * FROM users LIMIT 10 OFFSET 20
        query = db.select(User.all()).from_(User).limit(10).offset(20)
        sql_result = query.sql()
        assert "LIMIT 10" in sql_result.sql
        assert "OFFSET 20" in sql_result.sql
        ```
        """
        self._offset_value = n
        return self

    @overload
    def __await__(self: SelectQueryReady[SelectAll, T, Db]) -> Generator[Any, None, Sequence[T]]: ...
    @overload
    def __await__(self: SelectQueryReady[M, T, Db]) -> Generator[Any, None, Sequence[M]]: ...

    def __await__(self) -> Generator[Any, None, Sequence[T | M]]:
        """
        Async users should construct their query and await it.

        Non-async users have the `run()` convenience method below.
        But this method will still work if called in an async context against a non-async db.

        The overrides provide for a few different cases:
        - A Model was passed, in which case that's the return type
        - `SelectAll` was passed, in which case the return type is the `Table`
        - This is called with an async db, in which case an error is returned.
        """
        query = self.sql()
        model = self._get_model()
        model = cast(type[T] | type[M], model)
        adapter = TypeAdapter(list[model])

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                data = await db.fetch(query)
            else:
                db = cast(DbBase, self._db)
                data = db.fetch(query)
            results = adapter.validate_python(data)
            return results

        return awaitable().__await__()

    @overload
    def run(self: SelectQueryReady[SelectAll, T, DbBase]) -> Sequence[T]: ...
    @overload
    def run(self: SelectQueryReady[M, T, DbBase]) -> Sequence[M]: ...
    @overload
    def run(self: SelectQueryReady[M, T, AsyncDbBase]) -> SelectQueryReady[M, T, Db]: ...

    def run(self) -> Sequence[M | T] | SelectQueryReady[M, T, Db]:
        """
        Run the query against the underlying DB.

        Convenience method for those not using async.
        But still works if awaited.
        """
        if isinstance(self._db, DbBase):
            query = self.sql()
            model = self._get_model()
            model = cast(type[T] | type[M], model)
            adapter = TypeAdapter(list[model])
            data = self._db.fetch(query)
            results = adapter.validate_python(data)
            return results
        return self

    def _get_model(self) -> type[BaseModel] | type[M]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.

        If the model is `SelectAll`, we generate a dataclass based on the `Table`,
        otherwise the model itself
        is used.

        Extra processing is done to check for nested children that are Tables themselves.
        """
        model = generate_model(self.table) if self.model is SelectAll else self.model
        upgraded = upgrade_model_nested_fields(model)
        return upgraded

    def sql(self) -> QuerySingle:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """
        data_class = self._get_model()

        columns = to_sql_columns(data_class, self._db.db_type)

        distinct = "DISTINCT" if self._distinct else ""

        sql = f"""
        SELECT {distinct} {columns}
        FROM {self.table.fqn()}
        """
        sql = dedent(sql).strip()

        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        for join in self._joins:
            join_data = join.get(get_count)
            sql += f"\n{join_data.sql}"
            params = {**params, **join_data.params}

        if self._where_clause is not None:
            where_data = self._where_clause.sql(get_count)
            sql += f"\nWHERE {where_data.sql}"
            params = {**params, **where_data.params}

        if self._group_clause is not None:
            col_names = [c.info.fqn() for c in self._group_clause.cols]
            group_by_col = ", ".join(col_names)
            sql += f"\nGROUP BY {group_by_col}"

        if self._having_clause is not None:
            having_data = self._having_clause.clause.sql(get_count)
            sql += f"\nHAVING {having_data.sql}"
            params = {**params, **having_data.params}

        if self._order_clause is not None:
            order_by_query = self._order_clause.sql(get_count)
            sql += f"\nORDER BY {order_by_query.sql}"
            params = {**params, **order_by_query.params}

        if self._limit_value is not None:
            sql += f"\nLIMIT {self._limit_value}"

        if self._offset_value is not None:
            sql += f"\nOFFSET {self._offset_value}"

        sql = sql.strip()

        return QuerySingle(sql, params=params)
