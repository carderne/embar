from __future__ import annotations

from dataclasses import Field, dataclass, fields
from typing import Annotated, Any, get_args, get_origin

from pudl.column_base import ColumnBase


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
                # Found it - call your method
                return annotation.info.fqn
    raise Exception(f"Failed to get column name for {field.name}")
