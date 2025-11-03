import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from textwrap import dedent
from typing import Literal
from urllib.request import Request, urlopen

import psycopg
import yaml

from embar.db.pg import Db as PgDb
from embar.migration import Ddl
from embar.query.query import Query


@dataclass
class MigrateConfig:
    dialect: Literal["postgresql"]
    db_url: str
    schema_path: str
    migrations_dir: str | None = None


@dataclass
class TableMatch:
    old_name: str | None
    new_name: str | None
    old_ddl: Ddl | None
    new_ddl: Ddl | None
    match_type: Literal["exact", "renamed", "new", "deleted"]
    similarity_score: float = 1.0


@dataclass
class MigrationDiff:
    table_name: str
    old_table_name: str | None
    new_table_name: str | None
    match_type: Literal["exact", "renamed", "new", "deleted"]
    sql: str
    is_backward_compatible: bool
    explanation: str


def _similarity_score(str1: str, str2: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def _match_tables(db_schema: list[Ddl], new_schema: list[Ddl]) -> list[TableMatch]:
    """Match tables between old and new schemas."""
    matches: list[TableMatch] = []
    used_old: set[str] = set()
    used_new: set[str] = set()

    # First pass: exact matches
    for new_ddl in new_schema:
        for old_ddl in db_schema:
            if new_ddl.name == old_ddl.name:
                matches.append(
                    TableMatch(
                        old_name=old_ddl.name,
                        new_name=new_ddl.name,
                        old_ddl=old_ddl,
                        new_ddl=new_ddl,
                        match_type="exact",
                        similarity_score=1.0,
                    )
                )
                used_old.add(old_ddl.name)
                used_new.add(new_ddl.name)
                break

    # Second pass: find similar names (possible renames)
    remaining_old = [ddl for ddl in db_schema if ddl.name not in used_old]
    remaining_new = [ddl for ddl in new_schema if ddl.name not in used_new]

    for new_ddl in remaining_new:
        best_match = None
        best_score = 0.6  # Threshold for considering it a potential rename

        for old_ddl in remaining_old:
            if old_ddl.name in used_old:
                continue
            score = _similarity_score(new_ddl.name, old_ddl.name)
            if score > best_score:
                best_score = score
                best_match = old_ddl

        if best_match:
            matches.append(
                TableMatch(
                    old_name=best_match.name,
                    new_name=new_ddl.name,
                    old_ddl=best_match,
                    new_ddl=new_ddl,
                    match_type="renamed",
                    similarity_score=best_score,
                )
            )
            used_old.add(best_match.name)
            used_new.add(new_ddl.name)

    # Third pass: new tables
    for new_ddl in new_schema:
        if new_ddl.name not in used_new:
            matches.append(
                TableMatch(
                    old_name=None,
                    new_name=new_ddl.name,
                    old_ddl=None,
                    new_ddl=new_ddl,
                    match_type="new",
                    similarity_score=1.0,
                )
            )

    # Fourth pass: deleted tables
    for old_ddl in db_schema:
        if old_ddl.name not in used_old:
            matches.append(
                TableMatch(
                    old_name=old_ddl.name,
                    new_name=None,
                    old_ddl=old_ddl,
                    new_ddl=None,
                    match_type="deleted",
                    similarity_score=1.0,
                )
            )

    return matches


def _get_schema_from_db(conn: psycopg.Connection) -> list[Ddl]:
    """Extract current database schema as DDL objects."""
    results: list[Ddl] = []

    # Get enums
    enum_query = """
        SELECT
            t.typname as enum_name,
            string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) as enum_values
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE n.nspname = 'public'
        GROUP BY t.typname
        ORDER BY t.typname
    """

    with conn.cursor() as cur:
        cur.execute(enum_query)
        for enum_name, enum_values in cur.fetchall():
            ddl = f"CREATE TYPE {enum_name} AS ENUM ({', '.join(f"'{v}'" for v in enum_values.split(', '))});"
            results.append(Ddl(name=enum_name, ddl=ddl))

    # Get tables
    table_query = """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """

    with conn.cursor() as cur:
        cur.execute(table_query)
        tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        # Get column definitions
        column_query = """
            SELECT
                a.attname,
                pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                a.attnotnull,
                pg_get_expr(d.adbin, d.adrelid) as default_value
            FROM pg_attribute a
            LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
            WHERE a.attrelid = %s::regclass
                AND a.attnum > 0
                AND NOT a.attisdropped
            ORDER BY a.attnum
        """

        with conn.cursor() as cur:
            cur.execute(column_query, (table,))
            columns = cur.fetchall()

        # Build CREATE TABLE statement
        col_defs: list[str] = []
        for col_name, data_type, not_null, default in columns:
            col_def = f"    {col_name} {data_type}"
            if default:
                col_def += f" DEFAULT {default}"
            if not_null:
                col_def += " NOT NULL"
            col_defs.append(col_def)

        ddl = f"CREATE TABLE {table} (\n" + ",\n".join(col_defs) + "\n);"

        # Get constraints
        constraint_query = """
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = %s::regclass
            ORDER BY contype, conname
        """

        constraints: list[str] = []
        with conn.cursor() as cur:
            cur.execute(constraint_query, (table,))
            for con_name, con_def in cur.fetchall():
                constraints.append(f"ALTER TABLE {table} ADD CONSTRAINT {con_name} {con_def};")

        results.append(Ddl(name=table, ddl=ddl, constraints=constraints))

    return results


def _call_anthropic(api_key: str, prompt: str, max_tokens: int = 2000) -> str:
    """Make a request to Anthropic API using urllib."""
    url = "https://api.anthropic.com/v1/messages"

    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    headers = {"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}

    request = Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")

    with urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["content"][0]["text"]


def _llm_diff_table(match: TableMatch, api_key: str) -> MigrationDiff:
    """Use Anthropic Haiku to generate SQL diff for table changes."""

    prompt: str
    # Prepare the prompt based on match type
    if match.match_type == "new" and match.new_ddl is not None:
        prompt = dedent(f"""
        You are a database migration expert. Generate SQL to create this new table:

        NEW TABLE DDL:
        {match.new_ddl.ddl}
        {chr(10).join(match.new_ddl.constraints) if match.new_ddl.constraints else ""}

        Generate the complete SQL statements needed to create this table.
        Return ONLY the SQL statements, no explanations.
        """).strip()

    elif match.match_type == "deleted" and match.old_ddl is not None:
        prompt = dedent(f"""
        You are a database migration expert. Generate SQL to drop this table:

        OLD TABLE DDL:
        {match.old_ddl.ddl}

        Generate the SQL statement to drop this table. Return ONLY the SQL statement, no explanations.
        """).strip()

    elif match.old_ddl is not None and match.new_ddl is not None:  # exact or renamed
        rename_info = (
            f"\nNOTE: Table may have been renamed from '{match.old_name}' to '{match.new_name}'"
            if match.match_type == "renamed"
            else ""
        )

        prompt = dedent(f"""
        You are a database migration expert.
        Compare these two table definitions and generate SQL to migrate from OLD to NEW:{rename_info}

        OLD TABLE DDL:
        {match.old_ddl.ddl}
        {chr(10).join(match.old_ddl.constraints) if match.old_ddl.constraints else ""}

        NEW TABLE DDL:
        {match.new_ddl.ddl}
        {chr(10).join(match.new_ddl.constraints) if match.new_ddl.constraints else ""}

        Generate the SQL statements needed to migrate from OLD to NEW. This may include:
        - ALTER TABLE statements to add/drop/modify columns
        - ALTER TABLE statements to add/drop constraints
        - ALTER TABLE RENAME statements if the table was renamed
        - Any other necessary SQL

        CRITICAL: Return ONLY valid SQL statements that can be executed directly.
        If no changes are needed, return ONLY: -- No changes needed
        DO NOT include explanations, comments (except the "No changes needed" comment), or any non-SQL text.
        """).strip()
    else:
        raise Exception(f"Cannot handle match: {match}")

    # Get SQL from LLM
    sql = _call_anthropic(api_key, prompt, max_tokens=2000).strip()

    # Now check if it's backward compatible
    compatibility_prompt = dedent(f"""
    You are a database migration expert.
    Analyze this SQL migration for backward compatibility.

    SQL MIGRATION:
    {sql}

    A migration is BACKWARD-COMPATIBLE if existing code can continue to work without changes.
    A migration is NON-BACKWARD-COMPATIBLE if it:
    - Deletes or renames columns (breaks existing queries)
    - Deletes tables (breaks existing queries)
    - Renames tables (breaks existing queries)
    - Changes column types in incompatible ways (might break existing code)
    - Adds NOT NULL constraints without defaults (breaks existing inserts)
    - Removes defaults that code relies on

    A migration IS backward-compatible if it only:
    - Adds new columns (especially with defaults or nullable)
    - Adds new constraints that don't affect existing data patterns
    - Adds new indexes
    - Creates new tables

    Respond with ONLY one of these two options:
    1. "BACKWARD-COMPATIBLE: <brief explanation>"
    2. "NON-BACKWARD-COMPATIBLE: <brief explanation>"
    """).strip()

    compat_response = _call_anthropic(api_key, compatibility_prompt, max_tokens=500).strip()
    is_backward_compatible = compat_response.startswith("BACKWARD-COMPATIBLE")
    explanation = compat_response.split(": ", 1)[1] if ": " in compat_response else compat_response

    return MigrationDiff(
        table_name=match.new_name or match.old_name or "unknown",
        old_table_name=match.old_name,
        new_table_name=match.new_name,
        match_type=match.match_type,
        sql=sql,
        is_backward_compatible=is_backward_compatible,
        explanation=explanation,
    )


def create_migrations(config: MigrateConfig, api_key: str, conn: psycopg.Connection) -> list[MigrationDiff]:
    """Generate migration diffs by comparing database schema with Python models."""
    db_schema = _get_schema_from_db(conn)

    db = PgDb(conn)
    schema = importlib.import_module(config.schema_path)
    new_schema = db.migrates(schema).ddls

    # Match tables between old and new schemas
    matches = _match_tables(db_schema, new_schema)

    # Generate diffs for each match
    diffs: list[MigrationDiff] = []
    for match in matches:
        print(f"Processing {match.match_type} table: {match.old_name or match.new_name}...")
        diff = _llm_diff_table(match, api_key)
        diffs.append(diff)

    return diffs


def _format_migration_output(diffs: list[MigrationDiff]) -> str:
    """Format migration diffs as SQL with metadata comments."""
    output: list[str] = []
    output.append("-- Generated Migration SQL")
    output.append("-- =======================")
    output.append("")

    for i, diff in enumerate(diffs, 1):
        output.append(f"-- Migration {i}/{len(diffs)}")
        output.append(f"-- Table: {diff.table_name}")
        output.append(f"-- Type: {diff.match_type.upper()}")

        if diff.old_table_name and diff.new_table_name and diff.old_table_name != diff.new_table_name:
            output.append(f"-- Rename: {diff.old_table_name} -> {diff.new_table_name}")

        compat_status = "BACKWARD-COMPATIBLE" if diff.is_backward_compatible else "⚠️  NON-BACKWARD-COMPATIBLE"
        output.append(f"-- Compatibility: {compat_status}")
        output.append(f"-- Explanation: {diff.explanation}")
        output.append("")
        output.append(diff.sql)
        output.append("")
        output.append("")

    return "\n".join(output)


def _red_bold(text: str) -> str:
    """Return text in red and bold for terminal."""
    return f"\033[1;31m{text}\033[0m"


def _green(text: str) -> str:
    """Return text in green for terminal."""
    return f"\033[32m{text}\033[0m"


def _yellow(text: str) -> str:
    """Return text in yellow for terminal."""
    return f"\033[33m{text}\033[0m"


def _confirm_migration(diff: MigrationDiff, index: int, total: int) -> bool:
    """Prompt user to confirm a migration. Returns True if user confirms, False otherwise."""
    print("\n" + "=" * 80)
    print(f"Migration {index}/{total}: {diff.table_name} ({diff.match_type.upper()})")
    print("=" * 80)

    if diff.old_table_name and diff.new_table_name and diff.old_table_name != diff.new_table_name:
        print(f"Rename: {diff.old_table_name} -> {diff.new_table_name}")

    if diff.is_backward_compatible:
        print(_green("✓ BACKWARD-COMPATIBLE"))
    else:
        print(_red_bold("⚠️  NON-BACKWARD-COMPATIBLE"))
        print(_red_bold(f"⚠️  {diff.explanation}"))

    print("\nSQL to execute:")
    print(_yellow(diff.sql))
    print()

    while True:
        response = input("Execute this migration? [y/n]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            print("Please enter 'y' or 'n'")


def _save_migration_to_file(diffs: list[MigrationDiff], migrations_dir: str, migration_name: str) -> str:
    """Save migrations to a file in the migrations directory."""
    # Create migrations directory if it doesn't exist
    os.makedirs(migrations_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{migration_name}.sql"
    filepath = os.path.join(migrations_dir, filename)

    # Write migration to file
    content = _format_migration_output(diffs)
    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def _execute_migrations(diffs: list[MigrationDiff], db: PgDb) -> None:
    """Execute migrations with user confirmation for each one."""
    print(f"\n{_yellow('EXECUTE MODE ENABLED')}")
    print("You will be prompted to confirm each migration.\n")

    for i, diff in enumerate(diffs, 1):
        if not _confirm_migration(diff, i, len(diffs)):
            print(_red_bold("\n✗ Migration cancelled by user. Exiting."))
            sys.exit(0)

        # Execute the migration
        print("Executing...")
        try:
            db.execute(Query(diff.sql))
            print(_green("✓ Migration executed successfully"))
        except Exception as e:
            print(_red_bold(f"✗ Error executing migration: {e}"))
            sys.exit(1)

    print(f"\n{_green('✓ All migrations executed successfully!')}")


def _load_env_file():
    """Load environment variables from .env file if it exists."""
    # Try current directory first, then parent directory
    for env_path in [".env", "../.env"]:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
            break


def _load_config(config_path: str | None = None) -> MigrateConfig:
    """Load and validate configuration from file."""
    if config_path is None:
        config_path = "embar.yml"

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found.")
        sys.exit(1)

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    try:
        return MigrateConfig(**config_data)
    except TypeError as e:
        print(f"Error: Invalid config format: {e}")
        sys.exit(1)


def _get_api_key() -> str:
    """Get API key from environment or prompt user."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY environment variable not set.")
        api_key = input("Please enter your Anthropic API key: ").strip()
        if not api_key:
            print("Error: API key is required.")
            sys.exit(1)
    return api_key


def _generate_diffs(config: MigrateConfig, api_key: str) -> list[MigrationDiff]:
    """Generate migration diffs from database and schema comparison."""
    print(f"Connecting to database: {config.db_url}")
    print(f"Loading schema from: {config.schema_path}")
    print("")

    conn = psycopg.connect(config.db_url)

    try:
        diffs = create_migrations(config, api_key, conn)
    except Exception as e:
        print(f"Error generating migrations: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    return diffs


def cmd_generate(config_path: str | None = None):
    """Generate migration and save to file."""
    config = _load_config(config_path)

    if not config.migrations_dir:
        print(_red_bold("Error: 'migrations_dir' must be set in config to use 'embar generate'"))
        sys.exit(1)

    api_key = _get_api_key()
    diffs = _generate_diffs(config, api_key)

    if not diffs:
        print("No migrations needed.")
        return

    migration_name = input("Enter migration name: ").strip()
    if not migration_name:
        print("Error: Migration name is required.")
        sys.exit(1)

    filepath = _save_migration_to_file(diffs, config.migrations_dir, migration_name)
    print(f"\n{_green(f'✓ Migration saved to: {filepath}')}")


def cmd_migrate(_config_path: str | None = None):
    """Apply migrations from migration files (not yet implemented)."""
    print(_red_bold("Error: 'embar migrate' is not yet implemented."))
    print("This command will apply migrations from the migrations directory.")
    sys.exit(1)


def cmd_push(config_path: str | None = None):
    """Generate and execute migrations with user confirmation."""
    config = _load_config(config_path)
    api_key = _get_api_key()
    diffs = _generate_diffs(config, api_key)

    if not diffs:
        print("No migrations needed.")
        return

    # Optionally save to file if migrations_dir is set
    if config.migrations_dir:
        migration_name = input("Enter migration name: ").strip()
        if not migration_name:
            print("Error: Migration name is required when using migrations_dir.")
            sys.exit(1)

        filepath = _save_migration_to_file(diffs, config.migrations_dir, migration_name)
        print(f"\n{_green(f'✓ Migration saved to: {filepath}')}")

    # Execute migrations with confirmation
    conn = psycopg.connect(config.db_url)
    db = PgDb(conn)
    _execute_migrations(diffs, db)


def cmd_pull(_config_path: str | None = None):
    """Pull schema from database and generate models (not yet implemented)."""
    print(_red_bold("Error: 'embar pull' is not yet implemented."))
    print("This command will generate Python models from the database schema.")
    sys.exit(1)


def main():
    """Main entry point for the migration tool."""
    # Load .env file
    _load_env_file()

    # Add current directory to Python path for schema imports
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: embar <command> [config_path]")
        print("")
        print("Commands:")
        print("  generate    Generate migration and save to file (requires migrations_dir in config)")
        print("  migrate     Apply migrations from migration files (not yet implemented)")
        print("  push        Generate and execute migrations with confirmation")
        print("  pull        Pull schema from database (not yet implemented)")
        print("")
        print("Arguments:")
        print("  config_path    Optional path to config file (default: embar.yml)")
        sys.exit(1)

    command = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "generate":
        cmd_generate(config_path)
    elif command == "migrate":
        cmd_migrate(config_path)
    elif command == "push":
        cmd_push(config_path)
    elif command == "pull":
        cmd_pull(config_path)
    else:
        print(f"Error: Unknown command '{command}'")
        print("Valid commands: generate, migrate, push, pull")
        sys.exit(1)


if __name__ == "__main__":
    main()
