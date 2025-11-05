"""SQLite-specific column types."""

from embar.column.common import Column, Float, Integer, Text
from embar.custom_types import Type

# SQLite is weird about column types...
__all__ = ["Blob", "Float", "Integer", "Text"]


class Blob(Column[bytes]):
    """
    Blob column type for storing binary data.
    """

    _sql_type: str = "BLOB"
    _py_type: Type = bytes
