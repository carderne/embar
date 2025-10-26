from dataclasses import dataclass
from datetime import datetime
import os
import sqlite3
from typing import Annotated

import psycopg

from pudl.db.base import DbType
from pudl.db.pg import Db as PgDb
from pudl.db.sqlite import Db as SqliteDb
from pudl.selection import Selection
from pudl.sql import sql
from pudl.where import Eq, JEq, Like, Or

from . import schema
from .schema import User, Message


DATABASE_URL = os.getenv("DATABASE_URL")


@dataclass
class UserSel(Selection):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]


@dataclass
class UserFullMessages(Selection):
    email: Annotated[str, User.email]
    messages: Annotated[list[Message], Message.many()]
    date: Annotated[datetime, sql(t"CURRENT_TIMESTAMP")]


@dataclass
class MessageSel(Selection):
    user: Annotated[User, User]
    message: Annotated[str, Message.content]


assert DATABASE_URL is not None, "DATABASE_URL not set"
pg_client = psycopg.connect(DATABASE_URL)
sqlite_client = sqlite3.connect(":memory:")


def main(db_type: DbType):
    user = User(id=1, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")

    db = PgDb(pg_client) if db_type == "postgres" else SqliteDb(sqlite_client)
    db = PgDb(pg_client)
    db.migrates(schema)

    db.insert(User).value(user).execute()
    db.insert(Message).value(message).execute()

    # fmt: off
    users = (
        db.select(UserSel)
        .fromm(User)
        .left_join(Message, JEq(User.id, Message.user_id))
        .where(Or(
            Eq(User.id, 1),
            Like(User.email, "john%")
        ))
        .group_by(User.id)
        .limit(2)
        .execute()
    )
    # fmt: on
    print(users)

    # fmt: off
    users2 = (
        db.select(UserFullMessages)
        .fromm(User)
        .left_join(Message, JEq(User.id, Message.user_id))
        .group_by(User.id)
        .limit(2)
        .execute()
    )
    # fmt: on
    print(users2)

    # fmt: off
    messages = (
        db.select(MessageSel)
        .fromm(Message)
        .left_join(User, JEq(User.id, Message.user_id))
        .limit(2)
        .execute()
    )
    # fmt: on
    print(messages)


if __name__ == "__main__":
    main("postgres")
