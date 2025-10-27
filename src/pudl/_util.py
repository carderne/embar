from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import fields

from pudl.column.base import ColumnBase
from pudl.table import Table


def topological_sort_tables(tables: Sequence[type[Table]]) -> list[type[Table]]:
    """Sort table classes by foreign key dependencies using Kahn's algorithm."""

    # Build dependency graph
    dependencies: dict[type[Table], set[type[Table]]] = defaultdict(set)
    in_degree: dict[type[Table], int] = {table: 0 for table in tables}

    # Map table names to table classes for lookup
    name_to_table: dict[str, type[Table]] = {table.get_name(): table for table in tables}

    for table in tables:
        for field in fields(table):
            # Get the column instance from the field's default
            column = field.default
            if not isinstance(column, ColumnBase):
                continue

            # Check if this column has a foreign key reference
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
