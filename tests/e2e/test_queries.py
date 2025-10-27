from dataclasses import asdict
from datetime import datetime

from pudl.db.sqlite import Db as SqliteDb
from pudl.db.pg import Db as PgDb
from pudl.where import Eq, JEq, Like, Or
from pudl.selection import Selection
from pudl.sql import sql

from .schema import User, Message
from dataclasses import dataclass
from typing import Annotated


def test_select_string_array(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    @dataclass
    class UserSel(Selection):
        id: Annotated[int, User.id]
        messages: Annotated[list[str], Message.content.many()]

    # fmt: off
    res = (
        db.select(UserSel)
        .fromm(User)
        .left_join(Message, JEq(User.id, Message.user_id))
        .where(Or(
            Eq(User.id, 1),
            Like(User.email, "john%")
        ))
        .group_by(User.id)
        .limit(1)
        .execute()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    want = UserSel(id=1, messages=["Hello!"])
    assert asdict(got) == asdict(want)


def test_select_json_array(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    @dataclass
    class UserFullMessages(Selection):
        email: Annotated[str, User.email]
        messages: Annotated[list[Message], Message.many()]
        date: Annotated[datetime, sql(t"CURRENT_TIMESTAMP")]

    # fmt: off
    got = (
        db.select(UserFullMessages)
        .fromm(User)
        .left_join(Message, JEq(User.id, Message.user_id))
        .group_by(User.id)
        .limit(2)
        .execute()
    )
    # fmt: on

    assert len(got) == 1
    assert got[0].email == "john@foo.com"
    assert got[0].messages[0].content == "Hello!"
    assert got[0].messages[0].id == 1
    assert isinstance(got[0].date, datetime)


def test_select_json(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    @dataclass
    class MessageSel(Selection):
        user: Annotated[User, User]
        message: Annotated[str, Message.content]

    # fmt: off
    res = (
        db.select(MessageSel)
        .fromm(Message)
        .left_join(User, JEq(User.id, Message.user_id))
        .limit(2)
        .execute()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    assert got.user.email == "john@foo.com"
    assert got.user.id == 1
    assert got.message == "Hello!"
