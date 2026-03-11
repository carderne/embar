import json
from dataclasses import field, make_dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    Protocol,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

try:
    from pydantic import BaseModel

    _PYDANTIC_AVAILABLE = True
except ImportError:
    # Minimal stub so that `class SelectAllPydantic(BaseModel)` and
    # `isinstance(x, BaseModel)` work at runtime even without pydantic.
    # The stub is never used for actual validation — that path is guarded
    # by _require_pydantic().
    class BaseModel:
        """Stub used when pydantic is not installed."""

        pass

    _PYDANTIC_AVAILABLE = False

if TYPE_CHECKING:
    # Re-import the real thing for the type checker.
    from pydantic import BaseModel

from embar.column.base import ColumnBase
from embar.db.base import DbType
from embar.query.many import ManyColumn, ManyTable, OneTable
from embar.sql import Sql
from embar.table_base import TableBase


def _require_pydantic(feature: str) -> None:
    """Raise a clear ImportError if pydantic is not installed."""
    try:
        import pydantic  # noqa: F401
    except ImportError:
        raise ImportError(f"{feature} requires pydantic. Install it with: pip install 'embar[pydantic]'") from None


class DataclassType(Protocol):
    """Protocol for plain (non-pydantic) dataclass models."""

    __dataclass_fields__: ClassVar[dict[str, Any]]


class HasAnnotations(Protocol):
    """
    Protocol satisfied by any class that carries `__annotations__` — i.e. every
    Python class that declares at least one field-level type hint.

    This is the minimal structural requirement for `to_sql_columns` and
    `load_dataclass` to work: they only need `get_type_hints()` to succeed.
    """

    __annotations__: ClassVar[dict[str, Any]]


type DataModel = BaseModel | DataclassType | HasAnnotations


class SelectAllPydantic(BaseModel):
    """
    `SelectAll` version that validates with Pydantic.
    """

    ...


class SelectAllDataclass:
    """
    `SelectAll` version that doesn't validate (plain dataclass).
    """

    __dataclass_fields__: ClassVar[dict[str, Any]] = {}


def to_sql_columns(model: type[DataModel], db_type: DbType) -> str:
    parts: list[str] = []
    hints = get_type_hints(model, include_extras=True)
    for field_name, field_type in hints.items():
        source = _get_source_expr(field_name, field_type, db_type, hints)
        target = field_name
        parts.append(f'{source} AS "{target}"')

    return ", ".join(parts)


def _get_source_expr(field_name: str, field_type: type, db_type: DbType, hints: dict[str, Any]) -> str:
    """
    Get the source expression for the given field.

    It could be a simple column reference, a table or `Many` reference,
    or even a ['Sql'][embar.sql.Sql] query.
    """
    field_type = hints[field_name]
    if get_origin(field_type) is Annotated:
        annotations = get_args(field_type)
        # Skip first arg (the actual type), search metadata for TableColumn
        for annotation in annotations[1:]:
            if isinstance(annotation, ColumnBase):
                return annotation.info.fqn()
            if isinstance(annotation, ManyColumn):
                # not sure why this cast is needed
                # pyright doesn't figure out the ManyColumn is always [ColumnBase]?
                many_col = cast(ManyColumn[ColumnBase], annotation)
                fqn = many_col.of.info.fqn()
                match db_type:
                    case "postgres":
                        query = f"array_agg({fqn})"
                        return query
                    case "sqlite":
                        query = f"json_group_array({fqn})"
                        return query
            if isinstance(annotation, OneTable):
                one_table = cast(OneTable[type[TableBase]], annotation)
                table = one_table.of
                table_fqn = table.fqn()
                columns = table.column_names()
                column_pairs = ", ".join(
                    [f"'{field_name}', {table_fqn}.\"{col_name}\"" for field_name, col_name in columns.items()]
                )
                match db_type:
                    case "postgres":
                        query = f"json_build_object({column_pairs})"
                        return query
                    case "sqlite":
                        query = f"json_object({column_pairs})"
                        return query
            if isinstance(annotation, ManyTable):
                many_table = cast(ManyTable[type[TableBase]], annotation)
                table = many_table.of
                table_fqn = table.fqn()
                columns = table.column_names()
                column_pairs = ", ".join(
                    [f"'{field_name}', {table_fqn}.\"{col_name}\"" for field_name, col_name in columns.items()]
                )
                match db_type:
                    case "postgres":
                        query = f"json_agg(json_build_object({column_pairs}))"
                        return query
                    case "sqlite":
                        query = f"json_group_array(json_object({column_pairs}))"
                        return query
            if isinstance(annotation, Sql):
                query = annotation.sql()
                return query

    raise Exception(f"Failed to get source expression for {field_name}")


