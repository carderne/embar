import pytest

from embar.db.pg import AsyncDb as AsyncPgDb
from embar.db.pg import Db as PgDb
from embar.db.sqlite import Db as SqliteDb
from embar.query.select import SelectQuery

from ..schemas.schema import User


@pytest.mark.asyncio
async def test_await_on_async_pg(async_pg_db: AsyncPgDb):
    db = async_pg_db

    await db.migrate([User])

    user = User(id=1, email="john@foo.com")
    await db.insert(User).values(user)

    res = await db.select(User.all()).fromm(User)

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


def test_no_await_on_async_pg(async_pg_db: AsyncPgDb):
    db = async_pg_db

    with pytest.warns(RuntimeWarning, match="coroutine 'AsyncDb.migrate' was never awaited"):
        db.migrate([User])  # pyright:ignore[reportUnusedCoroutine]

    user = User(id=1, email="john@foo.com")
    db.insert(User).values(user)

    res = db.select(User.all()).fromm(User)

    # nothing has been executed
    assert isinstance(res, SelectQuery)


@pytest.mark.asyncio
async def test_await_on_sync_pg(pg_db: PgDb):
    db = pg_db

    db.migrate([User])

    user = User(id=1, email="john@foo.com")
    await db.insert(User).values(user)

    res = await db.select(User.all()).fromm(User)

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


def test_no_await_on_sync_pg(pg_db: PgDb):
    db = pg_db

    db.migrate([User])

    user = User(id=1, email="john@foo.com")
    db.insert(User).values(user).run()

    # note the added .run()
    res = db.select(User.all()).fromm(User).run()

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


@pytest.mark.asyncio
async def test_await_on_sqlite(sqlite_db: SqliteDb):
    db = sqlite_db

    db.migrate([User])

    user = User(id=1, email="john@foo.com")
    await db.insert(User).values(user)

    res = await db.select(User.all()).fromm(User)

    assert len(res) == 1
    got = res[0]
    assert got.id == 1


def test_no_await_on_sqlite(sqlite_db: SqliteDb):
    db = sqlite_db

    db.migrate([User])

    user = User(id=1, email="john@foo.com")
    db.insert(User).values(user).run()

    # note the added .run()
    res = db.select(User.all()).fromm(User).run()

    assert len(res) == 1
    got = res[0]
    assert got.id == 1
