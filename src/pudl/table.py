from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    TypeVar,
    final,
    overload,
)


@dataclass
class ColumnInfo:
    name: str
    col_type: str
    primary: bool
    not_null: bool
    default: str | None
    py_type: type

    def ddl(self: "ColumnInfo") -> str:
        primary = "PRIMARY KEY" if self.primary else ""
        nullable = "NOT NULL" if self.not_null else ""
        text = f"{self.name} {self.col_type} {primary} {nullable}"
        return text


@final
class TextColumn:
    info: ColumnInfo  # pyright:ignore[reportUninitializedInstanceVariable]

    @overload
    def __get__(self, obj: None, owner: type) -> "TextColumn": ...
    @overload
    def __get__(self, obj: object, owner: type) -> str: ...

    def __get__(self, obj: object | None, owner: type) -> "TextColumn | str":
        if obj is None:
            return self  # Class access returns descriptor
        return getattr(obj, f"_{self.name}", "")  # Instance access returns str

    def __set__(self, obj: object, value: str) -> None:
        setattr(obj, f"_{self.name}", value)

    def __init__(
        self,
        name: str | None,
        default: str | None = None,
        primary: bool = False,
        not_null: bool = False,
    ):
        self._explicit_name = name
        self.default = default
        self.primary = primary
        self.not_null = not_null
        self.name = name

    def __set_name__(self, owner: object, attr_name: str):
        self.name = (
            self._explicit_name if self._explicit_name is not None else attr_name
        )
        self.info = ColumnInfo(
            self.name, "text", self.primary, self.not_null, self.default, py_type=str
        )


def Text(
    name: str | None = None,
    default: str | None = None,
    primary: bool = False,
    not_null: bool = False,
) -> TextColumn:
    return TextColumn(name, default, primary, not_null)


@dataclass
class Table:
    _name: ClassVar[str]

    @classmethod
    def ddl(cls) -> str:
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, TextColumn):
                columns.append(attr.info.ddl())
        columns_str = ",".join(columns)
        return f"""CREATE TABLE IF NOT EXISTS {cls._name} ({columns_str});"""

    @classmethod
    def column_names(cls) -> list[str]:
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, TextColumn):
                columns.append(attr.info.name)
        return columns

    def values(self) -> list[Any]:
        result: list[Any] = []
        for attr_name in self.__class__.__dict__:
            if attr_name.startswith("_"):
                continue
            if isinstance(getattr(self.__class__, attr_name), TextColumn):
                result.append(getattr(self, attr_name))
        return result


AnyTable = TypeVar("AnyTable", bound=Table)


def table_config[T: Table](name: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        cls._name = name  # pyright:ignore[reportPrivateUsage]
        return cls

    return decorator
