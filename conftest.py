import psycopg
import pytest

from embar.db.pg import PgDb
from tests.e2e.container import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container_raw(request: pytest.FixtureRequest):
    """Session-scoped postgres container for docs tests."""
    try:
        with PostgresContainer("pgvector/pgvector:0.8.1-pg18-trixie", port=25432) as postgres:
            request.addfinalizer(postgres.stop)
            yield postgres
    except Exception as e:
        pytest.exit(f"postgres_container fixture failed: {e}", 1)


@pytest.fixture(scope="function")
def postgres_container(postgres_container_raw: PostgresContainer):
    url = postgres_container_raw.get_connection_url()
    conn = psycopg.connect(url)
    db = PgDb(conn)
    db.drop_tables()
    return postgres_container_raw
