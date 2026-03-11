"""
Tests for RETURNING with custom DB column names.

The bug: RETURNING * gives back DB column names (e.g. "user_email") but
generate_model() builds a model keyed by Python field names (e.g. "email"),
so load_results() can't match them up and the custom-name fields come back
as None.
"""

import pytest

from embar.db.sqlite import SqliteDb

from ..schemas import schema
from ..schemas.schema import Message, User


@pytest.fixture
def fresh_db(sqlite_db: SqliteDb) -> SqliteDb:
    """SQLite DB with the schema applied."""
    sqlite_db.migrates(schema).run()
    return sqlite_db


# ---------------------------------------------------------------------------
# Baseline: no custom column name – should always pass
# ---------------------------------------------------------------------------


def test_insert_returning_no_custom_column(fresh_db: SqliteDb):
    """RETURNING works when field name == DB column name (no rename)."""
    user = User(id=1, email="a@b.com")
    fresh_db.insert(User).values(user).run()

    msg = Message(id=42, user_id=1, content="hello")
    results = fresh_db.insert(Message).values(msg).returning().run()

    assert len(results) == 1
    assert results[0].id == 42
    assert results[0].content == "hello"


# ---------------------------------------------------------------------------
# The buggy case: field name != DB column name
# User.email maps to DB column "user_email"
# ---------------------------------------------------------------------------


def test_insert_returning_custom_column_name_pydantic(fresh_db: SqliteDb):
    """
    RETURNING correctly maps DB column 'user_email' back to Python field 'email'
    (pydantic path).
    """
    user = User(id=1, email="alice@example.com")
    results = fresh_db.insert(User).values(user).returning(use_pydantic=True).run()

    assert len(results) == 1
    assert results[0].id == 1
    # Before the fix: results[0].email is None because the DB returns the
    # column as "user_email" but the model field is "email".
    assert results[0].email == "alice@example.com"


def test_insert_returning_custom_column_name_plain(fresh_db: SqliteDb):
    """
    RETURNING correctly maps DB column 'user_email' back to Python field 'email'
    (plain dataclass path).
    """
    user = User(id=1, email="alice@example.com")
    results = fresh_db.insert(User).values(user).returning(use_pydantic=False).run()

    assert len(results) == 1
    assert results[0].id == 1
    # Same bug on the plain-dataclass path.
    assert results[0].email == "alice@example.com"


def test_update_returning_custom_column_name_pydantic(fresh_db: SqliteDb):
    """
    UPDATE … RETURNING correctly maps DB column 'user_email' back to Python
    field 'email' (pydantic path).
    """
    user = User(id=1, email="alice@example.com")
    fresh_db.insert(User).values(user).run()

    from embar.query.where import Eq

    results = (
        fresh_db.update(User).set({"email": "bob@example.com"}).where(Eq(User.id, 1)).returning(use_pydantic=True).run()
    )

    assert len(results) == 1
    assert results[0].id == 1
    assert results[0].email == "bob@example.com"


def test_update_returning_custom_column_name_plain(fresh_db: SqliteDb):
    """
    UPDATE … RETURNING correctly maps DB column 'user_email' back to Python
    field 'email' (plain dataclass path).
    """
    user = User(id=1, email="alice@example.com")
    fresh_db.insert(User).values(user).run()

    from embar.query.where import Eq

    results = (
        fresh_db.update(User)
        .set({"email": "bob@example.com"})
        .where(Eq(User.id, 1))
        .returning(use_pydantic=False)
        .run()
    )

    assert len(results) == 1
    assert results[0].id == 1
    assert results[0].email == "bob@example.com"
