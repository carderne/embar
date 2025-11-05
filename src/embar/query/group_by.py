"""Group by clause for queries."""

from dataclasses import dataclass

from embar.column.base import ColumnBase


@dataclass
class GroupBy:
    """
    Represents a GROUP BY clause for queries.
    """

    cols: tuple[ColumnBase, ...]