def _convert_annotation(
    field_type: type,
    use_pydantic: bool,
) -> Annotated[Any, Any] | Literal[False]:
    """
    Extract complex annotated types from `Annotated[int, MyTable.my_col]` expressions.

    If the annotated type is a column reference then this does nothing and returns false.

    ```python
    from typing import Annotated
    from pydantic import BaseModel
    from embar.column.common import Text, text
    from embar.table import Table
    from embar.model import _convert_annotation
    class MyTable(Table):
        my_col: Text = text()
    class MyModel(BaseModel):
        my_col: Annotated[str, MyTable.my_col]
    ```
    """
    if get_origin(field_type) is Annotated:
        annotations = get_args(field_type)
        # Skip first arg (the actual type), search metadata for TableColumn
        for annotation in annotations[1:]:
            if isinstance(annotation, ManyTable):
                many_table = cast(ManyTable[type[TableBase]], annotation)
                inner_type = many_table.of
                dc = generate_model(inner_type, use_pydantic)
                new_type = Annotated[list[dc], annotation]
                return new_type

            if isinstance(annotation, OneTable):
                one_table = cast(OneTable[type[TableBase]], annotation)
                inner_type = one_table.of
                dc = generate_model(inner_type, use_pydantic)
                new_type = Annotated[dc, annotation]
                return new_type
    return False


@overload
def generate_model(cls: type[TableBase], use_pydantic: Literal[True]) -> type[BaseModel]: ...
@overload
def generate_model(cls: type[TableBase], use_pydantic: Literal[False]) -> type[DataclassType]: ...
@overload
def generate_model(cls: type[TableBase], use_pydantic: bool) -> type[DataModel]: ...


def generate_model(cls: type[TableBase], use_pydantic: bool) -> type[DataModel]:
    if use_pydantic:
        return generate_pydantic_model(cls)
    return generate_dataclass_model(cls)


def generate_pydantic_model(cls: type[TableBase]) -> type[BaseModel]:
    """
    Create a Pydantic model based on a `Table`.

    Note the new model has the same exact name, maybe something to revisit.

    ```python
    from embar.table import Table
    from embar.model import generate_pydantic_model
    class MyTable(Table): ...
    generate_pydantic_model(MyTable)
    ```
    """
    _require_pydantic("generate_pydantic_model")
    from pydantic import BeforeValidator, create_model
    from pydantic import Field as PydanticField

    fields_dict: dict[str, Any] = {}
    for field_name, column in cls._fields.items():  # pyright:ignore[reportPrivateUsage]
        field_type = column.info.py_type

        if column.info.col_type == "VECTOR":
            field_type = Annotated[field_type, BeforeValidator(_parse_json_list)]

        fields_dict[field_name] = (
            Annotated[field_type, column],
            PydanticField(default_factory=lambda a=column: column.info.fqn()),
        )

    model = create_model(cls.__name__, **fields_dict)
    model.model_rebuild()
    return model


def generate_dataclass_model(cls: type[TableBase]) -> type[DataclassType]:
    """
    Create a plain dataclass based on a `Table` (no Pydantic validation).

    Fields are typed as `Annotated[py_type, column]` so that `to_sql_columns`
    can discover the SQL column reference.

    Note the new dataclass has the same exact name, maybe something to revisit.

    ```python
    from embar.table import Table
    from embar.model import generate_dataclass_model
    class MyTable(Table): ...
    generate_dataclass_model(MyTable)
    ```
    """
    dc_fields: list[Any] = []
    for field_name, column in cls._fields.items():  # pyright:ignore[reportPrivateUsage]
        field_type = column.info.py_type
        # Use Annotated so to_sql_columns can find the column reference
        annotated_type = Annotated[field_type, column]
        dc_fields.append(
            (
                field_name,
                annotated_type,
                field(default=None),
            )
        )

    data_class = make_dataclass(cls.__name__, dc_fields)
    return data_class


