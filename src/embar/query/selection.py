from __future__ import annotations

from dataclasses import Field, dataclass, field, fields, make_dataclass
from typing import Annotated, Any, Literal, cast, get_args, get_origin, get_type_hints

from embar.column.base import ColumnBase
from embar.db.base import DbType
from embar.query.many import ManyColumn, ManyTable
from embar.sql import Sql
from embar.table_base import TableBase


@dataclass
class Selection:
    """
    `Selection` is the base class for [`Select`][embar.query.select.Select] queries.

    Example:
    >>> from embar.column.common import Text
    >>> from embar.table import Table
    >>> class MyTable(Table):
    ...     my_col: Text = Text()
    >>> @dataclass
    ... class MySelection(Selection):
    ...     my_col: [str, MyTable.my_col]
    >>>
    """

    @classmethod
    def to_sql_columns(cls, db_type: DbType) -> str:
        parts: list[str] = []
        hints = get_type_hints(cls, include_extras=True)
        for cls_field in fields(cls):
            source = _get_source_expr(hints, cls_field, db_type)
            target = cls_field.name
            parts.append(f'{source} AS "{target}"')

        return ", ".join(parts)


# `SelectAll` tells the query engine to get all fields from the `from()` table
# but currently (?) doesn't work (from a typing POV) with joined tables...
# TODO figure out if worth keeping even with that limitation
class SelectAll(Selection): ...


def _get_source_expr(hints: dict[str, Any], field: Field[Any], db_type: DbType) -> str:
    """
    Get the source expression for the given `Selection` field.

    It could be a simple column reference, a table or `Many` reference,
    or even a ['Sql'][embar.sql.Sql] query.
    """
    field_type = hints[field.name]
    if get_origin(field_type) is Annotated:
        annotations = get_args(field.type)
        # Skip first arg (the actual type), search metadata for TableColumn
        for annotation in annotations[1:]:
            if isinstance(annotation, ColumnBase):
                return annotation.info.fqn
            if isinstance(annotation, ManyColumn):
                # not sure why this cast is needed
                # pyright doesn't figure out the ManyColumn is always [ColumnBase]?
                many_col = cast(ManyColumn[ColumnBase], annotation)
                fqn = many_col.of.info.fqn
                match db_type:
                    case "postgres":
                        query = f"array_agg({fqn})"
                        return query
                    case "sqlite":
                        query = f"json_group_array({fqn})"
                        return query
            if isinstance(annotation, type) and issubclass(annotation, TableBase):
                table = annotation
                table_fqn = table.fqn()
                columns = table.column_names()
                column_pairs = ", ".join(
                    [f"'{field_name}', {table_fqn}.\"{col_name}\"" for field_name, col_name in columns.items()]
                )
                match db_type:
                    case "postgres":
                        query = f"json_build_object({column_pairs})"
                        return query
                    case "sqlite":
                        query = f"json_object({column_pairs})"
                        return query
            if isinstance(annotation, ManyTable):
                many_table = cast(ManyTable[type[TableBase]], annotation)
                table = many_table.of
                table_fqn = many_table.of.fqn()
                columns = table.column_names()
                column_pairs = ", ".join(
                    [f"'{field_name}', {table_fqn}.\"{col_name}\"" for field_name, col_name in columns.items()]
                )
                match db_type:
                    case "postgres":
                        query = f"json_agg(json_build_object({column_pairs}))"
                        return query
                    case "sqlite":
                        query = f"json_group_array(json_object({column_pairs}))"
                        return query
            if isinstance(annotation, Sql):
                query = annotation.execute()
                return query

    raise Exception(f"Failed to get source expression for {field.name}")


def convert_annotation(
    field: Field[Any],
) -> Annotated[Any, Any] | Literal[False]:
    """
    Extract complex annotated types from `Annotated[int, MyTable.my_col]` expressions.

    If the annotated type is a column reference then this does nothing and returns false.

    Only used by `embar.query.Select` but more at home here with the `Selection` context where it's used.

    Example:
    >>> from embar.column.common import Text
    >>> from embar.table import Table
    >>> class MyTable(Table):
    ...     my_col: Text = Text()
    >>> @dataclass
    ... class MySelection(Selection):
    ...     my_col: [str, MyTable.my_col]
    >>> field = fields(MySelection)[0]
    >>> convert_annotation(field)
    False
    """
    if get_origin(field.type) is Annotated:
        annotations = get_args(field.type)
        # Skip first arg (the actual type), search metadata for TableColumn
        for annotation in annotations[1:]:
            if isinstance(annotation, ManyTable):
                many_table = cast(ManyTable[type[TableBase]], annotation)
                inner_type = many_table.of
                dc = generate_selection_dataclass(inner_type)
                new_type = Annotated[list[dc], annotation]
                return new_type

            if isinstance(annotation, type) and issubclass(annotation, TableBase):
                dc = generate_selection_dataclass(annotation)
                return Annotated[dc, annotation]
    return False


def generate_selection_dataclass(cls: type[TableBase]) -> type[Selection]:
    """
    Create a dataclass subclass of `Selection` based on a `Table`.

    Note the new table has the same exact name, maybe something to revisit.

    Example:
    >>> from embar.table import Table
    >>> class MyTable(Table): ...
    >>> generate_selection_dataclass(MyTable)
    <class 'embar.query.selection.MyTable'>
    """
    fields: list[tuple[str, Annotated[Any, Any], Any]] = []
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if isinstance(attr, ColumnBase):
            column_type = attr._pytype  # pyright:ignore[reportPrivateUsage]
            fields.append(
                (
                    attr_name,
                    Annotated[column_type, attr],
                    field(default_factory=lambda a=attr: a.info.fqn),
                )
            )

    return make_dataclass(cls.__name__, fields, bases=(Selection,))
