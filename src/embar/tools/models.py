from dataclasses import dataclass
from typing import Literal

from embar.migration import Ddl


@dataclass
class MigrateConfig:
    """
    Configuration for the migration tool.
    """

    dialect: Literal["postgresql"]
    db_url: str
    schema_path: str
    migrations_dir: str | None = None


@dataclass
class TableMatch:
    """
    Represents a match between old and new table definitions.
    """

    old_name: str | None
    new_name: str | None
    old_ddl: Ddl | None
    new_ddl: Ddl | None
    match_type: Literal["exact", "renamed", "new", "deleted"]
    similarity_score: float = 1.0


@dataclass
class MigrationDiff:
    """
    Represents a migration diff with compatibility information.
    """

    table_name: str
    old_table_name: str | None
    new_table_name: str | None
    match_type: Literal["exact", "renamed", "new", "deleted"]
    sql: str
    is_backward_compatible: bool
    explanation: str
