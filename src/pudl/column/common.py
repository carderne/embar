from __future__ import annotations

from typing import Callable, Self, overload


from pudl.column.base import ManyColumn, ColumnInfo, ColumnBase
from pudl.table import Table
from pudl.types import PyType, Type


class Column[T: PyType](ColumnBase):
    _ref: Callable[[], Column[T]] | None = None
    _sql_type: str  # pyright:ignore[reportUninitializedInstanceVariable]

    def __init__(
        self,
        name: str | None = None,
        default: str | None = None,
        primary: bool = False,
        not_null: bool = False,
    ):
        self._explicit_name: str | None = name
        self.default: str | None = default
        self.primary: bool = primary
        self.not_null: bool = not_null
        self.name: str | None = name

    @overload
    def __get__(self, obj: None, owner: type) -> Self: ...
    @overload
    def __get__(self, obj: object, owner: type) -> T: ...

    def __get__(self, obj: object | None, owner: type) -> Self | T:
        if obj is None:
            return self  # Class access returns descriptor
        return getattr(obj, f"_{self.name}")  # Instance access returns str

    def __set__(self, obj: object, value: T) -> None:
        setattr(obj, f"_{self.name}", value)

    def __set_name__(self, owner: Table, attr_name: str):
        self.name = self._explicit_name if self._explicit_name is not None else attr_name
        self.info: ColumnInfo = ColumnInfo(
            name=self.name,
            col_type=self._sql_type,
            primary=self.primary,
            not_null=self.not_null,
            default=self.default,
            _table_name=owner.get_name,
        )
        if self._ref is not None:
            self.info.ref = self._ref().info

    def fk(self, ref: Callable[[], Column[T]]) -> Self:
        self._ref = ref
        return self

    def many(self) -> ManyColumn[Self]:
        return ManyColumn[Self](self)


class Text(Column[str]):
    _sql_type: str = "TEXT"
    _pytype: Type = str


class Integer(Column[int]):
    _sql_type: str = "INTEGER"
    _pytype: Type = int


class Float(Column[float]):
    _sql_type: str = "REAL"
    _pytype: Type = float
