from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, fields, make_dataclass
from typing import (
    Any,
    NoReturn,
    Self,
    cast,
    overload,
)

from dacite import from_dict

from pudl.column.base import ColumnBase
from pudl.db.base import AllDbBase, AsyncDbBase, DbBase
from pudl.query.group_by import GroupBy
from pudl.query.join import JoinClause, LeftJoin
from pudl.query.selection import (
    SelectAll,
    Selection,
    convert_annotation,
    generate_selection_dataclass,
)
from pudl.query.where import WhereClause
from pudl.table import Table


@dataclass
class SelectQuery[S: Selection, T: Table, Db: AllDbBase]:
    """
    `InsertQuery` is used to insert data into a table.

    It is generic over the `Selection` made, `Table` being inserted into, and the database being used.

    It has a regular `execute()` method, and an async `aexecute()` method.
    These are typed to return `NoReturn` when the wrong one is used, but there doesn't
    seem to be a way to make it an error to use them in the wrong case.

    `SelectQuery` is never used directly, but always returned by a [`Fromm`][pudl.fromm.Fromm] instance.

    Example:
    >>> from pudl.db.pg import Db
    >>> db = Db(None)
    >>> select = db.select(None).fromm(None)
    >>> assert isinstance(select, SelectQuery)
    """

    _db: Db
    table: type[T]
    sel: type[S]

    _joins: list[JoinClause] = field(default_factory=list)
    _where_clause: WhereClause | None = None
    _group_clause: GroupBy | None = None
    _limit_value: int | None = None

    def left_join(self, table: type[Table], on: WhereClause) -> Self:
        self._joins.append(LeftJoin(table, on))
        return self

    def where(self, where_clause: WhereClause) -> Self:
        self._where_clause = where_clause
        return self

    def group_by(self, col: ColumnBase) -> Self:
        self._group_clause = GroupBy(col)
        return self

    def limit(self, n: int) -> Self:
        self._limit_value = n
        return self

    @overload
    def execute(self: SelectQuery[SelectAll, T, DbBase]) -> list[T]: ...

    @overload
    def execute(self: SelectQuery[S, T, DbBase]) -> list[S]: ...

    @overload
    def execute(self: SelectQuery[SelectAll, T, AsyncDbBase]) -> NoReturn: ...

    @overload
    def execute(self: SelectQuery[S, T, AsyncDbBase]) -> NoReturn: ...

    def execute(self) -> Sequence[Selection | T]:
        """
        execute the query against the underlying db.

        The overrides provide for a few different cases:
        - A subclass of `Selection` was passed, in which case that's the return type
        - `SelectAll` was passed, in which case the return type is the `Table`
        - This is called with an async db, in which case an error is returnd.

        Results are currently (?) parsed with dacite.
        """
        if not isinstance(self._db, DbBase):
            raise Exception("You need to use 'await ...aexecute()' here!")

        sql, params = self._build_sql()

        data_class = self._get_dataclass()

        data = self._db.fetch(sql, params)
        results = [from_dict(data_class, d) for d in data]
        return results

    @overload
    async def aexecute(self: SelectQuery[SelectAll, T, DbBase]) -> NoReturn: ...

    @overload
    async def aexecute(self: SelectQuery[S, T, DbBase]) -> NoReturn: ...

    @overload
    async def aexecute(self: SelectQuery[SelectAll, T, AsyncDbBase]) -> list[T]: ...

    @overload
    async def aexecute(self: SelectQuery[S, T, AsyncDbBase]) -> list[S]: ...

    async def aexecute(self) -> Sequence[Selection | T]:
        """
        execute the query against the underlying (async) db.

        The overrides provide for a few different cases:
        - A subclass of `Selection` was passed, in which case that's the return type
        - `SelectAll` was passed, in which case the return type is the `Table`
        - This is called with a non-async db, in which case an error is returnd.

        Results are currently (?) parsed with dacite.
        """
        if not isinstance(self._db, AsyncDbBase):
            raise Exception("You need to use '...execute()' here (not 'aexecute()')")

        sql, params = self._build_sql()
        data_class = self._get_dataclass()
        data = await self._db.afetch(sql, params)
        results = [from_dict(data_class, d) for d in data]
        return results

    def _get_dataclass(self) -> type[Selection] | type[S]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.

        If Selection is `SelectAll`, we generate a dataclass based on the `Table`,
        otherwise the `Seletion` (already a dataclass)
        is used.

        Extra processing is done to check for nested children that are Tables themselves.
        """
        # TODO does this work for doubly nested stuff? Probably not.
        data_class = generate_selection_dataclass(self.table) if self.sel is SelectAll else self.sel

        new_fields: list[tuple[str, type, Any]] = []
        for cls_field in fields(data_class):
            new_type = convert_annotation(cls_field)
            if new_type:
                new_fields.append((cls_field.name, new_type, cls_field))
            else:
                # This means convert_annotation returned False, i.e. it's a 'simple' field.
                # We have to recreate it with a Field tuple to match the stuff above for the legitimately new fields.
                # (I haven't found a way for it to just be left in-place or something.)
                field_type = cast(type, cls_field.type)
                new_fields.append((cls_field.name, field_type, cls_field))

        new_class = make_dataclass(data_class.__name__, new_fields, bases=(Selection,))
        return new_class

    def _build_sql(self) -> tuple[str, dict[str, Any]]:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """
        data_class = self._get_dataclass()
        selection = data_class.to_sql_columns(self._db.db_type)

        sql = f"SELECT {selection} FROM {self.table.fqn()}"

        count = -1

        def get_count() -> int:
            nonlocal count
            count += 1
            return count

        params: dict[str, Any] = {}

        for join in self._joins:
            join_data = join.get(get_count)
            sql += join_data.sql
            params = {**params, **join_data.params}

        if self._where_clause is not None:
            where_data = self._where_clause.get(get_count)
            sql += f" WHERE {where_data.sql} "
            params = {**params, **where_data.params}

        if self._group_clause is not None:
            group_by_col = self._group_clause.col.info.fqn
            sql += f" GROUP BY {group_by_col} "

        if self._limit_value is not None:
            sql += f" LIMIT {self._limit_value}"

        return sql, params
