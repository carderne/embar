from __future__ import annotations

from dataclasses import dataclass, make_dataclass, field
from typing import Any, ClassVar

from pudl.column_base import ColumnBase
from pudl.selection import Selection


@dataclass
class Table:
    _name: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any):
        if not hasattr(cls, "_name") or cls._name == Table._name:
            # Convert ClassName -> class_name
            cls._name = "".join(
                "_" + c.lower() if c.isupper() else c for c in cls.__name__
            ).lstrip("_")
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_name(cls) -> str:
        return cls._name

    @classmethod
    def fqn(cls) -> str:
        return f'"{cls._name}"'

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

    @classmethod
    def column_names(cls) -> list[str]:
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                columns.append(f'"{attr.info.name}"')
        return columns

    @classmethod
    def generate_selection_dataclass(cls) -> type[Selection]:
        fields: list[tuple[str, type, Any]] = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, ColumnBase):
                fields.append(
                    (attr_name, str, field(default_factory=lambda a=attr: a.info.fqn))
                )

        return make_dataclass(f"{cls.__name__}", fields, bases=(Selection,))

    def values(self) -> list[Any]:
        result: list[Any] = []
        for attr_name in self.__class__.__dict__:
            if attr_name.startswith("_"):
                continue
            if isinstance(getattr(self.__class__, attr_name), ColumnBase):
                result.append(getattr(self, attr_name))
        return result
