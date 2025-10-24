import asyncio
import random
import string
import os

from pudl.db import AsyncDb
from pudl.where import Eq, Like, Or

from . import schema
from .schema import User, Message, UserSel, MessageSel


DATABASE_URL = os.getenv("DATABASE_URL")


async def main():
    user_id = "".join(random.choices(string.ascii_lowercase, k=5))
    user = User(id=user_id, email="john@foo.com")
    message = Message(id="m1", user_id=user.id, content="Hello!")

    assert DATABASE_URL is not None, "DATABASE_URL not set"
    db = await AsyncDb(DATABASE_URL).connect()
    await db.migrates(schema)

    await db.insert(User).values(user).aexecute()
    await db.insert(Message).values(message).aexecute()

    # fmt: off
    users = await (
        db.select(UserSel)
        .fromm(User)
        .where(Or(
            Eq(User.id.info, "a"),
            Like(User.email.info, "john%")
        ))
        .limit(2)
        .aexecute()
    )
    # fmt: on
    print(users)

    # fmt: off
    messages = await (
        db.select(MessageSel)
        .fromm(Message)
        .left_join(User, Eq(User.id.info, Message.user_id.info))
        .limit(2)
        .aexecute()
    )
    # fmt: on
    print(messages)


if __name__ == "__main__":
    asyncio.run(main())
