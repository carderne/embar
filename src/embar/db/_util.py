"""Utilities for database migrations."""

from collections import defaultdict, deque
from collections.abc import Sequence
from types import ModuleType

from embar.column.base import EnumBase
from embar.migration import Ddl, MigrationDefs
from embar.table import Table


def get_migration_defs(schema: ModuleType) -> MigrationDefs:
    """
    Extract all table and enum definitions from a schema module.
    """
    enums: list[type[EnumBase]] = []
    tables: list[type[Table]] = []
    for name in dir(schema):
        obj = getattr(schema, name)
        # Check if it's a class and inherits from Table
        if isinstance(obj, type) and issubclass(obj, Table) and obj is not Table:
            tables.append(obj)
        if isinstance(obj, type) and issubclass(obj, EnumBase) and obj is not EnumBase:
            enums.append(obj)
    return MigrationDefs(enums=enums, tables=tables)


def merge_ddls(defs: MigrationDefs) -> list[Ddl]:
    """
    Convert migration definitions to DDL statements in dependency order.
    """
    queries: list[Ddl] = []
    for enum in defs.enums:
        queries.append(Ddl(name=enum.name, ddl=enum.ddl()))

    tables = _topological_sort_tables(defs.tables)
    for table in tables:
        constraints: list[str] = []
        for constraint in table.embar_config.constraints:
            constraints.append(constraint.sql().merged())
        queries.append(Ddl(name=table.get_name(), ddl=table.ddl(), constraints=constraints))

    return queries


def _topological_sort_tables(tables: Sequence[type[Table]]) -> list[type[Table]]:
    """
    Sort table classes by foreign key dependencies using Kahn's algorithm.

    Tables are returned in the order they should be created.

    ```python
    from embar.column.common import Integer
    from embar.table import Table
    from embar.db._util import _topological_sort_tables
    class User(Table):
        id: Integer = Integer()
    class Message(Table):
        user_id: Integer = Integer().fk(lambda: User.id)
    sorted = _topological_sort_tables([Message, User])
    assert sorted[0] == User
    assert sorted[1] == Message
    ```
    """

    # Build dependency graph
    dependencies: dict[type[Table], set[type[Table]]] = defaultdict(set)
    in_degree: dict[type[Table], int] = {table: 0 for table in tables}

    # Map table names to table classes for lookup
    name_to_table: dict[str, type[Table]] = {table.get_name(): table for table in tables}

    for table in tables:
        for column in table._fields.values():  # pyright:ignore[reportPrivateUsage]
            if column.info.ref is not None:
                ref_column = column.info.ref
                ref_table_name = ref_column.table_name
                if ref_table_name in name_to_table:
                    ref_table = name_to_table[ref_table_name]
                    dependencies[ref_table].add(table)
                    in_degree[table] += 1

    # Kahn's algorithm
    queue: deque[type[Table]] = deque(table for table in tables if in_degree[table] == 0)
    result: list[type[Table]] = []

    while queue:
        current = queue.popleft()
        result.append(current)

        for dependent in dependencies[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(tables):
        raise ValueError("Circular dependency detected in table foreign keys")

    return result
