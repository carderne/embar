from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pudl.types import Undefined


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

    @property
    def fqn(self) -> str:
        return f'"{self._table_name()}"."{self.name}"'

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


class ColumnBase:
    info: ColumnInfo  # pyright:ignore[reportUninitializedInstanceVariable]
    _pytype: type = Undefined


@dataclass
class ManyColumn[T: ColumnBase]:
    of: T
