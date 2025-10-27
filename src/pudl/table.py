from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from pudl.column.base import ColumnBase
from pudl.table_base import ManyTable, TableBase


@dataclass
class Table(TableBase):
    """
    All Table definitions inherit from `Table`.

    It's a `dataclass` so that [`_util.topological_sort_tables`][_util.topological_sort_tables]
    can pick up the fields.
    """

    def __init_subclass__(cls, **kwargs: Any):
        if not hasattr(cls, "_name") or cls._name == Table._name:
            # Convert ClassName -> class_name
            cls._name: str = "".join("_" + c.lower() if c.isupper() else c for c in cls.__name__).lstrip("_")
        super().__init_subclass__(**kwargs)

    @classmethod
    def many(cls) -> ManyTable[type[Self]]:
        return ManyTable[type[Self]](cls)

    @classmethod
    def get_name(cls) -> str:
        # TODO: the `_name` field seems to get included when ser/de?
        return cls._name

    @classmethod
    def ddl(cls) -> str:
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
