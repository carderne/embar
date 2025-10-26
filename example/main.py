from dataclasses import dataclass
import random
import os
from typing import Annotated

from pudl.db import Db
from pudl.selection import Selection
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


@dataclass
class MessageSel(Selection):
    user_name: Annotated[str, User.email]
    message: Annotated[str, Message.content]


def main():
    user_id = random.randint(0, 100)
    user = User(id=user_id, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")

    assert DATABASE_URL is not None, "DATABASE_URL not set"
    db = Db(DATABASE_URL).connect()
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
    main()
