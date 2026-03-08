"""Postgres-specific column types."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, TypeAlias, overload, override

from embar.column.base import EnumBase, OnDelete
from embar.column.common import (
    Column,
    Float,
    Integer,
    Null,
    NullFloat,
    NullInteger,
    NullText,
    Text,
    float_col,
    integer,
    text,
)
from embar.custom_types import NO_DEFAULT, Type, _NoDefaultType

# Re-export the common types as well as any new ones defined below
__all__ = [
    # Classes (used as type annotations)
    "BigInt",
    "BigSerial",
    "Boolean",
    "Char",
    "Date",
    "PgDecimal",
    "DoublePrecision",
    "Float",
    "Integer",
    "Interval",
    "Json",
    "Jsonb",
    "Null",
    "NullBigInt",
    "NullBoolean",
    "NullDate",
    "NullDoublePrecision",
    "NullFloat",
    "NullInteger",
    "NullInterval",
    "NullSmallInt",
    "NullText",
    "NullTimestamp",
    "NullVarchar",
    "Numeric",
    "Serial",
    "SmallInt",
    "SmallSerial",
    "Text",
    "Time",
    "Timestamp",
    "Varchar",
    "EnumCol",
    "Vector",
    # Factory functions (used as field values in Table definitions)
    "float_col",
    "integer",
    "text",
    "serial",
    "boolean",
    "timestamp",
    "jsonb",
    "smallint",
    "bigint",
    "smallserial",
    "bigserial",
    "varchar",
    "char_col",
    "numeric",
    "pg_decimal",
    "double_precision",
    "json_col",
    "time_col",
    "date_col",
    "interval",
    "enum_col",
    "vector",
]


class Serial(Column[int]):
    """
    Auto-incrementing integer column.
    """

    _sql_type: str = "SERIAL"
    _py_type: Type = int


class Boolean(Column[bool]):
    """
    Boolean column type.
    """

    _sql_type: str = "BOOLEAN"
    _py_type: Type = bool


class Timestamp(Column[datetime]):
    """
    Timestamp column type.
    """

    _sql_type: str = "TIMESTAMP"
    _py_type: Type = str


class Jsonb(Column[dict[str, Any]]):
    """
    JSONB column type for storing JSON data.
    """

    _sql_type: str = "JSONB"
    _py_type: Type = dict[str, Any]


# Integer types
class SmallInt(Column[int]):
    """
    Small integer column type.
    """

    _sql_type: str = "SMALLINT"
    _py_type: Type = int


class BigInt(Column[int]):
    """
    Big integer column type.
    """

    _sql_type: str = "BIGINT"
    _py_type: Type = int


# Serial types
class SmallSerial(Column[int]):
    """
    Auto-incrementing small integer column.
    """

    _sql_type: str = "SMALLSERIAL"
    _py_type: Type = int


class BigSerial(Column[int]):
    """
    Auto-incrementing big integer column.
    """

    _sql_type: str = "BIGSERIAL"
    _py_type: Type = int


# String types
class Varchar(Column[str]):
    """
    Variable-length character column type.
    """

    _sql_type: str = "VARCHAR"
    _py_type: Type = str

    def __init__(
        self,
        name: str | None = None,
        default: str | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
        length: int | None = None,
    ):
        """
        Create a new Varchar instance.
        """
        self._extra_args: tuple[int] | tuple[int, int] | None = (length,) if length is not None else None
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


class Char(Column[str]):
    """
    Fixed-length character column type.
    """

    _sql_type: str = "CHAR"
    _py_type: Type = str

    def __init__(
        self,
        name: str | None = None,
        default: str | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
        length: int | None = None,
    ):
        """
        Create a new Char instance.
        """
        self._extra_args: tuple[int] | tuple[int, int] | None = (length,) if length is not None else None
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


# Numeric types
class Numeric(Column[Decimal]):
    """
    Numeric column type with configurable precision and scale.
    """

    _sql_type: str = "NUMERIC"
    _py_type: Type = Decimal

    _extra_args: tuple[int] | tuple[int, int] | None

    def __init__(
        self,
        name: str | None = None,
        default: Decimal | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
        precision: int | None = None,
        scale: int | None = None,
    ):
        """
        Create a new Numeric instance.
        """
        if precision is None:
            if scale is not None:
                raise Exception("Numeric: 'precision' cannot be None if scale is set")
        elif scale is None:
            self._extra_args = (precision,)
        else:
            self._extra_args = (precision, scale)
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


class PgDecimal(Column[Decimal]):
    """
    Decimal column type with configurable precision and scale.
    """

    # Note: DECIMAL is an alias for NUMERIC in PostgreSQL
    _sql_type: str = "DECIMAL"
    _py_type: Type = Decimal

    _extra_args: tuple[int] | tuple[int, int] | None

    def __init__(
        self,
        name: str | None = None,
        default: Decimal | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
        precision: int | None = None,
        scale: int | None = None,
    ):
        """
        Create a new PgDecimal instance.
        """
        if precision is None:
            if scale is not None:
                raise Exception("Numeric: 'precision' cannot be None if scale is set")
        elif scale is None:
            self._extra_args = (precision,)
        else:
            self._extra_args = (precision, scale)
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


class DoublePrecision(Column[float]):
    """
    Double precision floating point column type.
    """

    _sql_type: str = "DOUBLE PRECISION"
    _py_type: Type = float


# JSON types
class Json(Column[dict[str, Any]]):
    """
    JSON column type for storing JSON data.
    """

    _sql_type: str = "JSON"
    _py_type: Type = dict[str, Any]


# Date/Time types
class Time(Column[time]):
    """
    Time column type.
    """

    _sql_type: str = "TIME"
    _py_type: Type = time


class Date(Column[date]):
    """
    Date column type.
    """

    _sql_type: str = "DATE"
    _py_type: Type = date


class Interval(Column[timedelta]):
    """
    Interval column type for storing time intervals.
    """

    _sql_type: str = "INTERVAL"
    _py_type: Type = timedelta


# Enum
class EmbarEnum(str, Enum):
    """
    `EmbarEnum` is just a regular Enum but without having to set the right side.

    ```python
    from enum import auto
    from embar.column.pg import EmbarEnum
    class StatusEnum(EmbarEnum):
       PENDING = auto()
       DONE = auto()
    ```
    """

    @staticmethod
    @override
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[Any]) -> str:
        return name


class PgEnum[E: EmbarEnum](EnumBase):
    """
    `PgEnum is used to create Postgres enum types.

    Subclasses must always assign values to the two class variables!

    ```python
    from enum import auto
    from embar.table import Table
    from embar.column.pg import EmbarEnum, EnumCol, PgEnum, enum_col
    class StatusEnum(EmbarEnum):
       PENDING = auto()
       DONE = auto()
    class StatusPgEnum(PgEnum[StatusEnum]):
        name: str = "status_enum"
        enum: type[StatusEnum] = StatusEnum
    class TableWithStatus(Table):
        status: EnumCol[StatusEnum] = enum_col(StatusPgEnum)
    ```
    """

    name: str
    enum: type[E]

    @override
    @classmethod
    def ddl(cls) -> str:
        quoted = [f"'{e.name}'" for e in cls.enum]
        values = ", ".join(quoted)
        sql = f"CREATE TYPE {cls.name} AS ENUM ({values});"
        return sql


class EnumCol[E: EmbarEnum](Column[str]):
    """
    Column type for Postgres enum values.
    """

    _sql_type: str
    _py_type: Type = str

    def __init__(
        self,
        pg_enum: type[PgEnum[E]],
        name: str | None = None,
        default: E | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
    ):
        """
        Create a new EnumCol instance.
        """
        self._sql_type = pg_enum.name

        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


# Extension: pgvector
# Should also support `halfvec` and `bit`
class Vector(Column[list[float]]):
    """
    Vector column using [pgvector](https://github.com/pgvector/pgvector).

    This assumes the extension is already installed and activated with
    CREATE EXTENSION vector;
    """

    _sql_type: str = "VECTOR"
    _py_type: Type = list[float]

    def __init__(
        self,
        length: int,
        name: str | None = None,
        default: list[float] | _NoDefaultType = NO_DEFAULT,
        primary: bool = False,
        not_null: bool = False,
    ):
        """
        Create a new Vector instance.
        """
        self._extra_args: tuple[int] | tuple[int, int] | None = (length,)
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)


# ---------------------------------------------------------------------------
# Nullable type aliases for Postgres-specific column types
# ---------------------------------------------------------------------------

NullBoolean: TypeAlias = Null[bool]
"""A nullable boolean column. Alias for ``Null[bool]``."""

NullTimestamp: TypeAlias = Null[datetime]
"""A nullable timestamp column. Alias for ``Null[datetime]``."""

NullSmallInt: TypeAlias = Null[int]
"""A nullable small integer column. Alias for ``Null[int]``."""

NullBigInt: TypeAlias = Null[int]
"""A nullable big integer column. Alias for ``Null[int]``."""

NullVarchar: TypeAlias = Null[str]
"""A nullable varchar column. Alias for ``Null[str]``."""

NullDoublePrecision: TypeAlias = Null[float]
"""A nullable double precision column. Alias for ``Null[float]``."""

NullDate: TypeAlias = Null[date]
"""A nullable date column. Alias for ``Null[date]``."""

NullInterval: TypeAlias = Null[timedelta]
"""A nullable interval column. Alias for ``Null[timedelta]``."""


# ---------------------------------------------------------------------------
# Factory functions (field specifiers for @dataclass_transform)
#
# Each function has three overloads where applicable:
# 1. No default → returns the non-null column type (field is required)
# 2. default: T  → returns the non-null column type (field is optional)
# 3. default: None → returns Null[T] (field is nullable and optional)
# ---------------------------------------------------------------------------


@overload
def serial(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Serial: ...


@overload
def serial(
    name: str | None = ...,
    *,
    default: int,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Serial: ...


@overload
def serial(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Null[int]: ...


def serial(
    name: str | None = None,
    *,
    default: int | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    fk: Callable[[], Column[int]] | None = None,
    on_delete: OnDelete | None = None,
) -> Serial | Null[int]:
    """Create a :class:`Serial` column."""
    col: Serial | Null[int]
    if default is None:
        col = Null[int](sql_type="SERIAL", py_type=int, name=name, default=default, primary=primary, not_null=not_null)
    else:
        col = Serial(name=name, default=default, primary=primary, not_null=not_null)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def boolean(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Boolean: ...


@overload
def boolean(
    name: str | None = ...,
    *,
    default: bool,
    primary: bool = ...,
    not_null: bool = ...,
) -> Boolean: ...


@overload
def boolean(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> NullBoolean: ...


def boolean(
    name: str | None = None,
    *,
    default: bool | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Boolean | NullBoolean:
    """Create a :class:`Boolean` column."""
    if default is None:
        return Null[bool](
            sql_type="BOOLEAN", py_type=bool, name=name, default=default, primary=primary, not_null=not_null
        )
    return Boolean(name=name, default=default, primary=primary, not_null=not_null)


@overload
def timestamp(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Timestamp: ...


@overload
def timestamp(
    name: str | None = ...,
    *,
    default: datetime,
    primary: bool = ...,
    not_null: bool = ...,
) -> Timestamp: ...


@overload
def timestamp(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> NullTimestamp: ...


def timestamp(
    name: str | None = None,
    *,
    default: datetime | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Timestamp | NullTimestamp:
    """Create a :class:`Timestamp` column."""
    if default is None:
        return Null[datetime](
            sql_type="TIMESTAMP", py_type=str, name=name, default=default, primary=primary, not_null=not_null
        )
    return Timestamp(name=name, default=default, primary=primary, not_null=not_null)


@overload
def jsonb(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Jsonb: ...


@overload
def jsonb(
    name: str | None = ...,
    *,
    default: dict[str, Any],
    primary: bool = ...,
    not_null: bool = ...,
) -> Jsonb: ...


@overload
def jsonb(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> Null[dict[str, Any]]: ...


def jsonb(
    name: str | None = None,
    *,
    default: dict[str, Any] | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Jsonb | Null[dict[str, Any]]:
    """Create a :class:`Jsonb` column."""
    if default is None:
        return Null[dict[str, Any]](
            sql_type="JSONB", py_type=dict, name=name, default=default, primary=primary, not_null=not_null
        )
    return Jsonb(name=name, default=default, primary=primary, not_null=not_null)


@overload
def smallint(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> SmallInt: ...


@overload
def smallint(
    name: str | None = ...,
    *,
    default: int,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> SmallInt: ...


@overload
def smallint(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> NullSmallInt: ...


def smallint(
    name: str | None = None,
    *,
    default: int | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    fk: Callable[[], Column[int]] | None = None,
    on_delete: OnDelete | None = None,
) -> SmallInt | NullSmallInt:
    """Create a :class:`SmallInt` column."""
    col: SmallInt | Null[int]
    if default is None:
        col = Null[int](
            sql_type="SMALLINT", py_type=int, name=name, default=default, primary=primary, not_null=not_null
        )
    else:
        col = SmallInt(name=name, default=default, primary=primary, not_null=not_null)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def bigint(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> BigInt: ...


@overload
def bigint(
    name: str | None = ...,
    *,
    default: int,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> BigInt: ...


@overload
def bigint(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    fk: Callable[[], Column[int]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> NullBigInt: ...


def bigint(
    name: str | None = None,
    *,
    default: int | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    fk: Callable[[], Column[int]] | None = None,
    on_delete: OnDelete | None = None,
) -> BigInt | NullBigInt:
    """Create a :class:`BigInt` column."""
    col: BigInt | Null[int]
    if default is None:
        col = Null[int](sql_type="BIGINT", py_type=int, name=name, default=default, primary=primary, not_null=not_null)
    else:
        col = BigInt(name=name, default=default, primary=primary, not_null=not_null)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def smallserial(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> SmallSerial: ...


@overload
def smallserial(
    name: str | None = ...,
    *,
    default: int,
    primary: bool = ...,
    not_null: bool = ...,
) -> SmallSerial: ...


@overload
def smallserial(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> Null[int]: ...


def smallserial(
    name: str | None = None,
    *,
    default: int | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> SmallSerial | Null[int]:
    """Create a :class:`SmallSerial` column."""
    if default is None:
        return Null[int](
            sql_type="SMALLSERIAL", py_type=int, name=name, default=default, primary=primary, not_null=not_null
        )
    return SmallSerial(name=name, default=default, primary=primary, not_null=not_null)


@overload
def bigserial(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> BigSerial: ...


@overload
def bigserial(
    name: str | None = ...,
    *,
    default: int,
    primary: bool = ...,
    not_null: bool = ...,
) -> BigSerial: ...


@overload
def bigserial(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> Null[int]: ...


def bigserial(
    name: str | None = None,
    *,
    default: int | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> BigSerial | Null[int]:
    """Create a :class:`BigSerial` column."""
    if default is None:
        return Null[int](
            sql_type="BIGSERIAL", py_type=int, name=name, default=default, primary=primary, not_null=not_null
        )
    return BigSerial(name=name, default=default, primary=primary, not_null=not_null)


@overload
def varchar(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    length: int | None = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Varchar: ...


@overload
def varchar(
    name: str | None = ...,
    *,
    default: str,
    primary: bool = ...,
    not_null: bool = ...,
    length: int | None = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Varchar: ...


@overload
def varchar(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    length: int | None = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> NullVarchar: ...


def varchar(
    name: str | None = None,
    *,
    default: str | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    length: int | None = None,
    fk: Callable[[], Column[str]] | None = None,
    on_delete: OnDelete | None = None,
) -> Varchar | NullVarchar:
    """Create a :class:`Varchar` column."""
    col: Varchar | Null[str]
    if default is None:
        col = Null[str](sql_type="VARCHAR", py_type=str, name=name, default=default, primary=primary, not_null=not_null)
        if length is not None:
            col._extra_args = (length,)
    else:
        col = Varchar(name=name, default=default, primary=primary, not_null=not_null, length=length)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def char_col(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    length: int | None = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Char: ...


@overload
def char_col(
    name: str | None = ...,
    *,
    default: str,
    primary: bool = ...,
    not_null: bool = ...,
    length: int | None = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Char: ...


@overload
def char_col(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    length: int | None = ...,
    fk: Callable[[], Column[str]] | None = ...,
    on_delete: OnDelete | None = ...,
) -> Null[str]: ...


def char_col(
    name: str | None = None,
    *,
    default: str | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    length: int | None = None,
    fk: Callable[[], Column[str]] | None = None,
    on_delete: OnDelete | None = None,
) -> Char | Null[str]:
    """Create a :class:`Char` column."""
    col: Char | Null[str]
    if default is None:
        col = Null[str](sql_type="CHAR", py_type=str, name=name, default=default, primary=primary, not_null=not_null)
        if length is not None:
            col._extra_args = (length,)
    else:
        col = Char(name=name, default=default, primary=primary, not_null=not_null, length=length)
    if fk is not None:
        col.fk(fk, on_delete)
    return col


@overload
def numeric(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    precision: int | None = ...,
    scale: int | None = ...,
) -> Numeric: ...


@overload
def numeric(
    name: str | None = ...,
    *,
    default: Decimal,
    primary: bool = ...,
    not_null: bool = ...,
    precision: int | None = ...,
    scale: int | None = ...,
) -> Numeric: ...


@overload
def numeric(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    precision: int | None = ...,
    scale: int | None = ...,
) -> Null[Decimal]: ...


def numeric(
    name: str | None = None,
    *,
    default: Decimal | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    precision: int | None = None,
    scale: int | None = None,
) -> Numeric | Null[Decimal]:
    """Create a :class:`Numeric` column."""
    if default is None:
        col: Null[Decimal] = Null[Decimal](
            sql_type="NUMERIC", py_type=Decimal, name=name, default=default, primary=primary, not_null=not_null
        )
        if precision is not None:
            if scale is not None:
                col._extra_args = (precision, scale)
            else:
                col._extra_args = (precision,)
        return col
    return Numeric(name=name, default=default, primary=primary, not_null=not_null, precision=precision, scale=scale)


@overload
def pg_decimal(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
    precision: int | None = ...,
    scale: int | None = ...,
) -> PgDecimal: ...


@overload
def pg_decimal(
    name: str | None = ...,
    *,
    default: Decimal,
    primary: bool = ...,
    not_null: bool = ...,
    precision: int | None = ...,
    scale: int | None = ...,
) -> PgDecimal: ...


@overload
def pg_decimal(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
    precision: int | None = ...,
    scale: int | None = ...,
) -> Null[Decimal]: ...


def pg_decimal(
    name: str | None = None,
    *,
    default: Decimal | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
    precision: int | None = None,
    scale: int | None = None,
) -> PgDecimal | Null[Decimal]:
    """Create a :class:`PgDecimal` column."""
    if default is None:
        col: Null[Decimal] = Null[Decimal](
            sql_type="DECIMAL", py_type=Decimal, name=name, default=default, primary=primary, not_null=not_null
        )
        if precision is not None:
            if scale is not None:
                col._extra_args = (precision, scale)
            else:
                col._extra_args = (precision,)
        return col
    return PgDecimal(name=name, default=default, primary=primary, not_null=not_null, precision=precision, scale=scale)


@overload
def double_precision(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> DoublePrecision: ...


@overload
def double_precision(
    name: str | None = ...,
    *,
    default: float,
    primary: bool = ...,
    not_null: bool = ...,
) -> DoublePrecision: ...


@overload
def double_precision(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> NullDoublePrecision: ...


def double_precision(
    name: str | None = None,
    *,
    default: float | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> DoublePrecision | NullDoublePrecision:
    """Create a :class:`DoublePrecision` column."""
    if default is None:
        return Null[float](
            sql_type="DOUBLE PRECISION", py_type=float, name=name, default=default, primary=primary, not_null=not_null
        )
    return DoublePrecision(name=name, default=default, primary=primary, not_null=not_null)


@overload
def json_col(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Json: ...


@overload
def json_col(
    name: str | None = ...,
    *,
    default: dict[str, Any],
    primary: bool = ...,
    not_null: bool = ...,
) -> Json: ...


@overload
def json_col(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> Null[dict[str, Any]]: ...


def json_col(
    name: str | None = None,
    *,
    default: dict[str, Any] | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Json | Null[dict[str, Any]]:
    """Create a :class:`Json` column."""
    if default is None:
        return Null[dict[str, Any]](
            sql_type="JSON", py_type=dict, name=name, default=default, primary=primary, not_null=not_null
        )
    return Json(name=name, default=default, primary=primary, not_null=not_null)


@overload
def time_col(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Time: ...


@overload
def time_col(
    name: str | None = ...,
    *,
    default: time,
    primary: bool = ...,
    not_null: bool = ...,
) -> Time: ...


@overload
def time_col(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> Null[time]: ...


def time_col(
    name: str | None = None,
    *,
    default: time | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Time | Null[time]:
    """Create a :class:`Time` column."""
    if default is None:
        return Null[time](sql_type="TIME", py_type=time, name=name, default=default, primary=primary, not_null=not_null)
    return Time(name=name, default=default, primary=primary, not_null=not_null)


@overload
def date_col(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Date: ...


@overload
def date_col(
    name: str | None = ...,
    *,
    default: date,
    primary: bool = ...,
    not_null: bool = ...,
) -> Date: ...


@overload
def date_col(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> NullDate: ...


def date_col(
    name: str | None = None,
    *,
    default: date | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Date | NullDate:
    """Create a :class:`Date` column."""
    if default is None:
        return Null[date](sql_type="DATE", py_type=date, name=name, default=default, primary=primary, not_null=not_null)
    return Date(name=name, default=default, primary=primary, not_null=not_null)


@overload
def interval(
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Interval: ...


@overload
def interval(
    name: str | None = ...,
    *,
    default: timedelta,
    primary: bool = ...,
    not_null: bool = ...,
) -> Interval: ...


@overload
def interval(
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> NullInterval: ...


def interval(
    name: str | None = None,
    *,
    default: timedelta | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Interval | NullInterval:
    """Create an :class:`Interval` column."""
    if default is None:
        return Null[timedelta](
            sql_type="INTERVAL", py_type=timedelta, name=name, default=default, primary=primary, not_null=not_null
        )
    return Interval(name=name, default=default, primary=primary, not_null=not_null)


def enum_col[E: EmbarEnum](
    pg_enum: type[PgEnum[E]],
    name: str | None = None,
    default: E | _NoDefaultType = NO_DEFAULT,
    *,
    primary: bool = False,
    not_null: bool = False,
) -> EnumCol[E]:
    """Create an :class:`EnumCol` column."""
    return EnumCol(pg_enum, name=name, default=default, primary=primary, not_null=not_null)


@overload
def vector(
    length: int,
    name: str | None = ...,
    *,
    primary: bool = ...,
    not_null: bool = ...,
) -> Vector: ...


@overload
def vector(
    length: int,
    name: str | None = ...,
    *,
    default: list[float],
    primary: bool = ...,
    not_null: bool = ...,
) -> Vector: ...


@overload
def vector(
    length: int,
    name: str | None = ...,
    *,
    default: None,
    primary: bool = ...,
    not_null: bool = ...,
) -> Null[list[float]]: ...


def vector(
    length: int,
    name: str | None = None,
    *,
    default: list[float] | None | _NoDefaultType = NO_DEFAULT,
    primary: bool = False,
    not_null: bool = False,
) -> Vector | Null[list[float]]:
    """Create a :class:`Vector` column."""
    if default is None:
        col: Null[list[float]] = Null[list[float]](
            sql_type="VECTOR", py_type=list, name=name, default=default, primary=primary, not_null=not_null
        )
        col._extra_args = (length,)
        return col
    return Vector(length, name=name, default=default, primary=primary, not_null=not_null)
