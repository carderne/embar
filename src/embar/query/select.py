from collections.abc import Sequence
from dataclasses import dataclass, field, make_dataclass
from typing import (
    Any,
    NoReturn,
    Self,
    overload,
)

from dacite import from_dict

from embar.column.base import ColumnBase
from embar.db.base import AllDbBase, AsyncDbBase, DbBase
from embar.query.group_by import GroupBy
from embar.query.join import JoinClause, LeftJoin
from embar.query.selection import (
    SelectAll,
    Selection,
    convert_annotation,
    generate_selection_dataclass,
)
from embar.query.where import WhereClause
from embar.table import Table


@dataclass
class SelectQuery[S: Selection, T: Table, Db: AllDbBase]:
    """
    `InsertQuery` is used to insert data into a table.

    It is generic over the `Selection` made, `Table` being inserted into, and the database being used.

    It has a regular `execute()` method, and an async `aexecute()` method.
    These are typed to return `NoReturn` when the wrong one is used, but there doesn't
    seem to be a way to make it an error to use them in the wrong case.

    `SelectQuery` is never used directly, but always returned by a [`Fromm`][embar.fromm.Fromm] instance.

    Example:
    >>> from embar.db.pg import Db
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

        selection = self._get_selection()

        data = self._db.fetch(sql, params)
        results = [from_dict(selection, d) for d in data]
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
        data_class = self._get_selection()
        data = await self._db.afetch(sql, params)
        results = [from_dict(data_class, d) for d in data]
        return results

    def _get_selection(self) -> type[Selection] | type[S]:
        """
        Generate the dataclass that will be used to deserialize (and validate) the query results.

        If Selection is `SelectAll`, we generate a dataclass based on the `Table`,
        otherwise the `Seletion` (already a dataclass)
        is used.

        Extra processing is done to check for nested children that are Tables themselves.
        """
        # TODO does this work for doubly nested stuff? Probably not.
        selection = generate_selection_dataclass(self.table) if self.sel is SelectAll else self.sel
        selection.__init_subclass__()

        new_fields: list[tuple[str, type]] = []
        for field_name, field_type in selection._fields.items():  # pyright:ignore[reportPrivateUsage]
            new_type = convert_annotation(field_type)
            if new_type:
                new_fields.append((field_name, new_type))
            else:
                # This means convert_annotation returned False, i.e. it's a 'simple' field.
                # We have to recreate it with a Field tuple to match the stuff above for the legitimately new fields.
                # (I haven't found a way for it to just be left in-place or something.)
                # field_type = cast(type, cls_field.type)
                new_fields.append((field_name, field_type))

        new_class = make_dataclass(selection.__name__, new_fields, bases=(Selection,))

        # Pretty gruesome stuf going on here...
        # __init_subclass__ won't have been called, so _fields won't have been assigned
        # so do it manually...
        new_class.__init_subclass__()

        return new_class

    def _build_sql(self) -> tuple[str, dict[str, Any]]:
        """
        Combine all the components of the query and build the SQL and bind parameters (psycopg format).
        """
        data_class = self._get_selection()
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
