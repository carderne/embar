from typing import ClassVar

from embar.column.base import ColumnBase
from embar.config import TableConfig
from embar.custom_types import Undefined


class TableBase:
    """
    Base class for `Table` classes.

    The split between `Table` and `TableBase` is a bit arbitrary, mostly
    dictated by preventing circular imports.
    """

    embar_config: TableConfig = Undefined
    _fields: ClassVar[dict[str, ColumnBase]]

    @classmethod
    def get_name(cls) -> str:
        """
        Get the table's _database_ name.
        """
        return cls.embar_config.table_name

    @classmethod
    def fqn(cls) -> str:
        """
        Get the "Fully Qualified Name" of the table (i.e. with quotes).
        """
        return f'"{cls.embar_config.table_name}"'
