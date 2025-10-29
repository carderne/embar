from dataclasses import dataclass

from embar.column.base import ColumnBase


@dataclass
class GroupBy:
    # TODO allow more complex group_by
    col: ColumnBase
