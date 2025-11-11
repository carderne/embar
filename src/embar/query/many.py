"""Types for nesting arrays in queries."""

from dataclasses import dataclass

from embar.column.base import ColumnBase
from embar.table_base import TableBase


@dataclass
class ManyTable[T: type[TableBase]]:
    """
    Used to nest arrays of entire tables.
    """

    of: T


@dataclass
class OneTable[T: type[TableBase]]:
    """
    Used to nest arrays of entire tables.
    """

    of: T


@dataclass
class ManyColumn[T: ColumnBase]:
    """
    Used to nest arrays of column results.
    """

    of: T
