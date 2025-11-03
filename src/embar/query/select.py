from collections.abc import Generator, Sequence
from textwrap import dedent
from typing import Any, Self, cast, overload

from dacite import from_dict

from embar.column.base import ColumnBase
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.group_by import GroupBy
from embar.query.join import CrossJoin, FullJoin, InnerJoin, JoinClause, LeftJoin, RightJoin
from embar.query.query import Query
from embar.query.selection import (
    SelectAll,
    Selection,
    generate_selection_dataclass,
    selection_to_dataclass,
)
from embar.query.where import WhereClause
from embar.table import Table


class SelectQuery[S: Selection, Db: AllDbBase]:
    """
    `SelectQuery` is returned by Db.select and exposes one method that produced the `SelectQueryReady`.
    """

    _db: Db
    sel: type[S]

    def __init__(self, sel: type[S], db: Db):
        self.sel = sel
        self._db = db

    def fromm[T: Table](self, table: type[T]) -> SelectQueryReady[S, T, Db]:
        """
        The silly name is because `from` is a reserved keyword.
        """
        return SelectQueryReady[S, T, Db](sel=self.sel, table=table, db=self._db)


class SelectQueryReady[S: Selection, T: Table, Db: AllDbBase]:
    """
    `SelectQueryReady` is used to insert data into a table.

    It is generic over the `Selection` made, `Table` being inserted into, and the database being used.

    `SelectQueryReady` is returned by [`fromm`][embar.query.select.SelectQuery.fromm].

    ```python
    from embar.db.pg import Db
    from embar.query.select import SelectQueryReady
    db = Db(None)
    select = db.select(None).fromm(None)
    assert isinstance(select, SelectQueryReady)
    ```
    """

    sel: type[S]
    table: type[T]
    _db: Db

    _joins: list[JoinClause]
    _where_clause: WhereClause | None = None
    _group_clause: GroupBy | None = None
    _limit_value: int | None = None

    def __init__(self, sel: type[S], table: type[T], db: Db):
        self.sel = sel
        self.table = table
        self._db = db
        self._joins = []

    def left_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(LeftJoin(table, on))
        return self

    def right_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(RightJoin(table, on))
        return self

    def inner_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(InnerJoin(table, on))
        return self

    def full_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(FullJoin(table, on))
        return self

    def cross_join(self, table: type[Table]) -> Self:
        self._joins.append(CrossJoin(table))
        return self

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    def group_by(self, *cols: ColumnBase) -> Self:
        self._group_clause = GroupBy(cols)
        return self

    def limit(self, n: int) -> Self:
        self._limit_value = n
        return self

    @overload
    def __await__(self: SelectQueryReady[SelectAll, T, Db]) -> Generator[Any, None, Sequence[T]]: ...
    @overload
    def __await__(self: SelectQueryReady[S, T, Db]) -> Generator[Any, None, Sequence[S]]: ...

    def __await__(self) -> Generator[Any, None, Sequence[T | S]]:
        """
        Async users should construct their query and await it.

        Non-async users have the `run()` convenience method below.
        But this method will still work if called in an async context against a non-async db.

        The overrides provide for a few different cases:
        - A subclass of `Selection` was passed, in which case that's the return type
        - `SelectAll` was passed, in which case the return type is the `Table`
        - This is called with an async db, in which case an error is returned.

        Results are currently (?) parsed with dacite.
        """
        query = self.sql()
        selection = self._get_selection()
        selection = cast(type[T] | type[S], selection)

        async def awaitable():
            db = self._db
            if isinstance(db, AsyncDbBase):
                data = await db.fetch(query)
            else:
                db = cast(DbBase, self._db)
                data = db.fetch(query)
            results = [from_dict(selection, d) for d in data]
            return results

        return awaitable().__await__()

    @overload
    def run(self: SelectQueryReady[SelectAll, T, DbBase]) -> Sequence[T]: ...
    @overload
    def run(self: SelectQueryReady[S, T, DbBase]) -> Sequence[S]: ...
    @overload
    def run(self: SelectQueryReady[S, T, AsyncDbBase]) -> SelectQueryReady[S, T, Db]: ...

    def run(self) -> Sequence[S | T] | SelectQueryReady[S, T, Db]:
        if isinstance(self._db, DbBase):
            query = self.sql()
            selection = self._get_selection()
            selection = cast(type[T] | type[S], selection)
            data = self._db.fetch(query)
            results = [from_dict(selection, d) for d in data]
            return results
        return self

    def _get_selection(self) -> type[Selection] | type[S]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.

        If Selection is `SelectAll`, we generate a dataclass based on the `Table`,
        otherwise the `Seletion` (already a dataclass)
        is used.

        Extra processing is done to check for nested children that are Tables themselves.
        """
        selection = generate_selection_dataclass(self.table) if self.sel is SelectAll else self.sel
        return selection_to_dataclass(selection)

    def sql(self) -> Query:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """
        data_class = self._get_selection()
        selection = data_class.to_sql_columns(self._db.db_type)

        sql = f"""
        SELECT {selection}
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

        if self._limit_value is not None:
            sql += f"\nLIMIT {self._limit_value}"

        sql = sql.strip()

        return Query(sql, params)
