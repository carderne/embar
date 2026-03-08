"""SQLite-specific column types."""

from typing import TypeAlias, overload

from embar.column.common import Column, Float, Integer, Null, Text, float_col, integer, text
from embar.custom_types import NO_DEFAULT, Type, _NoDefaultType

# SQLite is weird about column types...
__all__ = ["Blob", "Float", "Integer", "Null", "NullBlob", "Text", "blob", "float_col", "integer", "text"]

NullBlob: TypeAlias = Null[bytes]


class Blob(Column[bytes]):
    """
    Blob column type for storing binary data.
    """

    _sql_type: str = "BLOB"
    _py_type: Type = bytes


@overload
def blob(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Blob: ...


@overload
def blob(
    name: str | None = ...,
    *,
    default: bytes,
    primary: bool = ...,
    not_null: bool = ...,
) -> Blob: ...


@overload
def blob(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> NullBlob: ...


def blob(
    name: str | None = None,
    *,
    default: bytes | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Blob | NullBlob:
    """Create a :class:`Blob` column."""
    if default is None:
        return Null[bytes](
            sql_type="BLOB", py_type=bytes, name=name, default=default, primary=primary, not_null=not_null
        )
    return Blob(name=name, default=default, primary=primary, not_null=not_null)
