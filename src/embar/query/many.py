from dataclasses import dataclass

from embar.column.base import ColumnBase
from embar.table_base import TableBase


@dataclass
class ManyTable[T: type[TableBase]]:
    """
    Used in Selection classes to nest arrays of entire tables.
    """

    of: T


@dataclass
class ManyColumn[T: ColumnBase]:
    """
    Used in Selection classes to nest arrays of column results.
    """

    of: T
