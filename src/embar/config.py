"""Configuration for table definitions."""

from typing import Any

from embar.constraint_base import Constraint
from embar.custom_types import Undefined


class EmbarConfig:
    """
    Configuration for table definitions.

    Holds table name and constraints.
    """

    table_name: str = Undefined
    constraints: list[Constraint]

    def __init__(
        self,
        table_name: str | None = None,
        constraints: list[Constraint] | None = None,
    ):
        """
        Create a new EmbarConfig instance.
        """
        if table_name is not None:
            self.table_name = table_name
        self.constraints = constraints if constraints is not None else []

    def __set_name__(self, owner: Any, attr_name: str):
        """
        This runs after __init__ and sets the name (if unset) from containing class.
        """
        if self.table_name == Undefined:
            self.table_name = "".join("_" + c.lower() if c.isupper() else c for c in owner.__name__).lstrip("_")
