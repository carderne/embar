"""Migration tool for generating and applying database migrations using LLMs."""

import importlib
import os
import sys
from datetime import datetime
from difflib import SequenceMatcher
from textwrap import dedent

import psycopg

from embar.db.pg import PgDb
from embar.migration import Ddl
from embar.query.query import QuerySingle
from embar.tools.fmt import format_migration_output, green, red_bold, yellow
from embar.tools.llm import Llm
from embar.tools.models import MigrateConfig, MigrationDiff, TableMatch


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


def get_schema_from_db(conn: psycopg.Connection) -> list[Ddl]:
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


def _llm_diff_table(match: TableMatch, api_key: str, llm: Llm) -> MigrationDiff:
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
    sql = llm(api_key, prompt, max_tokens=2000).strip()

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

    compat_response = llm(api_key, compatibility_prompt, max_tokens=500).strip()
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


def _create_migrations(config: MigrateConfig, api_key: str, conn: psycopg.Connection, llm: Llm) -> list[MigrationDiff]:
    """Generate migration diffs by comparing database schema with Python models."""
    db_schema = get_schema_from_db(conn)

    db = PgDb(conn)
    schema = importlib.import_module(config.schema_path)
    new_schema = db.migrates(schema).ddls

    # Match tables between old and new schemas
    matches = _match_tables(db_schema, new_schema)

    # Generate diffs for each match
    diffs: list[MigrationDiff] = []
    for match in matches:
        print(f"Processing {match.match_type} table: {match.old_name or match.new_name}...")
        diff = _llm_diff_table(match, api_key, llm)
        diffs.append(diff)

    return diffs


def _confirm_migration(diff: MigrationDiff, index: int, total: int) -> bool:
    """Prompt user to confirm a migration. Returns True if user confirms, False otherwise."""
    print("\n" + "=" * 80)
    print(f"Migration {index}/{total}: {diff.table_name} ({diff.match_type.upper()})")
    print("=" * 80)

    if diff.old_table_name and diff.new_table_name and diff.old_table_name != diff.new_table_name:
        print(f"Rename: {diff.old_table_name} -> {diff.new_table_name}")

    if diff.is_backward_compatible:
        print(green("✓ BACKWARD-COMPATIBLE"))
    else:
        print(red_bold("⚠️  NON-BACKWARD-COMPATIBLE"))
        print(red_bold(f"⚠️  {diff.explanation}"))

    print("\nSQL to execute:")
    print(yellow(diff.sql))
    print()

    while True:
        response = input("Execute this migration? [y/n]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            print("Please enter 'y' or 'n'")


def save_migration_to_file(diffs: list[MigrationDiff], migrations_dir: str, migration_name: str) -> str:
    """Save migrations to a file in the migrations directory."""
    # Create migrations directory if it doesn't exist
    os.makedirs(migrations_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{migration_name}.sql"
    filepath = os.path.join(migrations_dir, filename)

    # Write migration to file
    content = format_migration_output(diffs)
    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def execute_migrations(diffs: list[MigrationDiff], db: PgDb) -> None:
    """Execute migrations with user confirmation for each one."""
    print(f"\n{yellow('EXECUTE MODE ENABLED')}")
    print("You will be prompted to confirm each migration.\n")

    for i, diff in enumerate(diffs, 1):
        if not _confirm_migration(diff, i, len(diffs)):
            print(red_bold("\n✗ Migration cancelled by user. Exiting."))
            sys.exit(0)

        # Execute the migration
        print("Executing...")
        try:
            db.execute(QuerySingle(diff.sql))
            print(green("✓ Migration executed successfully"))
        except Exception as e:
            print(red_bold(f"✗ Error executing migration: {e}"))
            sys.exit(1)

    print(f"\n{green('✓ All migrations executed successfully!')}")


def generate_diffs(config: MigrateConfig, api_key: str, llm: Llm) -> list[MigrationDiff]:
    """Generate migration diffs from database and schema comparison."""
    print(f"Connecting to database: {config.db_url}")
    print(f"Loading schema from: {config.schema_path}")
    print("")

    conn = psycopg.connect(config.db_url)

    try:
        diffs = _create_migrations(config, api_key, conn, llm)
    except Exception as e:
        print(f"Error generating migrations: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    return diffs


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    """Create _embar_migrations table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _embar_migrations (
                migration_name TEXT PRIMARY KEY,
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMP
            )
        """)
    conn.commit()


def check_migration_state(conn: psycopg.Connection) -> None:
    """Check if any migrations are in an invalid state (started but not finished)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT migration_name, started_at
            FROM _embar_migrations
            WHERE started_at IS NOT NULL AND finished_at IS NULL
            ORDER BY started_at
        """)
        incomplete = cur.fetchall()

    if incomplete:
        print(red_bold("Error: Database is in an invalid state!"))
        print("The following migrations were started but not completed:")
        for name, started_at in incomplete:
            print(f"  - {name} (started at {started_at})")
        print("\nPlease resolve this manually before running new migrations.")
        sys.exit(1)


def get_applied_migrations(conn: psycopg.Connection) -> set[str]:
    """Get set of migration names that have been successfully applied."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT migration_name
            FROM _embar_migrations
            WHERE finished_at IS NOT NULL
            ORDER BY finished_at
        """)
        return {row[0] for row in cur.fetchall()}


def get_migration_files(migrations_dir: str) -> list[tuple[str, str]]:
    """Get list of migration files sorted by timestamp. Returns (filename, filepath) tuples."""
    if not os.path.exists(migrations_dir):
        return []

    files: list[tuple[str, str]] = []
    for filename in sorted(os.listdir(migrations_dir)):
        if filename.endswith(".sql"):
            filepath = os.path.join(migrations_dir, filename)
            # Extract migration name (remove .sql extension)
            migration_name = filename[:-4]
            files.append((migration_name, filepath))

    return files


def apply_migration_file(conn: psycopg.Connection, db: PgDb, migration_name: str, filepath: str) -> None:
    """Apply a single migration file."""
    # Read the SQL file
    with open(filepath, "r") as f:
        sql_content = f.read()

    # Extract SQL statements (skip comment lines starting with --)
    current_statement: list[str] = []
    for line in sql_content.split("\n"):
        stripped = line.strip()
        # Skip comment lines and empty lines
        if stripped.startswith("--") or not stripped:
            continue
        current_statement.append(line)

    # Join all non-comment lines
    full_sql = "\n".join(current_statement).strip()

    if not full_sql:
        print(f"  {yellow('⊘ No SQL to execute (comments only)')}")
        return

    # Record migration start
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO _embar_migrations (migration_name, started_at)
            VALUES (%s, NOW())
        """,
            (migration_name,),
        )
    conn.commit()

    try:
        # Execute the SQL
        db.execute(QuerySingle(full_sql))

        # Record migration completion
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE _embar_migrations
                SET finished_at = NOW()
                WHERE migration_name = %s
            """,
                (migration_name,),
            )
        conn.commit()

        print(f"  {green('✓ Applied successfully')}")

    except Exception as e:
        print(f"  {red_bold(f'✗ Error: {e}')}")
        conn.rollback()
        raise