def upgrade_model_nested_fields[B: DataModel](model: type[B], use_pydantic: bool) -> type[B]:
    """
    Upgrade a model so that nested `ManyTable`/`OneTable` fields are resolved to concrete models.

    For Pydantic models, creates a new subclass via `create_model`.
    For plain dataclasses/annotated classes, creates a new dataclass with upgraded field types.

    ``use_pydantic`` controls whether nested table models are generated as Pydantic models
    or plain dataclasses, and must be supplied explicitly by the caller.
    """
    type_hints = get_type_hints(model, include_extras=True)

    if isinstance(model, type) and issubclass(model, BaseModel) and _PYDANTIC_AVAILABLE:
        from pydantic import create_model

        fields_dict: dict[str, Any] = {}
        for field_name, field_type in type_hints.items():
            new_type = _convert_annotation(field_type, use_pydantic=True)
            if new_type:
                fields_dict[field_name] = (new_type, None)
            else:
                fields_dict[field_name] = (field_type, None)

        new_class = create_model(model.__name__, __base__=model, **fields_dict)
        new_class.model_rebuild()
        return new_class

    # Plain dataclass / annotated-class path
    dc_fields: list[Any] = []
    for field_name, field_type in type_hints.items():
        new_type = _convert_annotation(field_type, use_pydantic=use_pydantic)
        resolved_type = new_type if new_type else field_type
        dc_fields.append((field_name, resolved_type, field(default=None)))

    new_class = make_dataclass(model.__name__, dc_fields)
    return new_class  # type: ignore[return-value]


def load_results[T](model: type[T], data: list[dict[str, Any]]) -> list[T]:
    """
    Load query result rows into model instances.

    Dispatches between Pydantic validation (for ``BaseModel`` subclasses) and
    the plain dict→dataclass loader for everything else.
    """
    if isinstance(model, type) and issubclass(model, BaseModel):
        from pydantic import TypeAdapter

        adapter = TypeAdapter(list[model])
        return adapter.validate_python(data)
    return load_dataclass(model, data)


def load_dataclass[T](model: type[T], data: list[dict[str, Any]]) -> list[T]:
    """
    Load a list of row dicts into plain dataclass/annotated-class instances
    (no Pydantic validation).

    Handles nested dataclasses (from ManyTable/OneTable annotations) by recursively
    loading JSON objects/arrays from the database into the appropriate types.
    """
    return [_load_one(model, row) for row in data]


def _load_one[T](model: type[T], row: dict[str, Any]) -> T:
    """
    Load a single row dict into a dataclass instance.
    """
    hints = get_type_hints(model, include_extras=True)
    kwargs: dict[str, Any] = {}
    for field_name, field_type in hints.items():
        raw = row.get(field_name)
        kwargs[field_name] = _coerce_field(field_type, raw)
    return model(**kwargs)


def _coerce_field(field_type: type, value: Any) -> Any:
    """
    Coerce a raw value into the expected Python type for a dataclass field.

    Handles nested dataclasses (list[SomeDataclass] or SomeDataclass) by parsing
    JSON strings/dicts from the database.
    """
    if value is None:
        return None

    origin = get_origin(field_type)
    args = get_args(field_type)

    # Unwrap Annotated[T, ...]
    if origin is Annotated:
        return _coerce_field(args[0], value)

    # list[SomeDataclass] — parameterised list, e.g. list[Message]
    if origin is list and args:
        inner = args[0]
        if _is_plain_dataclass(inner):
            items = value if isinstance(value, list) else json.loads(value)
            return [_load_one(inner, item) for item in items]
        return value

    # Bare list (no type args) — used by VECTOR columns whose py_type is plain `list`.
    # The DB returns either a Python list (postgres array) or a JSON string (sqlite).
    if field_type is list:
        return value if isinstance(value, list) else json.loads(value)

    # SomeDataclass
    if _is_plain_dataclass(field_type):
        data = value if isinstance(value, dict) else json.loads(value)
        return _load_one(field_type, data)

    return value


def _is_plain_dataclass(t: Any) -> bool:
    """Return True if `t` is a plain (non-Pydantic) dataclass type."""
    return isinstance(t, type) and hasattr(t, "__dataclass_fields__") and not issubclass(t, BaseModel)


def _parse_json_list(v: Any):
    if isinstance(v, str):
        return json.loads(v)
    return v
