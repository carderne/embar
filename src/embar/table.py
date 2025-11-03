"""
Ideally table.py would be in a table/ module but then it's impossible
to import table_base.py without triggering table.py, causing a circular loop by the Many stuff
(that's the reason the two were separated in the first place).
"""

from typing import Any, Self, dataclass_transform

from embar.column.base import ColumnBase
from embar.column.common import Column, Integer, Text
from embar.config import EmbarConfig
from embar.custom_types import Undefined
from embar.query.many import ManyTable
from embar.query.selection import SelectAll
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
    """

    def __init_subclass__(cls, **kwargs: Any):
        """
        Populate `_fields` and the `embar_config` if not provided.
        """
        cls._fields = {name: attr for name, attr in cls.__dict__.items() if isinstance(attr, ColumnBase)}  # pyright:ignore[reportUnannotatedClassAttribute]

        if cls.embar_config == Undefined:
            cls.embar_config: EmbarConfig = EmbarConfig()
            cls.embar_config.__set_name__(cls, "embar_config")

        super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs: Any) -> None:
        """
        Minimal replication of `dataclass` behaviour.
        """
        columns: dict[str, type[Column[Any]]] = {  # pyright:ignore[reportAssignmentType]
            name: attr for name, attr in type(self).__dict__.items() if isinstance(attr, ColumnBase)
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
    def many(cls) -> ManyTable[type[Self]]:
        """
        Used to nest many of another table in a column in a [`Selection`][embar.query.selection.Selection].

        ```python
        from typing import Annotated
        from embar.query.selection import Selection
        from embar.table import Table
        class MyTable(Table): ...
        class MySelectQuery(Selection):
            messages: Annotated[list[MyTable], MyTable.many()]
        ```
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

    @classmethod
    def all(cls) -> type[SelectAll]:
        """
        Generate a Select query `Selection` that returns all the table's fields.

        ```python
        from embar.query.selection import SelectAll
        from embar.table import Table
        class MyTable(Table): ...
        selection = MyTable.all()
        assert selection == SelectAll
        ```
        """
        return SelectAll

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
