from dataclasses import dataclass

from embar.db.base import AllDbBase
from embar.query.select import SelectQuery
from embar.query.selection import Selection
from embar.table import Table


@dataclass
class Fromm[S: Selection, Db: AllDbBase]:
    """
    `Fromm` is returned by Db.select and exposes one method that produced the `SelectQuery`.

    The extra "m" is because `from` is a reserved keyword.
    """

    _db: Db
    sel: type[S]

    def fromm[T: Table](self, table: type[T]) -> SelectQuery[S, T, Db]:
        return SelectQuery[S, T, Db](sel=self.sel, table=table, db=self._db)
