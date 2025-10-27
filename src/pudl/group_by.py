from dataclasses import dataclass

from pudl.column.base import ColumnBase


@dataclass
class GroupBy:
    col: ColumnBase
