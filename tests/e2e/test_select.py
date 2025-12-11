from datetime import datetime
from typing import Annotated

import pytest
from pydantic import BaseModel

from embar.db.pg import PgDb
from embar.db.sqlite import SqliteDb
from embar.query.where import Eq, Exists, Like, Or
from embar.sql import Sql

from ..schemas.schema import Message, User


def test_table_col_names():
    assert Message.get_name() == "message"
    assert User.get_name() == "users"


@pytest.mark.asyncio
async def test_select_string_array(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        messages: Annotated[list[str], Message.content.many()]

    # fmt: off
    res = (
        db.select(UserSel)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .where(Or(
            Eq(User.id, 1),
            Like(User.email, "john%")
        ))
        .group_by(User.id)
        .limit(1)
        .run()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    want = UserSel(id=1, messages=["Hello!"])

    assert got.messages == want.messages


def test_select_json_array(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    class UserFullMessages(BaseModel):
        email: Annotated[str, User.email]
        messages: Annotated[list[Message], Message.many()]
        date: Annotated[datetime, Sql(t"CURRENT_TIMESTAMP")]

    # fmt: off
    got = (
        db.select(UserFullMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
        .limit(2)
        .run()
    )
    # fmt: on

    assert len(got) == 1
    assert got[0].email == "john@foo.com"
    assert got[0].messages[0].content == "Hello!"
    assert got[0].messages[0].id == 1
    assert isinstance(got[0].date, datetime)


def test_select_json(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    class MessageSel(BaseModel):
        user: Annotated[User, User.one()]
        message: Annotated[str, Message.content]

    # fmt: off
    res = (
        db.select(MessageSel)
        .from_(Message)
        .left_join(User, Eq(User.id, Message.user_id))
        .limit(2)
        .run()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    assert got.user.email == "john@foo.com"
    assert got.user.id == 1
    assert got.message == "Hello!"


def test_select_subquery(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    class MessageSel(BaseModel):
        id: Annotated[int, Message.id]
        contenet: Annotated[str, Message.content]

    # fmt: off
    inner_query = (
        db.select(MessageSel)
        .from_(Message)
        .where(Eq(Message.id, 100))
    )
    # fmt: on

    # fmt: off
    res = (
        db.select(MessageSel)
        .from_(Message)
        .where(Exists(inner_query))
        .run()
    )
    # fmt: on

    assert len(res) == 0
