from dataclasses import dataclass

from pudl.column.base import ColumnBase


@dataclass
class TableBase:
    """
    Base class for `Table` classes.

    The split between `Table` and `TableBase` is a bit arbitrary, mostly
    dictated by preventing circular imports.
    """

    # TODO: the `_name` field seems to get included when ser/de?
    _name: str = ""

    @classmethod
    def fqn(cls) -> str:
        """
        Get the "Fully Qualified Name" of the table (i.e. with quotes).
        """
        return f'"{cls._name}"'

    @classmethod
    def column_names(cls) -> dict[str, str]:
        """
        Mapping of field names to _unquoted_ column names.

        Column names are allowed to be different to field names, so in queries
        we always need to map one to/from the other.
        """
        columns: dict[str, str] = {}
        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr, ColumnBase):
                columns[attr_name] = attr.info.name
        return columns
