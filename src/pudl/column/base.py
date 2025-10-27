from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from pudl.types import Type, Undefined

type OnDelete = (
    Literal["no action"] | Literal["restrict"] | Literal["set null"] | Literal["set default"] | Literal["cascade"]
)


@dataclass
class ColumnInfo:
    _table_name: Callable[[], str]
    name: str
    col_type: str
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
        return f'"{self._table_name()}"."{self.name}"'

    def ddl(self: "ColumnInfo") -> str:
        default = f"DEFAULT '{self.default}'" if self.default is not None else ""
        nullable = "NOT NULL" if self.not_null else ""
        primary = "PRIMARY KEY" if self.primary else ""
        reference = f'REFERENCES "{self.ref.table_name}"("{self.ref.name}")' if self.ref is not None else ""
        on_delete = f"ON DELETE {self.on_delete}" if self.on_delete is not None else ""
        text = f'"{self.name}" {self.col_type} {default} {nullable} {primary} {reference} {on_delete}'
        return text


class ColumnBase:
    info: ColumnInfo  # pyright:ignore[reportUninitializedInstanceVariable]
    _pytype: Type = Undefined


@dataclass
class ManyColumn[T: ColumnBase]:
    of: T
