"""
Ideally table.py would be in a table/ module but then it's impossible
to import table_base.py without triggering table.py, causing a circular loop by the Many stuff
(that's the reason the two were separated in the first place).
"""

from textwrap import dedent, indent
from typing import TYPE_CHECKING, Any, Literal, Self, dataclass_transform, get_args, get_origin, overload

if TYPE_CHECKING:
    from pydantic_core import core_schema as _core_schema

try:
    from pydantic_core import core_schema

    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False

from embar.column.base import ColumnBase
from embar.column.common import Column, Null, float_col, integer, text
from embar.column.pg import (
    bigint,
    bigserial,
    boolean,
    char_col,
    date_col,
    double_precision,
    enum_col,
    interval,
    json_col,
    jsonb,
    numeric,
    pg_decimal,
    serial,
    smallint,
    smallserial,
    time_col,
    timestamp,
    varchar,
    vector,
)
from embar.config import EmbarConfig
from embar.custom_types import Undefined
from embar.model import SelectAllDataclass, SelectAllPydantic
from embar.query.many import ManyTable, OneTable
from embar.table_base import TableBase


@dataclass_transform(
    kw_only_default=True,
    field_specifiers=(
        integer,
        text,
        float_col,
        varchar,
        serial,
        boolean,
        timestamp,
        jsonb,
        smallint,
        bigint,
        smallserial,
        bigserial,
        char_col,
        numeric,
        pg_decimal,
        double_precision,
        json_col,
        time_col,
        date_col,
        interval,
        enum_col,
        vector,
    ),
)
class Table(TableBase):
    """
    All table definitions inherit from `Table`.

    Table is used extensively as both a class/type and as objects.
    - Tables/schemas are created as `class MyTable(Table): ...`
    - Table references (in where clauses, joins, FKs) refer to these types
    - New rows to insert into a table are created as objects
    """

    def __init_subclass__(cls, **kwargs: Any):
        """
        Populate `_fields` and the `embar_config` if not provided.
        """
        cls._fields = {name: attr for name, attr in cls.__dict__.items() if isinstance(attr, ColumnBase)}

        if cls.embar_config == Undefined:
            cls.embar_config: EmbarConfig = EmbarConfig()
            cls.embar_config.__set_name__(cls, "embar_config")

        cls._validate_column_annotations()
        super().__init_subclass__(**kwargs)

    @classmethod
    def _validate_column_annotations(cls) -> None:
        """
        Validate that column annotations match their field specifiers.

        Checks both the base type (e.g. Text vs Integer) and nullability
        (e.g. NullText vs Text).
        """
        annotations = cls.__annotations__
        for name, col in cls._fields.items():
            if name not in annotations:
                continue
            ann = annotations[name]
            origin = get_origin(ann)

            if origin is Null:
                # Annotation is Null[T] — column must be a Null instance
                if not isinstance(col, Null):
                    raise TypeError(
                        f"{cls.__name__}.{name}: annotation is nullable ({ann}) "
                        f"but field specifier returns non-nullable {type(col).__name__}"
                    )
                # Check that T matches the column's py_type
                ann_args = get_args(ann)
                if ann_args and col._py_type != ann_args[0]:
                    raise TypeError(
                        f"{cls.__name__}.{name}: annotation is Null[{ann_args[0].__name__}] "
                        f"but field specifier has py_type={col._py_type.__name__}"
                    )
                # Nullable annotation but not_null=True in DB — always wrong
                if col._not_null:
                    raise TypeError(
                        f"{cls.__name__}.{name}: annotation is nullable ({ann}) but field specifier has not_null=True"
                    )
            elif isinstance(ann, type) and issubclass(ann, Column):
                # Annotation is a concrete Column subclass (e.g. Text, Integer)
                if isinstance(col, Null):
                    raise TypeError(
                        f"{cls.__name__}.{name}: annotation is non-nullable ({ann.__name__}) "
                        f"but field specifier returns nullable Null"
                    )
                if not isinstance(col, ann):
                    raise TypeError(
                        f"{cls.__name__}.{name}: annotation type is {ann.__name__} "
                        f"but field specifier returns {type(col).__name__}"
                    )

    def __init__(self, **kwargs: Any) -> None:
        """
        Minimal replication of `dataclass` behaviour.
        """
        columns: dict[str, type[Column[Any]]] = {
            name: attr for name, attr in type(self).__dict__.items() if isinstance(attr, ColumnBase)
        }

        for name, value in kwargs.items():
            if name not in columns:
                raise TypeError(f"Unknown field: {name}")
            setattr(self, name, value)

        # Handle defaults for missing fields
        missing = set(columns.keys()) - set(kwargs.keys())
        for name in list(missing):
            if columns[name].has_default:
                setattr(self, name, columns[name].default)
                missing.remove(name)

        if missing:
            raise TypeError(f"Missing required fields: {missing}")

    if _PYDANTIC_AVAILABLE:

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            source_type: Any,
            handler: Any,
        ) -> "_core_schema.CoreSchema":
            return core_schema.any_schema()

    @classmethod
    def many(cls) -> ManyTable[type[Self]]:
        """
        Used to nest many of another table in a column in a model

        ```python
        from typing import Annotated
        from pydantic import BaseModel
        from embar.table import Table
        class MyTable(Table): ...
        class MyModel(BaseModel):
            messages: Annotated[list[MyTable], MyTable.many()]
        ```
        """
        return ManyTable[type[Self]](cls)

    @classmethod
    def one(cls) -> OneTable[type[Self]]:
        """
        Used to nest one of another table in a column in a model
        """
        return OneTable[type[Self]](cls)

    @classmethod
    def ddl(cls) -> str:
        """
        Generate a full DDL for the table.
        """
        columns: list[str] = []
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                columns.append(attr.info.ddl())
        columns_str = ",\n".join(columns)
        columns_str = indent(columns_str, "    ")

        sql = f"""
CREATE TABLE IF NOT EXISTS {cls.fqn()} (
{columns_str}
);"""

        sql = dedent(sql).strip()

        return sql

    @overload
    @classmethod
    def all(cls) -> type[SelectAllPydantic]: ...
    @overload
    @classmethod
    def all(cls, use_pydantic: Literal[True]) -> type[SelectAllPydantic]: ...
    @overload
    @classmethod
    def all(cls, use_pydantic: Literal[False]) -> type[SelectAllDataclass]: ...

    @classmethod
    def all(cls, use_pydantic: bool = True) -> type[SelectAllPydantic] | type[SelectAllDataclass]:
        """
        Generate a Select query model that returns all the table's fields.

        ```python
        from embar.model import SelectAllPydantic
        from embar.table import Table
        class MyTable(Table): ...
        model = MyTable.all()
        assert model == SelectAllPydantic
        ```
        """
        if use_pydantic:
            if not _PYDANTIC_AVAILABLE:
                raise ImportError(
                    "Table.all() requires pydantic when use_pydantic=True (the default). "
                    "Either install it with: pip install 'embar[pydantic]' "
                    "or opt in to the plain-dataclass path with: MyTable.all(use_pydantic=False)"
                )
            return SelectAllPydantic
        return SelectAllDataclass

    def value_dict(self) -> dict[str, Any]:
        """
        Result is keyed to DB column names, _not_ field names.
        """
        result: dict[str, Any] = {}
        for attr_name, attr in self.__class__.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                result[attr.info.name] = getattr(self, attr_name)
        return result
