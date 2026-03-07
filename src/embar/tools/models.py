from dataclasses import dataclass
from typing import Literal


@dataclass
class MigrateConfig:
    """
    Configuration for the migration tool.
    """

    dialect: Literal["postgresql"]
    db_url: str
    schema_path: str
    migrations_dir: str | None = None
