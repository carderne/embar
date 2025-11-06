import pytest

from embar.db.pg import PgDb


@pytest.fixture(scope="module")
def db_dummy() -> PgDb:
    """A dummy db that can't actually be used to query, just construct queries."""
    db = PgDb(None)  # pyright:ignore[reportArgumentType]
    return db
