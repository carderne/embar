import pytest

from tests.e2e.container import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container(request: pytest.FixtureRequest):
    """Session-scoped postgres container for docs tests."""
    try:
        with PostgresContainer("postgres:18-alpine3.22", port=25432) as postgres:
            request.addfinalizer(postgres.stop)
            yield postgres
    except Exception as e:
        pytest.exit(f"postgres_container fixture failed: {e}", 1)
