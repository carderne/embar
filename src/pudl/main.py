from dataclasses import dataclass
import os
from typing import final

from pudl.db import Database
from pudl.table import Selection, TextColumn, Table, Text


DATABASE_URL = os.getenv("DATABASE_URL")


@dataclass
@final
class User(Table):
    _name = "user"
    id: TextColumn = Text()
    email: TextColumn = Text("user_email", default="text", not_null=True)


def main():
    user = User(id="a", email="john@foo.com")

    assert DATABASE_URL is not None, "DATABASE_URL not set"
    db = Database(DATABASE_URL).connect().migrate(User)

    db.insert(User).values(user).execute()

    @dataclass
    class UserSel(Selection):
        id: str = User.id.sel()

    results = (
        db.select(UserSel)
        .fromm(User)
        .where(User.id.info, "=", "a")
        .where(User.email.info, "LIKE", "john%")
        .limit(10)
        .execute()
    )

    print(results)


if __name__ == "__main__":
    main()
