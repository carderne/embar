import sqlite3

import psycopg
import pytest
import pytest_asyncio

from embar.db.pg import AsyncPgDb, PgDb
from embar.db.sqlite import SqliteDb

from ..schemas import schema
from ..schemas.schema import Message, User
from .container import PostgresContainer


@pytest.fixture(scope="module")
def postgres_container(request: pytest.FixtureRequest):
    try:
        with PostgresContainer("postgres:18-alpine3.22", port=25432) as postgres:
            # Add finalizer as backup safety net
            request.addfinalizer(postgres.stop)
            yield postgres
    except Exception as e:
        pytest.exit(f"postgres_container fixture failed: {e}", 1)


@pytest.fixture
def db_loaded(db: SqliteDb | PgDb):
    user = User(id=1, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")
    db.insert(User).values(user).run()
    db.insert(Message).values(message).run()
    return db


@pytest.fixture(params=["sqlite", "postgres"])
def db(request: pytest.FixtureRequest, sqlite_db: SqliteDb, pg_db: PgDb) -> SqliteDb | PgDb:
    """Parametrized fixture that runs tests against both SQLite and Postgres."""
    match request.param:
        case "sqlite":
            db = sqlite_db
        case "postgres":
            db = pg_db
        case _:
            raise Exception(f"Unsupported db {request.param}")

    db.migrates(schema).run()
    return db


@pytest.fixture(scope="module")
def sqlite_db_raw() -> SqliteDb:
    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    return db


@pytest.fixture(scope="function")
def sqlite_db(sqlite_db_raw: SqliteDb) -> SqliteDb:
    sqlite_db_raw.truncate()
    return sqlite_db_raw


@pytest.fixture(scope="module")
def pg_db_raw(postgres_container: PostgresContainer) -> PgDb:
    url = postgres_container.get_connection_url()
    conn = psycopg.connect(url)
    db = PgDb(conn)
    return db


@pytest.fixture(scope="function")
def pg_db(pg_db_raw: PgDb) -> PgDb:
    pg_db_raw.truncate()
    return pg_db_raw


@pytest_asyncio.fixture(scope="module")
async def async_pg_db_raw(postgres_container: PostgresContainer) -> AsyncPgDb:
    url = postgres_container.get_connection_url()
    conn = await psycopg.AsyncConnection.connect(url)
    db = AsyncPgDb(conn)
    return db


@pytest_asyncio.fixture(scope="function")
async def async_pg_db(async_pg_db_raw: AsyncPgDb) -> AsyncPgDb:
    await async_pg_db_raw.truncate()
    return async_pg_db_raw
