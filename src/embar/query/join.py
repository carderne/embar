from abc import ABC, abstractmethod
from typing import override

from embar.query.query import Query
from embar.query.where import GetCount, WhereClause
from embar.table import Table


class JoinClause(ABC):
    @abstractmethod
    def get(self, get_count: GetCount) -> Query: ...


class LeftJoin(JoinClause):
    table: type[Table]
    on: WhereClause

    def __init__(self, table: type[Table], on: WhereClause):
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> Query:
        on = self.on.sql(get_count)

        sql = f"LEFT JOIN {self.table.fqn()} ON {on.sql}"
        return Query(sql=sql, params=on.params)


class RightJoin(JoinClause):
    table: type[Table]
    on: WhereClause

    def __init__(self, table: type[Table], on: WhereClause):
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> Query:
        on = self.on.sql(get_count)

        sql = f"RIGHT JOIN {self.table.fqn()} ON {on.sql}"
        return Query(sql=sql, params=on.params)


class InnerJoin(JoinClause):
    table: type[Table]
    on: WhereClause

    def __init__(self, table: type[Table], on: WhereClause):
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> Query:
        on = self.on.sql(get_count)

        sql = f"INNER JOIN {self.table.fqn()} ON {on.sql}"
        return Query(sql=sql, params=on.params)


class FullJoin(JoinClause):
    table: type[Table]
    on: WhereClause

    def __init__(self, table: type[Table], on: WhereClause):
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> Query:
        on = self.on.sql(get_count)

        sql = f"FULL OUTER JOIN {self.table.fqn()} ON {on.sql}"
        return Query(sql=sql, params=on.params)


class CrossJoin(JoinClause):
    table: type[Table]

    def __init__(self, table: type[Table]):
        self.table = table

    @override
    def get(self, get_count: GetCount) -> Query:
        sql = f"CROSS JOIN {self.table.fqn()}"
        return Query(sql=sql)
