"""Common column types like Text, Integer, and Float."""

from typing import Any, Callable, Self, TypeAlias, overload

from embar.column.base import ColumnBase, ColumnInfo, OnDelete
from embar.custom_types import NO_DEFAULT, PyType, Type, _NoDefaultType
from embar.query.many import ManyColumn

SQL_TYPES_WITH_ARGS = ["NUMERIC", "DECIMAL", "VARCHAR", "CHAR"]


class Column[T: PyType](ColumnBase):
    """
    The main parent class for creating columns, generic over the Python type.
    """

    # This is a tuple of the two values needed to generate a foreign key:
    # - the table referred to (as a lambda as it will not be defined yet)
    # - any on_delete option
    _fk: tuple[Callable[[], Column[Any]], OnDelete | None] | None = None

    _explicit_name: str | None
    _name: str | None
    default: T | _NoDefaultType  # NO_DEFAULT means "no default"
    _primary: bool
    _not_null: bool

    # This is to support eg VARCHAR(100) and also NUMERIC(10, 2)
    _extra_args: tuple[int] | tuple[int, int] | None = None

    def __init__(
        self,
        name: str | None = None,
        default: T | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
    ):
        """
        Create a new Column instance.
        """
        self._name = name
        # if no _explicit_name, one is created automatically (see __set_name__)
        self._explicit_name = name
        self.default = default
        self._primary = primary
        self._not_null = not_null

    @overload
    def __get__(self, obj: None, owner: type) -> Self: ...
    @overload
    def __get__(self, obj: object, owner: type) -> T: ...

    def __get__(self, obj: object | None, owner: type) -> Self | T:
        """
        This allows this class to be typed as itself in Table definitions
        but as `T` in object instances. The overloads ensure this works for typechecking too.

        ```python
        from embar.table import Table
        from embar.column.common import Text, text
        class MyTable(Table):
            my_col: Text = text()      # typechecked as `Text`
        my_row = MyTable(my_col="foo") # typechecked as `str`
        assert isinstance(MyTable.my_col, Text)
        assert isinstance(my_row.my_col, str)
        ```
        """
        if obj is None:
            return self  # Class access returns descriptor
        return getattr(obj, f"_{self._name}")  # Instance access returns str

    def __set__(self, obj: object, value: T) -> None:
        """
        Allows values of type T (rather than `Column[T]`) to be assigned to this class when it's a field of an object.
        """
        setattr(obj, f"_{self._name}", value)

    def __set_name__(self, owner: Any, attr_name: str) -> None:
        """
        Called after the class body has executed, when the owning `Table` is being created.

        This is needed so that each `Column` can be told what the owning table's name is.
        """
        self._name = self._explicit_name if self._explicit_name is not None else attr_name
        default_for_info = None if isinstance(self.default, _NoDefaultType) else self.default
        self.info: ColumnInfo = ColumnInfo(
            name=self._name,
            col_type=self._sql_type,
            py_type=self._py_type,
            primary=self._primary,
            not_null=self._not_null,
            default=default_for_info,
            # This is passed a function, not a value.
            # Becuase in cases where the Table doesn't have an explicit name set, its name still
            # won't be known yet.
            _table_name=owner.get_name,
        )
        if self._fk is not None:
            ref, on_delete = self._fk
            self.info.ref = ref().info
            self.info.on_delete = on_delete

        if self._sql_type in SQL_TYPES_WITH_ARGS and self._extra_args is not None:
            args = ", ".join(str(x) for x in self._extra_args)
            self.info.args = f"({args})"

    def fk(
        self,
        ref: Callable[[], Column[Any]],
        on_delete: OnDelete | None = None,
    ) -> Self:
        """
        Create a foreign key reference to another table.
        """
        self._fk = (ref, on_delete)
        return self

    def many(self) -> ManyColumn[Self]:
        """
        Used to nest many values of this column in a model.

        ```python
        from typing import Annotated
        from pydantic import BaseModel
        from embar.column.common import Text, text
        from embar.table import Table
        class MyTable(Table):
            my_col: Text = text()
        class MyModel(BaseModel):
            values: Annotated[list[str], MyTable.my_col.many()]
        ```
        """
        return ManyColumn(self)

    @property
    def has_default(self) -> bool:
        """Whether this column has a default value (including None)."""
        return not isinstance(self.default, _NoDefaultType)


class Text(Column[str]):
    """
    A text column type.
    """

    _sql_type: str = "TEXT"
    _py_type: Type = str


