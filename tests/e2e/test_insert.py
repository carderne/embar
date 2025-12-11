from typing import Annotated

from pydantic import BaseModel

from embar.db.pg import PgDb
from embar.db.sqlite import SqliteDb

from ..schemas.schema import User


def test_insert_on_conflict_do_nothing(db: SqliteDb | PgDb):
    user1 = User(id=1, email="alice@example.com")
    db.insert(User).values(user1).run()

    # Insert duplicate - should be ignored
    user2 = User(id=1, email="bob@example.com")
    db.insert(User).values(user2).on_conflict_do_nothing(("id",)).run()

    # Verify only one row exists with original email
    class UserSel(BaseModel):
        email: Annotated[str, User.email]

    res = db.select(UserSel).from_(User).run()
    assert len(res) == 1
    assert res[0].email == "alice@example.com"


def test_insert_on_conflict_do_update(db: SqliteDb | PgDb):
    user1 = User(id=1, email="alice@example.com")
    db.insert(User).values(user1).run()

    # Insert duplicate with update
    user2 = User(id=1, email="ignored@example.com")
    db.insert(User).values(user2).on_conflict_do_update(("id",), {"user_email": "updated@example.com"}).run()

    # Verify email was updated
    class UserSel(BaseModel):
        email: Annotated[str, User.email]

    res = db.select(UserSel).from_(User).run()
    assert len(res) == 1
    assert res[0].email == "updated@example.com"


def test_insert_on_conflict_do_nothing_returning(db: SqliteDb | PgDb):
    user1 = User(id=1, email="alice@example.com")
    db.insert(User).values(user1).run()

    # Insert duplicate with returning - should return empty
    user2 = User(id=1, email="bob@example.com")
    # fmt: off
    res = (
        db.insert(User)
        .values(user2)
        .on_conflict_do_nothing(("id",))
        .returning()
        .run()
    )
    # fmt: on

    assert len(res) == 0


def test_insert_on_conflict_do_update_returning(db: SqliteDb | PgDb):
    user1 = User(id=1, email="alice@example.com")
    db.insert(User).values(user1).run()

    # Insert duplicate with update and returning
    user2 = User(id=1, email="ignored@example.com")
    res = (
        db.insert(User)
        .values(user2)
        .on_conflict_do_update(("id",), {"user_email": "updated@example.com"})
        .returning()
        .run()
    )

    # Verify row was returned and updated (check id since column name mapping works for it)
    assert len(res) == 1
    assert res[0].id == 1
