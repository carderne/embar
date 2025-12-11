import pytest

from embar.db.pg import AsyncPgDb, PgDb
from embar.db.sqlite import SqliteDb
from embar.query.select import SelectQueryReady

from ..schemas.schema import User


@pytest.mark.asyncio
async def test_await_on_async_pg(async_pg_db: AsyncPgDb):
    db = async_pg_db

    await db.migrate([User]).run()

    user = User(id=1, email="john@foo.com")
    await db.insert(User).values(user)

    res = await db.select(User.all()).from_(User)

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


def test_no_await_on_async_pg(async_pg_db: AsyncPgDb):
    db = async_pg_db

    _migrations_not_run = db.migrate([User])

    user = User(id=1, email="john@foo.com")
    db.insert(User).values(user)

    res = db.select(User.all()).from_(User)

    # nothing has been executed
    assert isinstance(res, SelectQueryReady)


@pytest.mark.asyncio
async def test_await_on_sync_pg(pg_db: PgDb):
    db = pg_db

    await db.migrate([User])

    user = User(id=1, email="john@foo.com")
    await db.insert(User).values(user)

    res = await db.select(User.all()).from_(User)

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


def test_no_await_on_sync_pg(pg_db: PgDb):
    db = pg_db

    db.migrate([User]).run()

    user = User(id=1, email="john@foo.com")
    db.insert(User).values(user).run()

    # note the added .run()
    res = db.select(User.all()).from_(User).run()

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


@pytest.mark.asyncio
async def test_await_on_sqlite(sqlite_db: SqliteDb):
    db = sqlite_db

    await db.migrate([User])

    user = User(id=1, email="john@foo.com")
    await db.insert(User).values(user)

    res = await db.select(User.all()).from_(User)

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


def test_no_await_on_sqlite(sqlite_db: SqliteDb):
    db = sqlite_db

    db.migrate([User]).run()

    user = User(id=1, email="john@foo.com")
    db.insert(User).values(user).run()

    # note the added .run()
    res = db.select(User.all()).from_(User).run()

    assert len(res) == 1
    got = res[0]
    assert got.id == 1
