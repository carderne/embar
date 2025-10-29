"""
Ideally table.py would be in a table/ module but then it's impossible
to import table_base.py without triggering table.py, causing a circular loop by the Many stuff
(that's the reason the two were separated in the first place).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from embar.column.base import ColumnBase
from embar.query.many import ManyTable
from embar.table_base import TableBase


@dataclass
class Table(TableBase):
    """
    All table definitions inherit from `Table`.

    Table is used extensively as both a class/type and as objects.
    - Tables/schemas are created as `class MyTable(Table): ...`
    - Table references (in where clauses, joins, FKs) refer to these types
    - New rows to insert into a table are created as objects
    - Values returned from Select queries are based on dynamically generated classes or
      `Selection` classes, never directly instances of `Table`

    It's a `dataclass` so that [`topological_sort_tables`][embar._util.topological_sort_tables]
    can pick up the fields.
    """

    def __init_subclass__(cls, **kwargs: Any):
        """
        Creates a `_name` attribute for the class based on its name, if one isn't provided.
        """
        if not hasattr(cls, "_name") or cls._name == Table._name:
            # Convert ClassName -> class_name
            cls._name: str = "".join("_" + c.lower() if c.isupper() else c for c in cls.__name__).lstrip("_")
        super().__init_subclass__(**kwargs)

    @classmethod
    def many(cls) -> ManyTable[type[Self]]:
        """
        Used to nest many of another table in a column in a [`Selection`][embar.selection.Selection].

        Example:
        >>> from embar.query.selection import Selection
        >>> class MyTable(Table): ...
        >>> class MySelectQuery(Selection):
        ...     messages: Annotated[list[MyTable], MyTable.many()]
        """
        return ManyTable[type[Self]](cls)

    @classmethod
    def get_name(cls) -> str:
        """
        Get the table's _database_ name.
        """
        return cls._name

    @classmethod
    def ddl(cls) -> str:
        """
        Generate a full DDL for the table.
        """
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                columns.append(attr.info.ddl())
        columns_str = ",".join(columns)
        return f"""CREATE TABLE IF NOT EXISTS {cls.fqn()} ({columns_str});"""

    def value_dict(self) -> dict[str, Any]:
        """
        Result is keyed to DB column names, _not_ field names.
        """
        result: dict[str, Any] = {}
        for attr_name, attr in self.__class__.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                result[attr.info.name] = getattr(self, attr_name)
        return result
