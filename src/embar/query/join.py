"""Join clauses for queries."""

from abc import ABC, abstractmethod
from typing import override

from embar.query.clause_base import ClauseBase, GetCount
from embar.query.query import QuerySingle
from embar.table import Table


class JoinClause(ABC):
    """
    Base class for all join clauses.
    """

    @abstractmethod
    def get(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the SQL for this join clause.
        """
        ...


class LeftJoin(JoinClause):
    """
    LEFT JOIN clause.
    """

    table: type[Table]
    on: ClauseBase

    def __init__(self, table: type[Table], on: ClauseBase):
        """
        Create a new LeftJoin instance.
        """
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the LEFT JOIN SQL.
        """
        on = self.on.sql(get_count)

        sql = f"LEFT JOIN {self.table.fqn()} ON {on.sql}"
        return QuerySingle(sql=sql, params=on.params)


class RightJoin(JoinClause):
    """
    RIGHT JOIN clause.
    """

    table: type[Table]
    on: ClauseBase

    def __init__(self, table: type[Table], on: ClauseBase):
        """
        Create a new RightJoin instance.
        """
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the RIGHT JOIN SQL.
        """
        on = self.on.sql(get_count)

        sql = f"RIGHT JOIN {self.table.fqn()} ON {on.sql}"
        return QuerySingle(sql=sql, params=on.params)


class InnerJoin(JoinClause):
    """
    INNER JOIN clause.
    """

    table: type[Table]
    on: ClauseBase

    def __init__(self, table: type[Table], on: ClauseBase):
        """
        Create a new InnerJoin instance.
        """
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the INNER JOIN SQL.
        """
        on = self.on.sql(get_count)

        sql = f"INNER JOIN {self.table.fqn()} ON {on.sql}"
        return QuerySingle(sql=sql, params=on.params)


class FullJoin(JoinClause):
    """
    FULL OUTER JOIN clause.
    """

    table: type[Table]
    on: ClauseBase

    def __init__(self, table: type[Table], on: ClauseBase):
        """
        Create a new FullJoin instance.
        """
        self.table = table
        self.on = on

    @override
    def get(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the FULL OUTER JOIN SQL.
        """
        on = self.on.sql(get_count)

        sql = f"FULL OUTER JOIN {self.table.fqn()} ON {on.sql}"
        return QuerySingle(sql=sql, params=on.params)


class CrossJoin(JoinClause):
    """
    CROSS JOIN clause.
    """

    table: type[Table]

    def __init__(self, table: type[Table]):
        """
        Create a new CrossJoin instance.
        """
        self.table = table

    @override
    def get(self, get_count: GetCount) -> QuerySingle:
        """
        Generate the CROSS JOIN SQL.
        """
        sql = f"CROSS JOIN {self.table.fqn()}"
        return QuerySingle(sql=sql)
