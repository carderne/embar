from dataclasses import dataclass

from pudl.column.base import ColumnBase


@dataclass
class GroupBy:
    # TODO allow more complex group_by
    col: ColumnBase
