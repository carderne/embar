from dataclasses import dataclass


@dataclass
class TableBase:
    _name: str = ""

    @classmethod
    def fqn(cls) -> str:
        return f'"{cls._name}"'


@dataclass
class ManyTable[T: type[TableBase]]:
    of: T
