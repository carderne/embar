import sqlite3
from typing import Any
import psycopg
import pytest


from pudl.db.sqlite import Db as SqliteDb
from pudl.db.pg import Db as PgDb

from .container import PostgresContainer
from . import schema
from .schema import User, Message

postgres = PostgresContainer("postgres:18-alpine3.22", port=25432)


@pytest.fixture(scope="module")
def postgres_container(request: Any):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)
    return postgres


@pytest.fixture(scope="function", autouse=True)
def truncate_tables():
    # TODO add between-test teardown
    ...


@pytest.fixture(params=["sqlite", "postgres"])
def db(request: pytest.FixtureRequest, sqlite_db: SqliteDb, pg_db: PgDb) -> SqliteDb | PgDb:
    """Parametrized fixture that runs tests against both SQLite and Postgres."""
    if request.param == "sqlite":
        return sqlite_db
    else:
        return pg_db


@pytest.fixture
def sqlite_db() -> SqliteDb:
    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    db.migrates(schema)

    user = User(id=1, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")
    db.insert(User).value(user).execute()
    db.insert(Message).value(message).execute()
    return db


@pytest.fixture(scope="module")
def pg_db(postgres_container: PostgresContainer) -> PgDb:
    url = postgres_container.get_connection_url()
    conn = psycopg.connect(url)
    db = PgDb(conn)
    db.migrates(schema)

    user = User(id=1, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")
    db.insert(User).value(user).execute()
    db.insert(Message).value(message).execute()
    return db
