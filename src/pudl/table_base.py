from dataclasses import dataclass

from pudl.column_base import ColumnBase


@dataclass
class TableBase:
    _name: str = ""

    @classmethod
    def fqn(cls) -> str:
        return f'"{cls._name}"'

    @classmethod
    def column_names(cls) -> list[str]:
        """
        Unquoted list of column names.
        """
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                columns.append(attr.info.name)
        return columns


@dataclass
class ManyTable[T: type[TableBase]]:
    of: T
