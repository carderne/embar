from typing import Annotated

import pytest
from pydantic import BaseModel

from embar.db.pg import AsyncPgDb, PgDb
from embar.db.sqlite import SqliteDb

from ..schemas.schema import Message, User


class UserEmail(BaseModel):
    email: Annotated[str, User.email]


def test_transaction_commit(db: SqliteDb | PgDb):
    """Test that changes inside a transaction are committed on success."""
    with db.transaction() as tx:
        user = User(id=1, email="alice@example.com")
        tx.insert(User).values(user).run()

    # Verify data persisted after transaction
    res = db.select(UserEmail).from_(User).run()
    assert len(res) == 1
    assert res[0].email == "alice@example.com"


def test_transaction_rollback_on_db_error(db: SqliteDb | PgDb):
    """Test that a database error causes rollback."""
    # Insert initial user
    user1 = User(id=1, email="alice@example.com")
    db.insert(User).values(user1).run()

    # Try to insert duplicate in transaction - should fail and rollback
    with pytest.raises(Exception):
        with db.transaction() as tx:
            # This insert should succeed
            user2 = User(id=2, email="bob@example.com")
            tx.insert(User).values(user2).run()

            # This insert should fail (duplicate id)
            user3 = User(id=1, email="charlie@example.com")
            tx.insert(User).values(user3).run()

    # Verify only original user exists (user2 was rolled back)
    res = db.select(UserEmail).from_(User).run()
    assert len(res) == 1
    assert res[0].email == "alice@example.com"


def test_transaction_rollback_on_exception(db: SqliteDb | PgDb):
    """Test that an unrelated exception causes rollback."""
    with pytest.raises(ValueError):
        with db.transaction() as tx:
            user = User(id=1, email="alice@example.com")
            tx.insert(User).values(user).run()

            # Raise unrelated exception
            raise ValueError("Something went wrong")

    # Verify no data was committed
    res = db.select(UserEmail).from_(User).run()
    assert len(res) == 0


@pytest.mark.asyncio
async def test_async_transaction_commit(async_pg_db: AsyncPgDb):
    """Test that changes inside an async transaction are committed on success."""
    db = async_pg_db
    await db.migrate([User, Message]).run()

    async with db.transaction() as tx:
        user = User(id=1, email="alice@example.com")
        await tx.insert(User).values(user)

    # Verify data persisted after transaction
    res = await db.select(UserEmail).from_(User)
    assert len(res) == 1
    assert res[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_async_transaction_rollback_on_db_error(async_pg_db: AsyncPgDb):
    """Test that a database error causes rollback in async transaction."""
    db = async_pg_db
    await db.migrate([User, Message]).run()

    # Insert initial user
    user1 = User(id=1, email="alice@example.com")
    await db.insert(User).values(user1)

    # Try to insert duplicate in transaction - should fail and rollback
    with pytest.raises(Exception):
        async with db.transaction() as tx:
            # This insert should succeed
            user2 = User(id=2, email="bob@example.com")
            await tx.insert(User).values(user2)

            # This insert should fail (duplicate id)
            user3 = User(id=1, email="charlie@example.com")
            await tx.insert(User).values(user3)

    # Verify only original user exists (user2 was rolled back)
    res = await db.select(UserEmail).from_(User)
    assert len(res) == 1
    assert res[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_async_transaction_rollback_on_exception(async_pg_db: AsyncPgDb):
    """Test that an unrelated exception causes rollback in async transaction."""
    db = async_pg_db
    await db.migrate([User, Message]).run()

    with pytest.raises(ValueError):
        async with db.transaction() as tx:
            user = User(id=1, email="alice@example.com")
            await tx.insert(User).values(user)

            # Raise unrelated exception
            raise ValueError("Something went wrong")

    # Verify no data was committed
    res = await db.select(UserEmail).from_(User)
    assert len(res) == 0
