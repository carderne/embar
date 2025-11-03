from dataclasses import field, make_dataclass
from typing import (
    Annotated,
    Any,
    ClassVar,
    Literal,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
    get_type_hints,
    override,
)

from embar.column.base import ColumnBase
from embar.db.base import DbType
from embar.query.many import ManyColumn, ManyTable
from embar.sql import Sql
from embar.table_base import TableBase


@dataclass_transform(kw_only_default=True)
class Selection:
    """
    `Selection` is the base class for [`SelectQuery`][embar.query.select.SelectQuery] queries.

    ```python
    from typing import Annotated
    from embar.column.common import Text
    from embar.table import Table
    from embar.query.selection import Selection
    class MyTable(Table):
        my_col: Text = Text()
    class MySelection(Selection):
        my_col: Annotated[str, MyTable.my_col]
    ```
    """

    _fields: ClassVar[dict[str, type]]

    def __init__(self, **kwargs: Any):
        """
        Minimal replication of `dataclass` behaviour.
        """
        for field_name in self.__class__.__annotations__:
            if field_name not in kwargs:
                raise TypeError(f"missing required argument: '{field_name}'")
            setattr(self, field_name, kwargs[field_name])

    def __init_subclass__(cls, **kwargs: Any):
        """
        Populate `_fields` if not provided.
        """
        hints = get_type_hints(cls, include_extras=True)
        # _fields is what embar uses to track fields
        cls._fields = {k: v for k, v in hints.items() if get_origin(v) is Annotated}

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Selection):
            return False
        return all(getattr(self, f) == getattr(other, f) for f in self._fields)

    @classmethod
    def to_sql_columns(cls, db_type: DbType) -> str:
        parts: list[str] = []
        hints = get_type_hints(cls, include_extras=True)
        for field_name, field_type in cls._fields.items():
            source = _get_source_expr(field_name, field_type, db_type, hints)
            target = field_name
            parts.append(f'{source} AS "{target}"')

        return ", ".join(parts)


class SelectAll(Selection):
    """
    `SelectAll` tells the query engine to get all fields from the `from()` table ONLY.

    Ideally it could get fields from joined tables too, but no way for that to work (from a typing POV)
    Not recommended for public use, users should rather use their table's `all()` method.
    """

    ...


def _get_source_expr(field_name: str, field_type: type, db_type: DbType, hints: dict[str, Any]) -> str:
    """
    Get the source expression for the given `Selection` field.

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
            if isinstance(annotation, type) and issubclass(annotation, TableBase):
                table = annotation
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
                table_fqn = many_table.of.fqn()
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
                query = annotation.execute()
                return query

    raise Exception(f"Failed to get source expression for {field_name}")


def _convert_annotation(
    field_type: type,
) -> Annotated[Any, Any] | Literal[False]:
    """
    Extract complex annotated types from `Annotated[int, MyTable.my_col]` expressions.

    If the annotated type is a column reference then this does nothing and returns false.

    Only used by `embar.query.Select` but more at home here with the `Selection` context where it's used.

    ```python
    from typing import Annotated
    from embar.column.common import Text
    from embar.table import Table
    from embar.query.selection import Selection, _convert_annotation
    class MyTable(Table):
        my_col: Text = Text()
    class MySelection(Selection):
        my_col: Annotated[str, MyTable.my_col]
    field = MySelection._fields["my_col"]
    assert _convert_annotation(field) == False
    """
    if get_origin(field_type) is Annotated:
        annotations = get_args(field_type)
        # Skip first arg (the actual type), search metadata for TableColumn
        for annotation in annotations[1:]:
            if isinstance(annotation, ManyTable):
                many_table = cast(ManyTable[type[TableBase]], annotation)
                inner_type = many_table.of
                dc = generate_selection_dataclass(inner_type)
                new_type = Annotated[list[dc], annotation]
                return new_type

            if isinstance(annotation, type) and issubclass(annotation, TableBase):
                dc = generate_selection_dataclass(annotation)
                return Annotated[dc, annotation]
    return False


def generate_selection_dataclass(cls: type[TableBase]) -> type[Selection]:
    """
    Create a dataclass subclass of `Selection` based on a `Table`.

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

    data_class = make_dataclass(cls.__name__, fields, bases=(Selection,))
    data_class.__init_subclass__()
    return data_class


def selection_to_dataclass[S: Selection](selection: type[S]) -> type[S]:
    selection.__init_subclass__()

    new_fields: list[tuple[str, type]] = []
    for field_name, field_type in selection._fields.items():  # pyright:ignore[reportPrivateUsage]
        new_type = _convert_annotation(field_type)
        if new_type:
            new_fields.append((field_name, new_type))
        else:
            # This means convert_annotation returned False, i.e. it's a 'simple' field.
            # We have to recreate it with a Field tuple to match the stuff above for the legitimately new fields.
            # (I haven't found a way for it to just be left in-place or something.)
            # field_type = cast(type, cls_field.type)
            new_fields.append((field_name, field_type))

    new_class = make_dataclass(selection.__name__, new_fields, bases=(Selection,))

    # Pretty gruesome stuff going on here...
    # __init_subclass__ won't have been called, so _fields won't have been assigned
    # so do it manually...
    new_class.__init_subclass__()

    return new_class