class Integer(Column[int]):
    """
    An integer column type.
    """

    _sql_type: str = "INTEGER"
    _py_type: Type = int


class Float(Column[float]):
    """
    A floating point column type.
    """

    _sql_type: str = "REAL"
    _py_type: Type = float


class Null[T: PyType](Column[T | None]):
    """
    A nullable column type.

    Use this as the annotation for columns that can be ``NULL`` in the database.
    The type parameter ``T`` is the underlying Python type (e.g. ``str``, ``int``).

    At the class level, ``Null[str]`` is a :class:`ColumnBase` so it works in
    ``order_by``, ``where``, ``Annotated``, etc.  At the instance level, the
    value is typed as ``T | None``.

    Convenience aliases are provided: :data:`NullText`, :data:`NullInteger`,
    :data:`NullFloat`.

    ```python
    from embar.table import Table
    from embar.column.common import Text, NullText, text, integer, NullInteger
    class MyTable(Table):
        name: Text = text()
        email: NullText = text(default=None)      # nullable, optional
        age: NullInteger = integer(default=None)   # nullable, optional
    row = MyTable(name="foo")
    assert row.email is None
    ```
    """

    def __init__(
        self,
        sql_type: str,
        py_type: Type,
        name: str | None = None,
        default: T | None | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
    ):
        self._sql_type = sql_type
        self._py_type = py_type
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


# Convenience type aliases for nullable columns
NullText: TypeAlias = Null[str]
"""A nullable text column. Alias for ``Null[str]``."""

NullInteger: TypeAlias = Null[int]
"""A nullable integer column. Alias for ``Null[int]``."""

NullFloat: TypeAlias = Null[float]
"""A nullable float column. Alias for ``Null[float]``."""


# ---------------------------------------------------------------------------
# Factory functions (field specifiers for @dataclass_transform)
#
# ty (the type checker) only recognises *functions* — not classes — as
# field_specifiers.  These thin wrappers have the right signature so that
# ty can inspect the ``default`` parameter and decide whether a field is
# required or optional.  At runtime they just delegate to the class.
#
# Each function has three overloads:
# 1. No default → returns the non-null column type (field is required)
# 2. default: T  → returns the non-null column type (field is optional)
# 3. default: None → returns Null[T] (field is nullable and optional)
# ---------------------------------------------------------------------------


@overload
def text(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Text: ...


@overload
def text(
    name: str | None = ...,
    *,
    default: str,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Text: ...


@overload
def text(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> NullText: ...


def text(
    name: str | None = None,
    *,
    default: str | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    fk: Callable[[], Column[str]] | None = None,
    on_delete: OnDelete | None = None,
) -> Text | NullText:
    """Create a :class:`Text` column (field specifier for ``@dataclass_transform``)."""
    col: Text | Null[str]
    if default is None:
        col = Null[str](sql_type="TEXT", py_type=str, name=name, default=default, primary=primary, not_null=not_null)
    else:
        col = Text(name=name, default=default, primary=primary, not_null=not_null)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def integer(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Integer: ...


@overload
def integer(
    name: str | None = ...,
    *,
    default: int,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Integer: ...


@overload
def integer(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> NullInteger: ...


def integer(
    name: str | None = None,
    *,
    default: int | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    fk: Callable[[], Column[int]] | None = None,
    on_delete: OnDelete | None = None,
) -> Integer | NullInteger:
    """Create an :class:`Integer` column (field specifier for ``@dataclass_transform``)."""
    col: Integer | Null[int]
    if default is None:
        col = Null[int](sql_type="INTEGER", py_type=int, name=name, default=default, primary=primary, not_null=not_null)
    else:
        col = Integer(name=name, default=default, primary=primary, not_null=not_null)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def float_col(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[float]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Float: ...


@overload
def float_col(
    name: str | None = ...,
    *,
    default: float,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[float]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Float: ...


@overload
def float_col(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[float]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> NullFloat: ...


def float_col(
    name: str | None = None,
    *,
    default: float | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    fk: Callable[[], Column[float]] | None = None,
    on_delete: OnDelete | None = None,
) -> Float | NullFloat:
    """Create a :class:`Float` column (field specifier for ``@dataclass_transform``)."""
    col: Float | Null[float]
    if default is None:
        col = Null[float](
            sql_type="REAL", py_type=float, name=name, default=default, primary=primary, not_null=not_null
        )
    else:
        col = Float(name=name, default=default, primary=primary, not_null=not_null)
    if fk is not None:
        col.fk(fk, on_delete)
    return col
