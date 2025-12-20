import importlib
import os
import sys

import psycopg

from embar.db.pg import PgDb
from embar.tools.fmt import green, red_bold
from embar.tools.llm import Llm, call_anthropic
from embar.tools.migrate import (
    apply_migration_file,
    check_migration_state,
    ensure_migrations_table,
    execute_migrations,
    generate_diffs,
    get_applied_migrations,
    get_migration_files,
    get_schema_from_db,
    save_migration_to_file,
)
from embar.tools.utils import get_api_key, load_config, load_env_file


def _cmd_schema(config_path: str | None = None):
    """Generate migration and save to file."""
    config = load_config(config_path)

    db = PgDb(None)  # pyright:ignore[reportArgumentType]
    schema = importlib.import_module(config.schema_path)
    new_schema = db.migrates(schema).ddls

    output = "\n\n".join(ddl.ddl for ddl in new_schema)
    print(output)


def _cmd_generate(config_path: str | None = None, llm: Llm = call_anthropic):
    """Generate migration and save to file."""
    config = load_config(config_path)

    if not config.migrations_dir:
        print(red_bold("Error: 'migrations_dir' must be set in config to use 'embar generate'"))
        sys.exit(1)

    api_key = get_api_key()
    diffs = generate_diffs(config, api_key, llm)

    if not diffs:
        print("No migrations needed.")
        return

    migration_name = input("Enter migration name: ").strip()
    if not migration_name:
        print("Error: Migration name is required.")
        sys.exit(1)

    filepath = save_migration_to_file(diffs, config.migrations_dir, migration_name)
    print(f"\n{green(f'✓ Migration saved to: {filepath}')}")


def _cmd_migrate(config_path: str | None = None):
    """Apply migrations from migration files."""
    config = load_config(config_path)

    if not config.migrations_dir:
        print(red_bold("Error: 'migrations_dir' must be set in config to use 'embar migrate'"))
        sys.exit(1)

    if not os.path.exists(config.migrations_dir):
        print(red_bold(f"Error: Migrations directory '{config.migrations_dir}' not found"))
        sys.exit(1)

    print(f"Connecting to database: {config.db_url}")
    conn = psycopg.connect(config.db_url)
    db = PgDb(conn)

    # Ensure migrations table exists
    ensure_migrations_table(conn)

    # Check for incomplete migrations
    check_migration_state(conn)

    # Get applied and pending migrations
    applied = get_applied_migrations(conn)
    all_migrations = get_migration_files(config.migrations_dir)

    pending = [(name, path) for name, path in all_migrations if name not in applied]

    if not pending:
        print(green("✓ No pending migrations to apply"))
        return

    print(f"\nFound {len(pending)} pending migration(s):")
    for name, _ in pending:
        print(f"  - {name}")
    print()

    # Apply each pending migration
    for i, (migration_name, filepath) in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] Applying {migration_name}...")

        try:
            apply_migration_file(conn, db, migration_name, filepath)
        except Exception:
            print(red_bold(f"\n✗ Migration failed: {migration_name}"))
            print("Database state has been rolled back for this migration.")
            sys.exit(1)

    print(f"\n{green('✓ All migrations applied successfully!')}")


def _cmd_push(config_path: str | None = None, llm: Llm = call_anthropic):
    """Generate and execute migrations with user confirmation."""
    config = load_config(config_path)
    api_key = get_api_key()
    diffs = generate_diffs(config, api_key, llm)

    if not diffs:
        print("No migrations needed.")
        return

    # Execute migrations with confirmation
    conn = psycopg.connect(config.db_url)
    db = PgDb(conn)
    execute_migrations(diffs, db)


def _cmd_pull(config_path: str | None = None):
    """Pull schema from database and print DDL."""
    config = load_config(config_path)

    print(f"Connecting to database: {config.db_url}")
    print("Extracting schema...\n")

    conn = psycopg.connect(config.db_url)
    schema = get_schema_from_db(conn)

    if not schema:
        print("No tables or enums found in database.")
        return

    print("-- Database Schema")
    print("-- " + "=" * 78)
    print()

    for ddl in schema:
        print(f"-- {ddl.name}")
        print(ddl.ddl)
        if ddl.constraints:
            print()
            for constraint in ddl.constraints:
                print(constraint)
        print()
        print()


def main():
    """Main entry point for the migration tool."""
    # Load .env file
    load_env_file()

    # Add current directory to Python path for schema imports
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: embar <command> [config_path]")
        print("")
        print("Commands:")
        print("  schema      Print the current table schema to stdout")
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

    if command == "schema":
        _cmd_schema(config_path)
    elif command == "generate":
        _cmd_generate(config_path)
    elif command == "migrate":
        _cmd_migrate(config_path)
    elif command == "push":
        _cmd_push(config_path)
    elif command == "pull":
        _cmd_pull(config_path)
    else:
        print(f"Error: Unknown command '{command}'")
        print("Valid commands: generate, migrate, push, pull")
        sys.exit(1)


if __name__ == "__main__":
    main()
