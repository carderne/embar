import sqlite3
import psycopg
import pytest


from pudl.db.sqlite import Db as SqliteDb
from pudl.db.pg import Db as PgDb
from pudl.sql import sql

from .container import PostgresContainer
from . import schema
from .schema import User, Message

postgres = PostgresContainer("postgres:18-alpine3.22", port=25432)


@pytest.fixture(scope="module")
def postgres_container(request: pytest.FixtureRequest):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)
    return postgres


@pytest.fixture(scope="function")
def db_clean(db: SqliteDb | PgDb):
    query1 = sql(t"DELETE FROM {Message}").execute()
    db.execute(query1, {})
    query2 = sql(t"DELETE FROM {User}").execute()
    db.execute(query2, {})
    return db


@pytest.fixture
def db_loaded(db_clean: SqliteDb | PgDb):
    db = db_clean
    user = User(id=1, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")
    db.insert(User).value(user).execute()
    db.insert(Message).value(message).execute()
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

    db.migrates(schema)
    return db


@pytest.fixture
def sqlite_db() -> SqliteDb:
    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    return db


@pytest.fixture(scope="module")
def pg_db(postgres_container: PostgresContainer) -> PgDb:
    url = postgres_container.get_connection_url()
    conn = psycopg.connect(url)
    db = PgDb(conn)
    return db
