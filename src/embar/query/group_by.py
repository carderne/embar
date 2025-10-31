from dataclasses import dataclass

from embar.column.base import ColumnBase


@dataclass
class GroupBy:
    cols: tuple[ColumnBase, ...]
