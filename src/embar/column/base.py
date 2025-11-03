from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Literal

from embar.custom_types import Type

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

    args: str | None = None

    @property
    def table_name(self) -> str:
        return self._table_name()

    def fqn(self) -> str:
        """
        Return the Fully Qualified Name (table and column both in quotes).

        ```python
        from embar.column.base import ColumnInfo
        col = ColumnInfo(
           _table_name=lambda: "foo", name="bar", col_type="TEXT", py_type=str, primary=False, not_null=False
        )
        fqn = col.fqn()
        assert fqn == '"foo"."bar"'
        ```
        """
        return f'"{self._table_name()}"."{self.name}"'

    def ddl(self) -> str:
        """
        Generate the DDL just for this column.

        Used by the [`Table.ddl()`][embar.table.Table.ddl] method to generate the full DDL.

        ```python
        from embar.column.base import ColumnInfo
        col = ColumnInfo(
           _table_name=lambda: "foo", name="bar", col_type="TEXT", py_type=str, primary=True, not_null=True
        )
        ddl = col.ddl()
        assert ddl == '"bar" TEXT NOT NULL PRIMARY KEY'
        ```
        """
        args = self.args if self.args is not None else ""
        default = f"DEFAULT '{self.default}'" if self.default is not None else ""
        nullable = "NOT NULL" if self.not_null else ""
        primary = "PRIMARY KEY" if self.primary else ""
        reference = f'REFERENCES "{self.ref.table_name}"("{self.ref.name}")' if self.ref is not None else ""
        on_delete = f"ON DELETE {self.on_delete}" if self.on_delete is not None else ""
        text = f'"{self.name}" {self.col_type}{args} {default} {nullable} {primary} {reference} {on_delete}'
        clean = " ".join(text.split()).strip()
        return clean


class ColumnBase:
    """
    Base class for all [`Column`][embar.column.common.Column] classes.

    Mostly here to avoid circular dependencies with modules that need to know about the fields below.
    """

    info: ColumnInfo  # pyright:ignore[reportUninitializedInstanceVariable]

    # These must always be assigned by children, type-checker won't catch it
    _sql_type: str  # pyright:ignore[reportUninitializedInstanceVariable]
    _py_type: Type  # pyright:ignore[reportUninitializedInstanceVariable]


class EnumBase(ABC):
    name: str

    @classmethod
    @abstractmethod
    def ddl(cls) -> str: ...
