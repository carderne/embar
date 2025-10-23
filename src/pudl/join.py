from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

from pudl.table import Table
from pudl.where import GetCount, WhereClause, WhereData


class JoinClause(ABC):
    @abstractmethod
    def get(self, get_count: GetCount) -> WhereData: ...


@dataclass
class LeftJoin(JoinClause):
    table: type[Table]
    on: WhereClause

    @override
    def get(self, get_count: GetCount) -> WhereData:
        on = self.on.get(get_count)

        sql = f" LEFT JOIN {self.table.fqn()} ON {on.sql}"
        return WhereData(sql=sql, params=on.params)
