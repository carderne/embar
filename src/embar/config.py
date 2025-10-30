from dataclasses import dataclass

from embar.custom_types import Undefined


@dataclass
class TableConfig:
    table_name: str = Undefined
