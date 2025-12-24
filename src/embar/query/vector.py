"""
Code specific to the pgvector extension.

The base vector column is still defined in embar.column.pg
"""

from typing import override

from embar.column.base import ColumnInfo
from embar.column.common import Column
from embar.query.clause_base import ClauseBase, GetCount
from embar.query.query import QuerySingle


class L2Distance(ClauseBase):
    """
    Get the L2 Distance using pgvector.

    Assumes pgvector extension is installed and activated.

    Creates a query like col_a <-> '[1,2,3]' or col_a <-> col_b.
    """

    left: ColumnInfo
    right: list[float] | ColumnInfo

    def __init__(self, left: Column[list[float]], right: list[float] | Column[list[float]]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"l2distance_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return QuerySingle(sql=f"{self.left.fqn()} <-> {self.right.fqn()}")

        # pgvector expects an argument of the form '[1,2,3]'
        stringified = str(self.right).replace(" ", "")

        return QuerySingle(sql=f"{self.left.fqn()} <-> %({name})s", params={name: stringified})


class CosineDistance(ClauseBase):
    """
    Get the Cosine Distance using pgvector.

    Assumes pgvector extension is installed and activated.

    Creates a query like col_a <=> '[1,2,3]' or col_a <=> col_b.
    """

    left: ColumnInfo
    right: list[float] | ColumnInfo

    def __init__(self, left: Column[list[float]], right: list[float] | Column[list[float]]):
        self.left = left.info
        self.right = right.info if isinstance(right, Column) else right

    @override
    def sql(self, get_count: GetCount) -> QuerySingle:
        count = get_count()
        name = f"l2distance_{self.left.name}_{count}"
        if isinstance(self.right, ColumnInfo):
            return QuerySingle(sql=f"{self.left.fqn()} <=> {self.right.fqn()}")

        # pgvector expects an argument of the form '[1,2,3]'
        stringified = str(self.right).replace(" ", "")

        return QuerySingle(sql=f"{self.left.fqn()} <=> %({name})s", params={name: stringified})
