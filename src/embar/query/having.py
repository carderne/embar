"""Having clause for filtering grouped queries."""

from dataclasses import dataclass

from embar.query.clause_base import ClauseBase


@dataclass
class Having:
    """
    Represents a HAVING clause for filtering aggregated/grouped results.

    HAVING clauses are similar to WHERE clauses but operate on grouped/aggregated data.
    They are typically used with GROUP BY to filter groups based on aggregate conditions.

    ```python
    from embar.query.having import Having
    from embar.query.where import Gt
    from embar.column.base import ColumnBase, ColumnInfo

    # Example: HAVING COUNT(*) > 5
    count_col = ColumnBase()
    count_col.info = ColumnInfo(
        _table_name=lambda: "users",
        name="count",
        col_type="INTEGER",
        py_type=int,
        primary=False,
        not_null=False
    )
    having = Having(Gt(count_col, 5))
    ```
    """

    clause: ClauseBase
