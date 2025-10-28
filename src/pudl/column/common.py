from __future__ import annotations

from typing import Callable, Self, overload

from pudl.column.base import ColumnBase, ColumnInfo, OnDelete
from pudl.query.many import ManyColumn
from pudl.table import Table
from pudl.types import PyType, Type


class Column[T: PyType](ColumnBase):
    """
    The main parent class for creating columns, generic over the Python type.
    """

    # This is a tuple of the two values needed to generate a foreign key:
    # - the table referred to (as a lambda as it will not be defined yet)
    # - any on_delete option
    _fk: tuple[Callable[[], Column[T]], OnDelete | None] | None = None

    # This must always be assigned by children, type-checker won't catch it
    _sql_type: str  # pyright:ignore[reportUninitializedInstanceVariable]

    def __init__(
        self,
        name: str | None = None,
        default: str | None = None,
        primary: bool = False,
        not_null: bool = False,
    ):
        self.name: str | None = name
        # if no _explicit_name, one is craeted automatically (see __set_name__)
        self._explicit_name: str | None = name
        self.default: str | None = default
        self.primary: bool = primary
        self.not_null: bool = not_null

    @overload
    def __get__(self, obj: None, owner: type) -> Self: ...
    @overload
    def __get__(self, obj: object, owner: type) -> T: ...

    def __get__(self, obj: object | None, owner: type) -> Self | T:
        """
        This allows this class to be typed as itself in Table definitions
        but as `T` in object instances. The overloads ensure this works for typechecking too.

        >>> from dataclasses import dataclass
        >>> from pudl.table import Table
        >>> @dataclass
        ... class MyTable(Table):
        ...     my_col: Text = Text()      # typechecked as `Text`
        >>> my_row = MyTable(my_col="foo") # typechecked as `str`
        >>> assert isinstance(MyTable.my_col, Text)
        >>> assert isinstance(my_row.my_col, str)
        """
        if obj is None:
            return self  # Class access returns descriptor
        return getattr(obj, f"_{self.name}")  # Instance access returns str

    def __set__(self, obj: object, value: T) -> None:
        # TODO is this still needed?
        setattr(obj, f"_{self.name}", value)

    def __set_name__(self, owner: Table, attr_name: str):
        """
        Called after the class body has executed, when the owning `Table` is being created.

        This is needed so that each `Column` can be told what the owning table's name is.
        """
        self.name = self._explicit_name if self._explicit_name is not None else attr_name
        self.info: ColumnInfo = ColumnInfo(
            name=self.name,
            col_type=self._sql_type,
            primary=self.primary,
            not_null=self.not_null,
            default=self.default,
            # This is passed a function, not a value.
            # Becuase in cases where the Table doesn't have an explicit name set, its name still
            # won't be known yet.
            _table_name=owner.get_name,
        )
        if self._fk is not None:
            ref, on_delete = self._fk
            self.info.ref = ref().info
            self.info.on_delete = on_delete

    def fk(
        self,
        ref: Callable[[], Column[T]],
        on_delete: OnDelete | None = None,
    ) -> Self:
        self._fk = (ref, on_delete)
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
