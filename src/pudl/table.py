from __future__ import annotations

from dataclasses import MISSING, dataclass, fields, make_dataclass, field
from typing import (
    Any,
    Callable,
    ClassVar,
    Self,
    TypeVar,
    final,
    overload,
)


@dataclass
class ColumnInfo:
    _table_name: Callable[[], str]
    name: str
    col_type: str
    primary: bool
    not_null: bool
    default: str | None
    ref: ColumnInfo | None = None

    @property
    def table_name(self) -> str:
        return self._table_name()

    def ddl(self: "ColumnInfo") -> str:
        primary = "PRIMARY KEY" if self.primary else ""
        nullable = "NOT NULL" if self.not_null else ""
        reference = (
            f'REFERENCES "{self.ref.table_name}"("{self.ref.name}")'
            if self.ref is not None
            else ""
        )
        text = f'"{self.name}" {self.col_type} {primary} {nullable} {reference}'
        return text


@final
class TextColumn:
    _ref: Callable[[], ColumnInfo] | None = None
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

    def __set_name__(self, owner: Table, attr_name: str):
        self.name = (
            self._explicit_name if self._explicit_name is not None else attr_name
        )
        self.info = ColumnInfo(
            name=self.name,
            col_type="text",
            primary=self.primary,
            not_null=self.not_null,
            default=self.default,
            _table_name=owner.get_name,
        )
        if self._ref is not None:
            self.info.ref = self._ref()

    def sel(self) -> str:
        return f'"{self.info.table_name}"."{self.info.name}"'

    def fk(self, ref: Callable[[], ColumnInfo]) -> Self:
        self._ref = ref
        return self


def Text(
    name: str | None = None,
    default: str | None = None,
    primary: bool = False,
    not_null: bool = False,
) -> TextColumn:
    return TextColumn(name, default, primary, not_null)


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
    def ddl(cls) -> str:
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, TextColumn):
                columns.append(attr.info.ddl())
        columns_str = ",".join(columns)
        return f"""CREATE TABLE IF NOT EXISTS "{cls._name}" ({columns_str});"""

    @classmethod
    def column_names(cls) -> list[str]:
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, TextColumn):
                columns.append(f'"{attr.info.name}"')
        return columns

    @classmethod
    def generate_selection_dataclass(cls) -> type[Selection]:
        fields: list[tuple[str, type, Any]] = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, TextColumn):
                fields.append(
                    (attr_name, str, field(default_factory=lambda a=attr: a.sel()))
                )

        return make_dataclass(f"{cls.__name__}", fields, bases=(Selection,))

    def values(self) -> list[Any]:
        result: list[Any] = []
        for attr_name in self.__class__.__dict__:
            if attr_name.startswith("_"):
                continue
            if isinstance(getattr(self.__class__, attr_name), TextColumn):
                result.append(getattr(self, attr_name))
        return result


AnyTable = TypeVar("AnyTable", bound=Table)


@dataclass
class Selection:
    @classmethod
    def to_sql_columns(cls) -> str:
        parts: list[str] = []
        for cls_field in fields(cls):
            source: Any = (
                cls_field.default_factory()
                if cls_field.default_factory is not MISSING
                else cls_field.default
            )
            target = cls_field.name
            parts.append(f'{source} AS "{target}"')

        return ", ".join(parts)


class SelectAll(Selection): ...
