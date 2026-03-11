"""Base class for table definitions."""

from typing import ClassVar

from embar.column.base import ColumnBase
from embar.config import EmbarConfig
from embar.custom_types import Undefined


class TableBase:
    """
    Base class for `Table` classes.

    The split between `Table` and `TableBase` is a bit arbitrary, mostly
    dictated by preventing circular imports.
    """

    embar_config: EmbarConfig = Undefined
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
    def returning_clause(cls) -> str:
        """
        Build a ``RETURNING`` clause that aliases every DB column back to its
        Python field name.

        When field name and DB column name are the same this produces::

            RETURNING "id", "content"

        When they differ (e.g. ``email`` → ``user_email``) this produces::

            RETURNING "user_email" AS "email", "id"

        Using explicit aliases instead of ``RETURNING *`` ensures that
        ``load_results`` can always match columns to model fields by their
        Python field names, regardless of any custom DB column name.
        """
        parts: list[str] = []
        for field_name, col in cls._fields.items():
            db_col = col.info.name
            if db_col == field_name:
                parts.append(f'"{db_col}"')
            else:
                parts.append(f'"{db_col}" AS "{field_name}"')
        return "RETURNING " + ", ".join(parts)
