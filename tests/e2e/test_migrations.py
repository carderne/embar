"""E2E tests for migration commands."""

import os
import tempfile
from typing import TYPE_CHECKING
from unittest.mock import patch

import psycopg
import pytest

from embar.tools.commands import (
    _cmd_generate as cmd_generate,  # pyright: ignore[reportPrivateUsage]
)
from embar.tools.commands import (
    _cmd_migrate as cmd_migrate,  # pyright: ignore[reportPrivateUsage]
)
from embar.tools.commands import (
    _cmd_pull as cmd_pull,  # pyright: ignore[reportPrivateUsage]
)
from embar.tools.commands import (
    _cmd_push as cmd_push,  # pyright: ignore[reportPrivateUsage]
)

from .container import PostgresContainer

if TYPE_CHECKING:
    from pytest import CaptureFixture


@pytest.fixture(scope="module")
def migrations_postgres_container(request: pytest.FixtureRequest):
    """Separate postgres container for migration tests to avoid conflicts."""
    try:
        with PostgresContainer("postgres:18-alpine3.22", port=25433) as postgres:
            request.addfinalizer(postgres.stop)
            yield postgres
    except Exception as e:
        pytest.exit(f"migrations_postgres_container fixture failed: {e}", 1)


@pytest.fixture
def clean_db(migrations_postgres_container: PostgresContainer):
    """Clean database before each test."""
    url = migrations_postgres_container.get_connection_url()
    conn = psycopg.connect(url)
    with conn.cursor() as cur:
        # Drop all tables in public schema
        cur.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
    conn.commit()
    conn.close()
    return migrations_postgres_container


@pytest.fixture
def temp_migrations_dir():
    """Create a temporary directory for migration files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_config_path(clean_db: PostgresContainer, temp_migrations_dir: str):
    """Create a test config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        print('dialect = "postgresql"', file=f)
        print(f'db_url = "{clean_db.get_connection_url()}"', file=f)
        print('schema_path = "tests.e2e.migrations_schema"', file=f)
        print(f'migrations_dir = "{temp_migrations_dir}"', file=f)
        config_path = f.name
    yield config_path
    os.unlink(config_path)


def mock_llm(
    api_key: str,  # pyright: ignore[reportUnusedParameter]
    prompt: str,
    max_tokens: int = 2000,  # pyright: ignore[reportUnusedParameter]
) -> str:
    """Mock LLM that returns static SQL based on prompt content."""
    prompt_lower = prompt.lower()

    # Check if this is a backward compatibility check
    if "backward-compatible" in prompt_lower or "backward compatibility" in prompt_lower:
        return "BACKWARD-COMPATIBLE: This migration only adds new tables/columns"

    # Check if this is asking to create a new table
    if "create this new table" in prompt_lower or "new table ddl" in prompt_lower:
        return """CREATE TABLE testuser (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);"""

    # Check if this is asking to drop a table
    if "drop this table" in prompt_lower:
        return "DROP TABLE testuser;"

    # Default: no changes needed
    return "-- No changes needed"


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
def test_cmd_generate(test_config_path: str, temp_migrations_dir: str):
    """Test cmd_generate creates a migration file."""
    with patch("builtins.input", return_value="initial_schema"):
        cmd_generate(config_path=test_config_path, llm=mock_llm)

    # Check that a migration file was created
    files = os.listdir(temp_migrations_dir)
    assert len(files) == 1
    assert files[0].endswith("_initial_schema.sql")

    # Verify file contains expected SQL
    with open(os.path.join(temp_migrations_dir, files[0])) as f:
        content = f.read()
    assert "CREATE TABLE" in content or "testuser" in content.lower()


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
def test_cmd_migrate(test_config_path: str, temp_migrations_dir: str, clean_db: PostgresContainer):
    """Test cmd_migrate applies migration files to database."""
    # Create a migration file manually
    migration_content = """-- Migration: create testuser table
CREATE TABLE testuser (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
"""
    migration_file = os.path.join(temp_migrations_dir, "20240101_000000_create_testuser.sql")
    with open(migration_file, "w") as f:
        f.write(migration_content)

    # Run migrate
    cmd_migrate(config_path=test_config_path)

    # Verify table was created
    conn = psycopg.connect(clean_db.get_connection_url())
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'testuser')")
        row = cur.fetchone()
        exists = row[0] if row else False
    conn.close()
    assert exists, "testuser table should exist after migration"

    # Verify migration was tracked
    conn = psycopg.connect(clean_db.get_connection_url())
    with conn.cursor() as cur:
        cur.execute("SELECT migration_name FROM _embar_migrations WHERE finished_at IS NOT NULL")
        applied = [row[0] for row in cur.fetchall()]
    conn.close()
    assert "20240101_000000_create_testuser" in applied


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
def test_cmd_push(test_config_path: str, clean_db: PostgresContainer):
    """Test cmd_push generates and executes migrations."""
    # Mock input to confirm migration execution
    with patch("builtins.input", return_value="y"):
        cmd_push(config_path=test_config_path, llm=mock_llm)

    # Verify table was created
    conn = psycopg.connect(clean_db.get_connection_url())
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'testuser')")
        row = cur.fetchone()
        exists = row[0] if row else False
    conn.close()
    assert exists, "testuser table should exist after push"


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
def test_cmd_pull(test_config_path: str, clean_db: PostgresContainer, capsys: "CaptureFixture[str]"):
    """Test cmd_pull extracts schema from database."""
    # First create a table in the database
    conn = psycopg.connect(clean_db.get_connection_url())
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE pulled_table (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL
            )
        """)
    conn.commit()
    conn.close()

    # Run pull
    cmd_pull(config_path=test_config_path)

    # Check captured output
    captured = capsys.readouterr()
    assert "pulled_table" in captured.out
    assert "CREATE TABLE" in captured.out
