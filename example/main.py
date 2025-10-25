import random
import os

from pudl.db import Db
from pudl.where import Eq, JEq, Like, Or

from . import schema
from .schema import User, Message, UserSel, MessageSel


DATABASE_URL = os.getenv("DATABASE_URL")


def main():
    user_id = random.randint(0, 100)
    user = User(id=user_id, email="john@foo.com")
    message = Message(id=1, user_id=user.id, content="Hello!")

    assert DATABASE_URL is not None, "DATABASE_URL not set"
    db = Db(DATABASE_URL).connect()
    db.migrates(schema)

    db.insert(User).values(user).execute()
    db.insert(Message).values(message).execute()

    # fmt: off
    users = (
        db.select(UserSel)
        .fromm(User)
        .where(Or(
            Eq(User.id, 1),
            Like(User.email, "john%")
        ))
        .limit(2)
        .execute()
    )
    # fmt: on
    print(users)

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
