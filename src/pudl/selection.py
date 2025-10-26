from __future__ import annotations

from dataclasses import Field, dataclass, field, fields, make_dataclass
from typing import Annotated, Any, Literal, cast, get_args, get_origin

from pudl.column_base import ManyColumn, ColumnBase
from pudl.table_base import ManyTable, TableBase


@dataclass
class Selection:
    @classmethod
    def to_sql_columns(cls) -> str:
        parts: list[str] = []
        for cls_field in fields(cls):
            source = _get_annotation(cls_field)
            target = cls_field.name
            parts.append(f'{source} AS "{target}"')

        return ", ".join(parts)


# TODO not sure it's possible to make this work
# (from a typing perspective)
# with joins...
class SelectAll(Selection): ...


def _get_annotation(field: Field[Any]) -> str:
    # Check if it's an Annotated type
    if get_origin(field.type) is Annotated:
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
                query = f"array_agg({fqn})"
                return query
            if isinstance(annotation, ManyTable):
                many_table = cast(ManyTable[type[TableBase]], annotation)
                fqn = many_table.of.fqn()
                query = f"json_agg(row_to_json({fqn}.*))"
                return query
    raise Exception(f"Failed to get column name for {field.name}")


def convert_annotation(
    field: Field[Any],
) -> Annotated[Any, Any] | Literal[False]:
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
