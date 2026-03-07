"""SQLite-specific column types."""

from embar.column.common import Column, Float, Integer, Text, float_col, integer, text
from embar.custom_types import Type

# SQLite is weird about column types...
__all__ = ["Blob", "Float", "Integer", "Text", "blob", "float_col", "integer", "text"]


class Blob(Column[bytes]):
    """
    Blob column type for storing binary data.
    """

    _sql_type: str = "BLOB"
    _py_type: Type = bytes


def blob(
    name: str | None = None,
    default: bytes | None = None,
    *,
    primary: bool = False,
    not_null: bool = False,
) -> Blob:
    """Create a :class:`Blob` column."""
    return Blob(name=name, default=default, primary=primary, not_null=not_null)
