"""Postgres-specific column types."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, override

from embar.column.base import EnumBase
from embar.column.common import Column, Float, Integer, Text
from embar.custom_types import Type

# Re-export the common types as well as any new ones defined below
__all__ = [
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
        default: str | None = None,
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
        default: str | None = None,
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
        default: Decimal | None = None,
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
        default: Decimal | None = None,
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
    from embar.column.pg import EmbarEnum, EnumCol, PgEnum
    class StatusEnum(EmbarEnum):
       PENDING = auto()
       DONE = auto()
    class StatusPgEnum(PgEnum[StatusEnum]):
        name: str = "status_enum"
        enum: type[StatusEnum] = StatusEnum
    class TableWithStatus(Table):
        status: EnumCol[StatusEnum] = EnumCol(StatusPgEnum)
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
        default: E | None = None,
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
        default: list[float] | None = None,
        primary: bool = False,
        not_null: bool = False,
    ):
        """
        Create a new Vector instance.
        """
        self._extra_args: tuple[int] | tuple[int, int] | None = (length,)
        super().__init__(name=name, default=default, primary=primary, not_null=not_null)
