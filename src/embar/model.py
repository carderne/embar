import json
from typing import (
    Annotated,
    Any,
    Literal,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel, BeforeValidator, Field, create_model

from embar.column.base import ColumnBase
from embar.db.base import DbType
from embar.query.many import ManyColumn, ManyTable, OneTable
from embar.sql import Sql
from embar.table_base import TableBase


class SelectAll(BaseModel):
    """
    `SelectAll` tells the query engine to get all fields from the `from()` table ONLY.

    Ideally it could get fields from joined tables too, but no way for that to work (from a typing POV)
    Not recommended for public use, users should rather use their table's `all()` method.
    """

    ...


def to_sql_columns(model: type[BaseModel], db_type: DbType) -> str:
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
) -> Annotated[Any, Any] | Literal[False]:
    """
    Extract complex annotated types from `Annotated[int, MyTable.my_col]` expressions.

    If the annotated type is a column reference then this does nothing and returns false.

    Only used by `embar.query.Select` but more at home here with the context where it's used.

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
                dc = generate_model(inner_type)
                new_type = Annotated[list[dc], annotation]
                return new_type

            if isinstance(annotation, OneTable):
                one_table = cast(OneTable[type[TableBase]], annotation)
                inner_type = one_table.of
                dc = generate_model(inner_type)
                new_type = Annotated[dc, annotation]
                return new_type
    return False


def generate_model(cls: type[TableBase]) -> type[BaseModel]:
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

        if column.info.col_type == "VECTOR":
            field_type = Annotated[field_type, BeforeValidator(_parse_json_list)]

        fields_dict[field_name] = (
            Annotated[field_type, column],
            Field(default_factory=lambda a=column: column.info.fqn()),
        )

    model = create_model(cls.__name__, **fields_dict)
    model.model_rebuild()
    return model


def upgrade_model_nested_fields[B: BaseModel](model: type[B]) -> type[B]:
    type_hints = get_type_hints(model, include_extras=True)

    fields_dict: dict[str, Any] = {}
    for field_name, field_type in type_hints.items():
        new_type = _convert_annotation(field_type)
        if new_type:
            fields_dict[field_name] = (new_type, None)
        else:
            fields_dict[field_name] = (field_type, None)

    new_class = create_model(model.__name__, __base__=model, **fields_dict)
    new_class.model_rebuild()

    return new_class


def _parse_json_list(v: Any):
    if isinstance(v, str):
        return json.loads(v)
    return v
