from dataclasses import dataclass
from typing import Any, Callable, Literal

from embar.custom_types import Type, Undefined

type OnDelete = (
    Literal["no action"] | Literal["restrict"] | Literal["set null"] | Literal["set default"] | Literal["cascade"]
)


@dataclass
class ColumnInfo:
    """
    `ColumnInfo` is the type that ultimately holds all the db column info.

    It knows nothing about the python field: its name, what type it should deserialize to etc.
    """

    # _table_name is callable as generally the `Table` won't yet have a name
    # at the time the Column is created.
    _table_name: Callable[[], str]
    name: str
    col_type: str
    py_type: Type
    primary: bool
    not_null: bool
    default: Any | None = None
    ref: ColumnInfo | None = None
    on_delete: OnDelete | None = None

    @property
    def table_name(self) -> str:
        return self._table_name()

    @property
    def fqn(self) -> str:
        """
        Return the Fully Qualified Name (table and column both in quotes).

        Example:
        >>> col = ColumnInfo(
        ...    _table_name=lambda: "foo", name="bar", col_type="TEXT", py_type=str, primary=False, not_null=False
        ... )
        >>> col.fqn
        '"foo"."bar"'
        """
        return f'"{self._table_name()}"."{self.name}"'

    def ddl(self: "ColumnInfo") -> str:
        """
        Generate the DDL just for this column.

        Used by the [`Table.ddl()`][embar.table.Table.ddl] method to generate the full DDL.

        Example:
        >>> col = ColumnInfo(
        ...    _table_name=lambda: "foo", name="bar", col_type="TEXT", py_type=str, primary=True, not_null=True
        ... )
        >>> col.ddl()
        '"bar" TEXT  NOT NULL PRIMARY KEY  '
        """
        # TODO sort out all the double spacing stuff
        default = f"DEFAULT '{self.default}'" if self.default is not None else ""
        nullable = "NOT NULL" if self.not_null else ""
        primary = "PRIMARY KEY" if self.primary else ""
        reference = f'REFERENCES "{self.ref.table_name}"("{self.ref.name}")' if self.ref is not None else ""
        on_delete = f"ON DELETE {self.on_delete}" if self.on_delete is not None else ""
        text = f'"{self.name}" {self.col_type} {default} {nullable} {primary} {reference} {on_delete}'
        return text


class ColumnBase:
    """
    Base class for all [`Column`][embar.column.common.column] classes.

    Mostly here to avoid circular dependencies with modules that need to know about the fields below.
    """

    info: ColumnInfo  # pyright:ignore[reportUninitializedInstanceVariable]
    # TODO Check if any methods use _pytype while it could be Undefined
    # If so the class probably needs to be split...
    _pytype: Type = Undefined
