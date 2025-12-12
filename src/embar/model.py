from dataclasses import field, make_dataclass
from typing import (
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

from pydantic import BaseModel, create_model
from pydantic import Field as PydanticField

from embar.column.base import ColumnBase
from embar.db.base import DbType
from embar.query.many import ManyColumn, ManyTable, OneTable
from embar.sql import Sql
from embar.table_base import TableBase


class DataclassType(Protocol):
    __dataclass_fields__: ClassVar[dict[str, type]]


type DataModel = BaseModel | DataclassType


class SelectAllPydantic(BaseModel):
    """
    `SelectAll` version that validates with Pydantic
    """

    ...


class SelectAllDataclass:
    """
    `SelectAll` version that doesn't validate
    """

    __dataclass_fields__: ClassVar[dict[str, type]]


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
    from embar.column.common import Text
    from embar.table import Table
    from embar.model import _convert_annotation
    class MyTable(Table):
        my_col: Text = Text()
    class MyModel(BaseModel):
        my_col: Annotated[str, MyTable.my_col]
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


def generate_model(cls: type[TableBase], use_pydantic: bool) -> type[DataModel]:
    if use_pydantic:
        return generate_pydantic_model(cls)
    return generate_dataclass_model(cls)


def generate_pydantic_model(cls: type[TableBase]) -> type[BaseModel]:
    """
    Create a model based on a `Table`.

    Note the new table has the same exact name, maybe something to revisit.

    ```python
    from embar.table import Table
    from embar.model import generate_model
    class MyTable(Table): ...
    generate_model(MyTable)
    ```
    """

    fields_dict: dict[str, Any] = {}
    for field_name, column in cls._fields.items():  # pyright:ignore[reportPrivateUsage]
        field_type = column.info.py_type
        fields_dict[field_name] = (
            Annotated[field_type, column],
            PydanticField(default_factory=lambda a=column: column.info.fqn()),
        )

    model = create_model(cls.__name__, **fields_dict)
    model.model_rebuild()
    return model


def generate_dataclass_model(cls: type[TableBase]) -> type[DataclassType]:
    """
    Create a dataclass based on a `Table`.

    Note the new table has the same exact name, maybe something to revisit.

    ```python
    from embar.table import Table
    from embar.query.selection import generate_selection_dataclass
    class MyTable(Table): ...
    generate_selection_dataclass(MyTable)
    ```
    """
    fields: list[tuple[str, Annotated[Any, Any], Any]] = []
    for field_name, column in cls._fields.items():  # pyright:ignore[reportPrivateUsage]
        field_type = column.info.py_type
        fields.append(
            (
                field_name,
                Annotated[field_type, column],
                field(default_factory=lambda a=column: column.info.fqn()),
            )
        )

    data_class = make_dataclass(cls.__name__, fields)
    data_class.__init_subclass__()
    return data_class


def upgrade_model_nested_fields[B: DataModel](model: type[B]) -> type[B]:
    """
    Get nested field models into root model.
    """
    type_hints = get_type_hints(model, include_extras=True)

    if issubclass(model, BaseModel):
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

    model.__init_subclass__()

    new_fields: list[tuple[str, type]] = []
    for field_name, field_type in model.__dataclass_fields__.items():
        new_type = _convert_annotation(field_type, False)
        if new_type:
            new_fields.append((field_name, new_type))
        else:
            # This means convert_annotation returned False, i.e. it's a 'simple' field.
            # We have to recreate it with a Field tuple to match the stuff above for the legitimately new fields.
            # (I haven't found a way for it to just be left in-place or something.)
            # field_type = cast(type, cls_field.type)
            new_fields.append((field_name, field_type))

    new_class = make_dataclass(model.__name__, new_fields)

    # Pretty gruesome stuff going on here...
    # __init_subclass__ won't have been called, so _fields won't have been assigned
    # so do it manually...
    new_class.__init_subclass__()

    return new_class
