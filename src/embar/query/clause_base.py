from abc import ABC, abstractmethod
from typing import Callable

from embar.query.query import QuerySingle

# Where clauses get passed a get_count() function that returns a monotonically
# increasing integer. This allows each SQL binding parameter to get a unique
# name like `%(eq_id_2)s` in psycopg format.
type GetCount = Callable[[], int]


class ClauseBase(ABC):
    """
    ABC for ORDER BY and WHERE clauses.

    Not all use the get_count() directly (those with no bindings)
    but their children might.
    """

    @abstractmethod
    def sql(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the SQL fragment for this clause.
        """
        ...
