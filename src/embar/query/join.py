from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

from embar.query.where import GetCount, WhereClause, WhereData
from embar.table import Table


class JoinClause(ABC):
    @abstractmethod
    def get(self, get_count: GetCount) -> WhereData: ...


# TODO add more join types


@dataclass
class LeftJoin(JoinClause):
    table: type[Table]
    on: WhereClause

    @override
    def get(self, get_count: GetCount) -> WhereData:
        on = self.on.get(get_count)

        sql = f" LEFT JOIN {self.table.fqn()} ON {on.sql}"
        return WhereData(sql=sql, params=on.params)
