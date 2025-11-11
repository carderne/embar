"""Common column types like Text, Integer, and Float."""

from typing import Any, Callable, Self, overload

from embar.column.base import ColumnBase, ColumnInfo, OnDelete
from embar.custom_types import PyType, Type
from embar.query.many import ManyColumn

SQL_TYPES_WITH_ARGS = ["NUMERIC", "DECIMAL", "VARCHAR", "CHAR"]


class Column[T: PyType](ColumnBase):
    """
    The main parent class for creating columns, generic over the Python type.
    """

    # This is a tuple of the two values needed to generate a foreign key:
    # - the table referred to (as a lambda as it will not be defined yet)
    # - any on_delete option
    _fk: tuple[Callable[[], Column[T]], OnDelete | None] | None = None

    _explicit_name: str | None
    _name: str | None
    default: T | None  # not protected because used by Table
    _primary: bool
    _not_null: bool

    # This is to support eg VARCHAR(100) and also NUMERIC(10, 2)
    _extra_args: tuple[int] | tuple[int, int] | None = None

    def __init__(
        self,
        name: str | None = None,
        default: T | None = None,
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
        from embar.column.common import Text
        class MyTable(Table):
            my_col: Text = Text()      # typechecked as `Text`
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
        self.info: ColumnInfo = ColumnInfo(
            name=self._name,
            col_type=self._sql_type,
            py_type=self._py_type,
            primary=self._primary,
            not_null=self._not_null,
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

        if self._sql_type in SQL_TYPES_WITH_ARGS and self._extra_args is not None:
            args = ", ".join(str(x) for x in self._extra_args)
            self.info.args = f"({args})"

    def fk(
        self,
        ref: Callable[[], Column[T]],
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
        from embar.column.common import Text
        from embar.table import Table
        class MyTable(Table):
            my_col: Text = Text()
        class MyModel(BaseModel):
            values: Annotated[list[str], MyTable.my_col.many()]
        ```
        """
        return ManyColumn[Self](self)


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
