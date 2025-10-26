from dataclasses import dataclass

from pudl.column_base import ColumnBase


@dataclass
class GroupBy:
    col: ColumnBase
