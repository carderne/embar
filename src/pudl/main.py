import random
import string
from dataclasses import dataclass
import os
from typing import final

from pudl.db import Database
from pudl.table import SelectAll, Selection, TextColumn, Table, Text
from pudl.where import And, Eq, Like


DATABASE_URL = os.getenv("DATABASE_URL")


@dataclass
@final
class User(Table):
    _name = "user"
    id: TextColumn = Text(primary=True)
    email: TextColumn = Text("user_email", default="text", not_null=True)


@dataclass
@final
class Message(Table):
    id: TextColumn = Text()
    user_id: TextColumn = Text().fk(lambda: User.id.info)
    content: TextColumn = Text()


@dataclass
class UserSel(Selection):
    id: str = User.id.sel()


def main():
    id = "".join(random.choices(string.ascii_lowercase, k=5))
    user = User(id=id, email="john@foo.com")

    message = Message(id=id, user_id=id, content="Hello!")

    assert DATABASE_URL is not None, "DATABASE_URL not set"
    db = Database(DATABASE_URL).connect().migrate([User, Message])

    db.insert(User).values(user).execute()
    db.insert(Message).values(message).execute()

    # fmt: off
    results = (
        db.select(UserSel)
        .fromm(User)
        .where(And(
            Eq(User.id.info, "a"),
            Like(User.email.info, "john%")
        ))
        .limit(10)
        .execute()
    )
    # fmt: on
    print(results)

    # fmt: off
    results = (
        db.select(SelectAll)
        .fromm(Message)
        .limit(2)
        .execute()
    )
    # fmt: on
    print(results)


if __name__ == "__main__":
    main()
