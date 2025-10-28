from dataclasses import dataclass

from pudl.db.base import AllDbBase
from pudl.query.select import SelectQuery
from pudl.query.selection import Selection
from pudl.table import Table


@dataclass
class Fromm[S: Selection, Db: AllDbBase]:
    """
    `Fromm` is returned by Db.select and exposes one method that produced the `SelectQuery`.

    The extra "m" is because `from` is a reserved keyword.
    """

    _db: Db
    sel: type[S]

    def fromm[T: Table](self, table: type[T]) -> SelectQuery[S, T, Db]:
        return SelectQuery[S, T, Db](sel=self.sel, table=table, _db=self._db)
