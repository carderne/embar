"""
Ideally table.py would be in a table/ module but then it's impossible
to import table_base.py without triggering table.py, causing a circular loop by the Many stuff
(that's the reason the two were separated in the first place).
"""

from typing import Any, ClassVar, Self, dataclass_transform

from embar.column.base import ColumnBase
from embar.column.common import Column, Integer, Text
from embar.config import TableConfig
from embar.custom_types import Undefined
from embar.query.many import ManyTable
from embar.table_base import TableBase


@dataclass_transform(kw_only_default=True, field_specifiers=(Integer, Text, Integer.fk))
class Table(TableBase):
    """
    All table definitions inherit from `Table`.

    Table is used extensively as both a class/type and as objects.
    - Tables/schemas are created as `class MyTable(Table): ...`
    - Table references (in where clauses, joins, FKs) refer to these types
    - New rows to insert into a table are created as objects
    - Values returned from Select queries are based on dynamically generated classes or
      `Selection` classes, never directly instances of `Table`

    It's a `dataclass` so that [`topological_sort_tables`][embar._util.topological_sort_tables]
    can pick up the fields.
    """

    _fields: ClassVar[dict[str, ColumnBase]]

    def __init_subclass__(cls, **kwargs: Any):
        """
        Populate `_fields` and the `embar_config` if not provided.
        """
        cls._fields = {name: attr for name, attr in cls.__dict__.items() if isinstance(attr, ColumnBase)}

        if cls.embar_config == Undefined:
            cls.embar_config: TableConfig = TableConfig()

        # Set table_name if not provided
        if cls.embar_config.table_name == Undefined:
            cls.embar_config.table_name = "".join("_" + c.lower() if c.isupper() else c for c in cls.__name__).lstrip(
                "_"
            )
        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        """
        Minimal replication of `dataclass` behaviour.
        """
        columns: dict[str, type[Column[Any]]] = {  # pyright:ignore[reportUnknownVariableType,reportAssignmentType]
            name: attr for name, attr in type(self).__dict__.items() if isinstance(attr, Column)
        }

        for name, value in kwargs.items():
            if name not in columns:
                raise TypeError(f"Unknown field: {name}")
            setattr(self, name, value)

        # Handle defaults for missing fields
        missing = set(columns.keys()) - set(kwargs.keys())
        for name in list(missing):
            if columns[name].default is not None:  # pyright:ignore[reportGeneralTypeIssues]
                setattr(self, name, columns[name].default)  # pyright:ignore[reportGeneralTypeIssues]
                missing.remove(name)

        if missing:
            raise TypeError(f"Missing required fields: {missing}")

    @classmethod
    def column_names(cls) -> dict[str, str]:
        """
        Mapping of field names to _unquoted_ column names.

        Column names are allowed to be different to field names, so in queries
        we always need to map one to/from the other.
        """
        cols = {name: col.info.name for name, col in cls._fields.items()}
        return cols

    @classmethod
    def many(cls) -> ManyTable[type[Self]]:
        """
        Used to nest many of another table in a column in a [`Selection`][embar.selection.Selection].

        Example:
        >>> from typing import Annotated
        >>> from embar.query.selection import Selection
        >>> class MyTable(Table): ...
        >>> class MySelectQuery(Selection):
        ...     messages: Annotated[list[MyTable], MyTable.many()]
        """
        return ManyTable[type[Self]](cls)

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
        columns_str = ",".join(columns)
        return f"""CREATE TABLE IF NOT EXISTS {cls.fqn()} ({columns_str});"""

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
